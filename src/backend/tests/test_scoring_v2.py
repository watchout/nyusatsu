"""Tests for scoring algorithm v2 (F-005)."""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Case, PriceHistory
from app.services.scoring_v2 import ScoringV2, calculate_score_for_case


@pytest.fixture
async def sample_case_for_scoring(session: AsyncSession) -> Case:
    """Create a sample case for scoring."""
    case = Case(
        source="test",
        source_id="scoring_test_001",
        case_name="スコアリングテスト案件",
        issuing_org="テスト市役所",
        category="建築",
        region="東京都",
        submission_deadline=datetime.now(timezone.utc) + timedelta(days=15),
        opening_date=datetime.now(timezone.utc) - timedelta(days=5),
    )
    session.add(case)
    await session.flush()
    return case


@pytest.fixture
async def case_with_price_data(
    session: AsyncSession, sample_case_for_scoring: Case
) -> Case:
    """Create case with historical price data."""
    case = sample_case_for_scoring

    # Add 5 price records
    for i in range(5):
        history = PriceHistory(
            case_id=case.id,
            budgeted_price=Decimal("10000000"),
            winning_bid=Decimal(f"{9500000 + i * 100000}"),
            total_bids=5 + i,
            recorded_at=datetime.now(timezone.utc) - timedelta(days=i * 30),
            confidence_score=85,
        )
        session.add(history)

    await session.flush()
    return case


@pytest.mark.asyncio
async def test_scoring_v2_init(session: AsyncSession) -> None:
    """Test ScoringV2 initialization."""
    scorer = ScoringV2(session)
    assert scorer.session is not None
    assert scorer.price_analyzer is not None


@pytest.mark.asyncio
async def test_deadline_score_calculation() -> None:
    """Test deadline score calculation."""
    # Create a case with 20 days left
    case = Case(
        source="test",
        source_id="deadline_test",
        case_name="期限テスト",
        issuing_org="テスト",
        submission_deadline=datetime.now(timezone.utc) + timedelta(days=20),
    )

    scorer = ScoringV2(None)  # type: ignore
    score = scorer._calculate_deadline_score(case)

    assert score == 100  # 21+ days = 100


@pytest.mark.asyncio
async def test_deadline_score_near_deadline() -> None:
    """Test deadline score when deadline is near."""
    case = Case(
        source="test",
        source_id="deadline_test_2",
        case_name="期限テスト2",
        issuing_org="テスト",
        submission_deadline=datetime.now(timezone.utc) + timedelta(days=2),
    )

    scorer = ScoringV2(None)  # type: ignore
    score = scorer._calculate_deadline_score(case)

    assert score == 20  # 1-4 days = 20


@pytest.mark.asyncio
async def test_category_score() -> None:
    """Test category scoring."""
    scorer = ScoringV2(None)  # type: ignore

    # Test known category
    case_architecture = Case(
        source="test",
        source_id="cat_test_1",
        case_name="建築案件",
        issuing_org="テスト",
        category="建築",
    )
    assert scorer._calculate_category_score(case_architecture) == 90

    # Test another category
    case_civil = Case(
        source="test",
        source_id="cat_test_2",
        case_name="土木案件",
        issuing_org="テスト",
        category="土木",
    )
    assert scorer._calculate_category_score(case_civil) == 85


@pytest.mark.asyncio
async def test_bonus_score_government_issued() -> None:
    """Test bonus score for government-issued cases."""
    scorer = ScoringV2(None)  # type: ignore

    case = Case(
        source="test",
        source_id="bonus_test",
        case_name="国発注案件",
        issuing_org="国土交通省",
        submission_deadline=datetime.now(timezone.utc) + timedelta(days=30),
        opening_date=datetime.now(timezone.utc) - timedelta(days=5),
    )

    bonus = scorer._calculate_bonus_score(case)
    assert bonus > 50  # Should have bonus


@pytest.mark.asyncio
async def test_comprehensive_score_calculation(
    session: AsyncSession, case_with_price_data: Case
) -> None:
    """Test comprehensive score calculation."""
    scorer = ScoringV2(session)
    result = await scorer.calculate_comprehensive_score(case_with_price_data)

    assert "score" in result
    assert "score_breakdown" in result
    assert "factors" in result
    assert "recommendation" in result
    assert "confidence" in result

    assert 0 <= result["score"] <= 100
    assert result["score_breakdown"]["deadline_score"] >= 0
    assert result["score_breakdown"]["price_score"] >= 0
    assert result["score_breakdown"]["category_score"] >= 0
    assert result["score_breakdown"]["bonus_score"] >= 0

    assert result["recommendation"] in ["推奨", "検討", "非推奨"]


@pytest.mark.asyncio
async def test_comprehensive_score_high_quality(
    session: AsyncSession, case_with_price_data: Case
) -> None:
    """Test that good cases get high scores."""
    # Adjust case for good score
    case_with_price_data.submission_deadline = (
        datetime.now(timezone.utc) + timedelta(days=20)
    )
    case_with_price_data.category = "建築"
    case_with_price_data.issuing_org = "国土交通省"

    scorer = ScoringV2(session)
    result = await scorer.calculate_comprehensive_score(case_with_price_data)

    # Good case should have recommendation "推奨" or "検討"
    assert result["recommendation"] in ["推奨", "検討"]


@pytest.mark.asyncio
async def test_calculate_score_for_case_function(
    session: AsyncSession, case_with_price_data: Case
) -> None:
    """Test the convenience function."""
    result = await calculate_score_for_case(session, case_with_price_data)

    assert "score" in result
    assert "score_breakdown" in result
    assert 0 <= result["score"] <= 100


@pytest.mark.asyncio
async def test_days_left_calculation(
    session: AsyncSession, sample_case_for_scoring: Case
) -> None:
    """Test days left calculation."""
    scorer = ScoringV2(session)
    days_left = scorer._get_days_left(sample_case_for_scoring)

    assert days_left is not None
    assert days_left >= 14  # 15 days set in fixture
