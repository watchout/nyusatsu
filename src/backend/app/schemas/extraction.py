"""Structured extraction schemas for F-002 LLM output.

Defines the 5-category extraction model that the LLM must produce.
Each field carries an assertion_type where applicable.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.evidence import AssertionType


# ---------------------------------------------------------------------------
# Category 1: 参加条件
# ---------------------------------------------------------------------------
class AdditionalRequirement(BaseModel):
    name: str
    type: str  # "license", "certification", "experience", etc.
    assertion_type: AssertionType = AssertionType.INFERRED


class EligibilityExtraction(BaseModel):
    unified_qualification: bool | None = None
    grade: str | None = None
    business_category: str | None = None
    region: str | None = None
    additional_requirements: list[AdditionalRequirement] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Category 2: スケジュール
# ---------------------------------------------------------------------------
class ScheduleExtraction(BaseModel):
    spec_meeting_date: str | None = None
    submission_deadline: str | None = None
    opening_date: str | None = None
    equivalent_deadline: str | None = None
    quote_deadline: str | None = None
    performance_deadline: str | None = None


# ---------------------------------------------------------------------------
# Category 3: 業務内容
# ---------------------------------------------------------------------------
class DeliveryItem(BaseModel):
    name: str
    quantity: str | None = None
    spec: str | None = None


class DeliveryLocation(BaseModel):
    address: str
    delivery_deadline: str | None = None


class BusinessContentExtraction(BaseModel):
    business_type: str | None = None
    summary: str | None = None
    items: list[DeliveryItem] = Field(default_factory=list)
    delivery_locations: list[DeliveryLocation] = Field(default_factory=list)
    contract_type: str | None = None
    has_quote_requirement: bool | None = None
    has_spec_meeting: bool | None = None


# ---------------------------------------------------------------------------
# Category 4: 提出物
# ---------------------------------------------------------------------------
class SubmissionItem(BaseModel):
    name: str
    template_source: str | None = None  # "発注機関指定書式", "汎用テンプレート", null
    deadline: str | None = None
    notes: str | None = None
    assertion_type: AssertionType = AssertionType.INFERRED


class SubmissionItemsExtraction(BaseModel):
    bid_time_items: list[SubmissionItem] = Field(default_factory=list)
    performance_time_items: list[SubmissionItem] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Category 5: リスク要因
# ---------------------------------------------------------------------------
class RiskFactor(BaseModel):
    risk_type: str  # "quote_deadline_urgent", "multiple_delivery_locations", etc.
    label: str
    severity: str  # "high", "medium", "low"
    description: str
    assertion_type: AssertionType = AssertionType.INFERRED


# ---------------------------------------------------------------------------
# 統合: 5カテゴリ全体
# ---------------------------------------------------------------------------
class CaseCardExtraction(BaseModel):
    """Full structured extraction from LLM, covering all 5 JSONB categories."""

    eligibility: EligibilityExtraction | None = None
    schedule: ScheduleExtraction | None = None
    business_content: BusinessContentExtraction | None = None
    submission_items: SubmissionItemsExtraction | None = None
    risk_factors: list[RiskFactor] = Field(default_factory=list)
