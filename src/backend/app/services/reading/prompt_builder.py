"""Prompt construction for F-002 Stage 2.

Builds LLM prompts that instruct extraction of 5 categories
from notice HTML and spec PDF text.
"""

from __future__ import annotations

from app.services.llm.base import LLMRequest

# ---------------------------------------------------------------------------
# System prompt — instructs the LLM on extraction rules
# ---------------------------------------------------------------------------
EXTRACTION_SYSTEM_PROMPT = """\
あなたは日本の官公庁入札案件から構造化情報を抽出する専門AIです。

以下の5カテゴリをJSON形式で出力してください。

## 出力JSON構造

```json
{
  "eligibility": {
    "unified_qualification": true/false/null,
    "grade": "A"/"B"/"C"/"D"/null,
    "business_category": "物品の販売"/null,
    "region": "関東・甲信越"/null,
    "additional_requirements": [
      {"name": "...", "type": "license/certification/experience", "assertion_type": "fact/inferred/caution"}
    ]
  },
  "schedule": {
    "spec_meeting_date": "ISO8601 or null",
    "submission_deadline": "ISO8601 or null",
    "opening_date": "ISO8601 or null",
    "equivalent_deadline": "ISO8601 or null",
    "quote_deadline": "ISO8601 or null",
    "performance_deadline": "ISO8601 or null"
  },
  "business_content": {
    "business_type": "物品の販売/役務の提供/...",
    "summary": "概要文",
    "items": [{"name": "...", "quantity": "...", "spec": "..."}],
    "delivery_locations": [{"address": "...", "delivery_deadline": "..."}],
    "contract_type": "単価契約/総価契約/null",
    "has_quote_requirement": true/false/null,
    "has_spec_meeting": true/false/null
  },
  "submission_items": {
    "bid_time_items": [
      {"name": "...", "template_source": "発注機関指定書式/汎用テンプレート/null", "deadline": "...", "notes": "...", "assertion_type": "fact/inferred/caution"}
    ],
    "performance_time_items": [
      {"name": "...", "template_source": "...", "deadline": "...", "notes": "...", "assertion_type": "fact/inferred/caution"}
    ]
  },
  "risk_factors": [
    {"risk_type": "...", "label": "...", "severity": "high/medium/low", "description": "...", "assertion_type": "fact/inferred/caution"}
  ]
}
```

## assertion_type ルール
- "fact": 原文に明確に記載されている場合
- "inferred": 原文から推測できるが明確ではない場合
- "caution": 原文に矛盾や曖昧さがある場合（要人手確認）

## 注意事項
- JSONのみを出力してください。説明文は不要です。
- 情報が見つからないフィールドはnullを設定してください。
- 日付はISO 8601形式（例: "2026-03-15T17:00:00+09:00"）で出力してください。
- 和暦（令和○年）はISO8601に変換してください。
- 全角数字は半角に変換してください。
"""

CHUNK_SYSTEM_PROMPT_SUFFIX = """
## チャンク処理モード
この文書は長いため分割して送信しています。
チャンク {chunk_index}/{total_chunks} です。
このチャンクに含まれる情報のみを抽出してください。
情報がない場合はnullを設定してください。
"""


class PromptBuilder:
    """Build LLM prompts for structured extraction."""

    def build_extraction_prompt(
        self,
        notice_text: str,
        spec_text: str | None = None,
    ) -> LLMRequest:
        """Build a full extraction prompt with notice and optional spec text."""
        user_content = self._build_user_content(notice_text, spec_text)
        return LLMRequest(
            system=EXTRACTION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
            max_tokens=4096,
            temperature=0.0,
            metadata={"prompt_type": "full_extraction"},
        )

    def build_chunk_prompt(
        self,
        chunk_text: str,
        chunk_index: int,
        total_chunks: int,
    ) -> LLMRequest:
        """Build a prompt for a single chunk of a long document."""
        system = EXTRACTION_SYSTEM_PROMPT + CHUNK_SYSTEM_PROMPT_SUFFIX.format(
            chunk_index=chunk_index,
            total_chunks=total_chunks,
        )
        return LLMRequest(
            system=system,
            messages=[{"role": "user", "content": chunk_text}],
            max_tokens=4096,
            temperature=0.0,
            metadata={
                "prompt_type": "chunk_extraction",
                "chunk_index": chunk_index,
                "total_chunks": total_chunks,
            },
        )

    @staticmethod
    def _build_user_content(
        notice_text: str,
        spec_text: str | None,
    ) -> str:
        """Combine notice and spec text into user message."""
        parts = [
            "## 入札公告（HTML）\n",
            notice_text,
        ]
        if spec_text:
            parts.append("\n\n## 仕様書（PDF）\n")
            parts.append(spec_text)
        return "".join(parts)
