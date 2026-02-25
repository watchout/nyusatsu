"""Evidence and assertion type schemas for F-002/F-003/F-004.

Defines the fixed JSON contract for root evidence mapping.
- PdfEvidence: page + section + quote
- HtmlEvidence: selector + heading_path + quote
"""

from __future__ import annotations

from enum import Enum
from typing import Literal, Union

from pydantic import BaseModel, Field


class AssertionType(str, Enum):
    """Assertion confidence level per F-002 §3-B-1."""

    FACT = "fact"
    INFERRED = "inferred"
    CAUTION = "caution"


class PdfEvidence(BaseModel):
    """Evidence reference pointing to a PDF source."""

    source_type: Literal["pdf"] = "pdf"
    page: int = Field(..., ge=1, description="1-indexed page number")
    section: str = Field(..., min_length=1, description="Section heading text")
    quote: str = Field(..., min_length=1, max_length=200, description="Quoted text from source")
    assertion_type: AssertionType


class HtmlEvidence(BaseModel):
    """Evidence reference pointing to an HTML source."""

    source_type: Literal["html"] = "html"
    selector: str | None = Field(default=None, description="CSS selector hint")
    heading_path: str = Field(
        ..., min_length=1, description="Breadcrumb path e.g. '入札公告 > 参加資格'"
    )
    quote: str = Field(..., min_length=1, max_length=200, description="Quoted text from source")
    assertion_type: AssertionType


EvidenceRef = Union[PdfEvidence, HtmlEvidence]
"""Discriminated union for evidence references (PDF or HTML)."""
