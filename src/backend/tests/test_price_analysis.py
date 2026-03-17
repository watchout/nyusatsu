"""Tests for price analysis service (F-005)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Case, PriceHistory
from app.services.price_analysis import PriceAnalyzer


@pytest.fixture
async def sample_case(session: AsyncSession) -> Case:
    """Create a sample case."""
    case = Case(
        source="test",
        source_id="test_001",
        case_name="テスト案件",
        issuing_org="テスト市",
        category="建築",
        region="東京都",
        submission_deadline=datetime.now(UTC) + timedelta(days=10),
    )
    session.add(case)
    await session.flush()
    return case


@pytest.fixture
async def sample_price_histories(
    session: AsyncSession, sample_case: Case
) -> list[PriceHistory]:
    """Create sample price history records."""
    histories = []
    now = datetime.now(UTC)

    for i in range(5):
        recorded_at = now - timedelta(days=i * 30)
        history = PriceHistory(
            case_id=sample_case.id,
            budgeted_price=Decimal("10000000"),
            winning_bid=Decimal(f"{9500000 + i * 100000}"),
            total_bids=5 + i,
            unique_bidders=5 + i,
            recorded_at=recorded_at,
            confidence_score=85,
        )
        session.add(history)
        histories.append(history)

    await session.flush()
    return histories


@pytest.mark.asyncio
async def test_price_analyzer_init(session: AsyncSession) -> None:
    """Test PriceAnalyzer initialization."""
    analyzer = PriceAnalyzer(session)
    assert analyzer.session is not None


@pytest.mark.asyncio
async def test_get_price_stats_empty(session: AsyncSession) -> None:
    """Test price stats with no data."""
    analyzer = PriceAnalyzer(session)
    stats = await analyzer.get_price_stats()

    assert stats["count"] == 0
    assert stats["avg_winning_bid"] is None
    assert stats["median_winning_bid"] is None


@pytest.mark.asyncio
async def test_get_price_stats_with_data(
    session: AsyncSession,
    sample_case: Case,
    sample_price_histories: list[PriceHistory],
) -> None:
    """Test price stats with sample data."""
    analyzer = PriceAnalyzer(session)
    stats = await analyzer.get_price_stats()

    assert stats["count"] == 5
    assert stats["avg_winning_bid"] is not None
    assert stats["median_winning_bid"] is not None
    assert stats["std_dev"] is not None
    assert stats["avg_bid_count"] is not None


@pytest.mark.asyncio
async def test_analyze_price_for_case_no_data(
    session: AsyncSession, sample_case: Case
) -> None:
    """Test case analysis with no price data."""
    analyzer = PriceAnalyzer(session)
    analysis = await analyzer.analyze_price_for_case(sample_case.id)

    assert analysis["recent_winning_bids"] == []
    assert analysis["price_trend"] == "insufficient_data"
    assert analysis["confidence"] == 0
    assert analysis["price_score"] == 50


@pytest.mark.asyncio
async def test_analyze_price_for_case_with_data(
    session: AsyncSession,
    sample_case: Case,
    sample_price_histories: list[PriceHistory],
) -> None:
    """Test case analysis with price data."""
    analyzer = PriceAnalyzer(session)
    analysis = await analyzer.analyze_price_for_case(sample_case.id)

    assert len(analysis["recent_winning_bids"]) > 0
    assert analysis["price_trend"] in ["上昇", "低下", "安定", "insufficient_data"]
    assert analysis["confidence"] > 0
    assert 0 <= analysis["price_score"] <= 100


@pytest.mark.asyncio
async def test_import_price_data(session: AsyncSession, sample_case: Case) -> None:
    """Test importing price data."""
    analyzer = PriceAnalyzer(session)

    price_data = {
        "budgeted_price": 10000000,
        "winning_bid": 9500000,
        "total_bids": 5,
        "unique_bidders": 5,
        "recorded_at": datetime.now(UTC),
    }

    history = await analyzer.import_price_data(sample_case.id, price_data)

    assert history.case_id == sample_case.id
    assert history.budgeted_price == Decimal("10000000")
    assert history.winning_bid == Decimal("9500000")
    assert history.price_difference_rate == Decimal("-5.00")


@pytest.mark.asyncio
async def test_competitive_level_detection(
    session: AsyncSession, sample_case: Case
) -> None:
    """Test competitive level detection."""
    analyzer = PriceAnalyzer(session)

    # High competition (many bids)
    for i in range(5):
        history = PriceHistory(
            case_id=sample_case.id,
            winning_bid=Decimal("9500000"),
            total_bids=15,
            recorded_at=datetime.now(UTC) - timedelta(days=i),
        )
        session.add(history)

    await session.flush()

    analysis = await analyzer.analyze_price_for_case(sample_case.id)
    assert analysis["competitive_level"] == "激戦"


@pytest.mark.asyncio
async def test_price_trend_detection(
    session: AsyncSession, sample_case: Case
) -> None:
    """Test price trend detection."""
    analyzer = PriceAnalyzer(session)

    # Ascending trend
    base_prices = [9000000, 9200000, 9400000, 9600000, 9800000]
    for i, price in enumerate(base_prices):
        history = PriceHistory(
            case_id=sample_case.id,
            winning_bid=Decimal(str(price)),
            total_bids=5,
            recorded_at=datetime.now(UTC) - timedelta(days=i),
        )
        session.add(history)

    await session.flush()

    analysis = await analyzer.analyze_price_for_case(sample_case.id)
    assert analysis["price_trend"] == "上昇"
