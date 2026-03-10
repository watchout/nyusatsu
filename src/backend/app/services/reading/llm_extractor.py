"""LLM-based structured extraction for F-002 Stage 2.

Orchestrates prompt building, optional chunking, LLM calls, and response parsing.
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog

from app.schemas.extraction import CaseCardExtraction, ScheduleExtraction
from app.services.llm.base import LLMProvider
from app.services.reading.prompt_builder import PromptBuilder
from app.services.reading.response_parser import ResponseParser
from app.services.reading.section_chunker import SectionChunker

logger = structlog.get_logger()


@dataclass(frozen=True)
class ExtractionResult:
    """Result of LLM extraction."""

    extraction: CaseCardExtraction
    llm_model: str
    llm_request_id: str | None
    token_usage: dict[str, int]
    was_chunked: bool


class LLMExtractor:
    """Extract structured data from notice/spec text using an LLM."""

    def __init__(
        self,
        provider: LLMProvider,
        *,
        chunker: SectionChunker | None = None,
    ) -> None:
        self._provider = provider
        self._prompt_builder = PromptBuilder()
        self._chunker = chunker or SectionChunker()
        self._parser = ResponseParser()

    async def extract(
        self,
        notice_text: str,
        spec_text: str | None = None,
    ) -> ExtractionResult:
        """Run full extraction pipeline.

        1. Combine texts and check if chunking is needed.
        2. If short: single LLM call.
        3. If long: chunk, call LLM per chunk, merge results.
        """
        combined = notice_text
        if spec_text:
            combined = f"{notice_text}\n\n{spec_text}"

        if self._chunker.needs_splitting(combined):
            return await self._extract_chunked(notice_text, spec_text)
        return await self._extract_single(notice_text, spec_text)

    async def _extract_single(
        self,
        notice_text: str,
        spec_text: str | None,
    ) -> ExtractionResult:
        """Single-shot extraction for documents within token threshold."""
        request = self._prompt_builder.build_extraction_prompt(
            notice_text,
            spec_text,
        )
        response = await self._provider.complete(request)
        extraction = self._parser.parse(response.content)

        return ExtractionResult(
            extraction=extraction,
            llm_model=response.model,
            llm_request_id=response.metadata.get("request_id"),
            token_usage=dict(response.token_usage),
            was_chunked=False,
        )

    async def _extract_chunked(
        self,
        notice_text: str,
        spec_text: str | None,
    ) -> ExtractionResult:
        """Chunked extraction for long documents."""
        combined = notice_text
        if spec_text:
            combined = f"{notice_text}\n\n{spec_text}"

        chunks = self._chunker.split(combined)
        logger.info("chunked_extraction_start", num_chunks=len(chunks))

        extractions: list[CaseCardExtraction] = []
        total_usage: dict[str, int] = {"input": 0, "output": 0}
        last_model = ""
        last_request_id: str | None = None

        for chunk in chunks:
            request = self._prompt_builder.build_chunk_prompt(
                chunk.text,
                chunk.chunk_index,
                chunk.total_chunks,
            )
            response = await self._provider.complete(request)
            extraction = self._parser.parse(response.content)
            extractions.append(extraction)

            total_usage["input"] += response.token_usage.get("input", 0)
            total_usage["output"] += response.token_usage.get("output", 0)
            last_model = response.model
            last_request_id = response.metadata.get("request_id")

        merged = self._merge_extractions(extractions)
        return ExtractionResult(
            extraction=merged,
            llm_model=last_model,
            llm_request_id=last_request_id,
            token_usage=total_usage,
            was_chunked=True,
        )

    @staticmethod
    def _merge_extractions(
        extractions: list[CaseCardExtraction],
    ) -> CaseCardExtraction:
        """Merge multiple chunk extractions into one.

        Strategy: first non-null value wins for scalar fields,
        lists are concatenated with deduplication by name.
        """
        if len(extractions) == 1:
            return extractions[0]

        merged = CaseCardExtraction()

        for ext in extractions:
            # Eligibility: first non-null wins
            if ext.eligibility and not merged.eligibility:
                merged.eligibility = ext.eligibility
            elif ext.eligibility and merged.eligibility:
                # Merge additional_requirements
                existing_names = {
                    r.name for r in merged.eligibility.additional_requirements
                }
                for req in ext.eligibility.additional_requirements:
                    if req.name not in existing_names:
                        merged.eligibility.additional_requirements.append(req)
                        existing_names.add(req.name)
                # Fill null scalars
                if not merged.eligibility.grade and ext.eligibility.grade:
                    merged.eligibility.grade = ext.eligibility.grade
                if not merged.eligibility.business_category and ext.eligibility.business_category:
                    merged.eligibility.business_category = ext.eligibility.business_category
                if not merged.eligibility.region and ext.eligibility.region:
                    merged.eligibility.region = ext.eligibility.region

            # Schedule: first non-null wins per field
            if ext.schedule:
                if not merged.schedule:
                    merged.schedule = ext.schedule
                else:
                    for f in ScheduleExtraction.model_fields:
                        if getattr(merged.schedule, f) is None and getattr(ext.schedule, f) is not None:
                            setattr(merged.schedule, f, getattr(ext.schedule, f))

            # Business content: first non-null wins, lists concatenated
            if ext.business_content:
                if not merged.business_content:
                    merged.business_content = ext.business_content
                else:
                    bc = merged.business_content
                    ext_bc = ext.business_content
                    if not bc.summary and ext_bc.summary:
                        bc.summary = ext_bc.summary
                    if not bc.business_type and ext_bc.business_type:
                        bc.business_type = ext_bc.business_type
                    # Deduplicate items by name
                    existing_items = {i.name for i in bc.items}
                    for item in ext_bc.items:
                        if item.name not in existing_items:
                            bc.items.append(item)
                            existing_items.add(item.name)

            # Submission items: concatenate lists with dedup
            if ext.submission_items:
                if not merged.submission_items:
                    merged.submission_items = ext.submission_items
                else:
                    si = merged.submission_items
                    ext_si = ext.submission_items
                    existing_bid = {i.name for i in si.bid_time_items}
                    for item in ext_si.bid_time_items:
                        if item.name not in existing_bid:
                            si.bid_time_items.append(item)
                            existing_bid.add(item.name)
                    existing_perf = {i.name for i in si.performance_time_items}
                    for item in ext_si.performance_time_items:
                        if item.name not in existing_perf:
                            si.performance_time_items.append(item)
                            existing_perf.add(item.name)

            # Risk factors: concatenate with dedup by risk_type
            existing_risks = {r.risk_type for r in merged.risk_factors}
            for rf in ext.risk_factors:
                if rf.risk_type not in existing_risks:
                    merged.risk_factors.append(rf)
                    existing_risks.add(rf.risk_type)

        return merged
