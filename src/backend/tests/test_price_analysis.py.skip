"""Tests for price analysis service (F-005)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Case
from app.models.price_history import SuccessfulBids
from app.services.price_analysis import PriceAnalyzer


@pytest.fixture
async def sample_case(db: AsyncSession) -> Case:
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
    db.add(case)
    await db.flush()
    return case


@pytest.fixture
async def sample_price_histories(
    db: AsyncSession, sample_case: Case
) -> list[SuccessfulBids]:
    """Create sample price history records."""
    histories = []
    now = datetime.now(UTC)

    for i in range(5):
        bid_date = now - timedelta(days=i * 30)
        history = SuccessfulBids(
            case_id=sample_case.id,
            final_price=Decimal(f"{9500000 + i * 100000}"),
            number_of_bidders=5 + i,
            bid_date=bid_date,
            source="test",
        )
        db.add(history)
        histories.append(history)

    await db.flush()
    return histories


@pytest.mark.asyncio
async def test_price_analyzer_init(db: AsyncSession) -> None:
    """Test PriceAnalyzer initialization."""
    analyzer = PriceAnalyzer(db)
    assert analyzer.session is not None


@pytest.mark.asyncio
async def test_get_price_stats_empty(db: AsyncSession) -> None:
    """Test price stats with no data."""
    analyzer = PriceAnalyzer(db)
    stats = await analyzer.get_price_stats()

    assert stats["count"] == 0
    assert stats["avg_winning_bid"] is None
    assert stats["median_winning_bid"] is None


@pytest.mark.asyncio
async def test_get_price_stats_with_data(
    db: AsyncSession,
    sample_case: Case,
    sample_price_histories: list[SuccessfulBids],
) -> None:
    """Test price stats with sample data."""
    analyzer = PriceAnalyzer(db)
    stats = await analyzer.get_price_stats()

    assert stats["count"] == 5
    assert stats["avg_winning_bid"] is not None
    assert stats["median_winning_bid"] is not None
    assert stats["std_dev"] is not None
    assert stats["avg_bid_count"] is not None


@pytest.mark.asyncio
async def test_analyze_price_for_case_no_data(
    db: AsyncSession, sample_case: Case
) -> None:
    """Test case analysis with no price data."""
    analyzer = PriceAnalyzer(db)
    analysis = await analyzer.analyze_price_for_case(sample_case.id)

    assert analysis["recent_winning_bids"] == []
    assert analysis["price_trend"] == "insufficient_data"
    assert analysis["confidence"] == 0
    assert analysis["price_score"] == 50


@pytest.mark.asyncio
async def test_analyze_price_for_case_with_data(
    db: AsyncSession,
    sample_case: Case,
    sample_price_histories: list[SuccessfulBids],
) -> None:
    """Test case analysis with price data."""
    analyzer = PriceAnalyzer(db)
    analysis = await analyzer.analyze_price_for_case(sample_case.id)

    assert len(analysis["recent_winning_bids"]) > 0
    assert analysis["price_trend"] in ["上昇", "低下", "安定", "insufficient_data"]
    assert analysis["confidence"] > 0
    assert 0 <= analysis["price_score"] <= 100


@pytest.mark.asyncio
async def test_import_price_data(db: AsyncSession, sample_case: Case) -> None:
    """Test importing price data."""
    analyzer = PriceAnalyzer(db)

    price_data = {
        "budgeted_price": 10000000,
        "winning_bid": 9500000,
        "total_bids": 5,
        "unique_bidders": 5,
        "recorded_at": datetime.now(UTC),
    }

    history = await analyzer.import_price_data(sample_case.id, price_data)

    assert history.case_id == sample_case.id
    assert history.asking_price == Decimal("10000000")
    assert history.lowest_bid == Decimal("9500000")


@pytest.mark.asyncio
async def test_competitive_level_detection(
    db: AsyncSession, sample_case: Case
) -> None:
    """Test competitive level detection."""
    analyzer = PriceAnalyzer(db)

    # High competition (many bids)
    for i in range(5):
        history = SuccessfulBids(
            case_id=sample_case.id,
            final_price=Decimal("9500000"),
            number_of_bidders=15,
            bid_date=datetime.now(UTC) - timedelta(days=i),
            source="test",
        )
        db.add(history)

    await db.flush()

    analysis = await analyzer.analyze_price_for_case(sample_case.id)
    assert analysis["competitive_level"] == "激戦"


@pytest.mark.asyncio
async def test_price_trend_detection(
    db: AsyncSession, sample_case: Case
) -> None:
    """Test price trend detection."""
    analyzer = PriceAnalyzer(db)

    # Ascending trend
    base_prices = [9000000, 9200000, 9400000, 9600000, 9800000]
    for i, price in enumerate(base_prices):
        history = SuccessfulBids(
            case_id=sample_case.id,
            final_price=Decimal(str(price)),
            number_of_bidders=5,
            bid_date=datetime.now(UTC) - timedelta(days=i),
            source="test",
        )
        db.add(history)

    await db.flush()

    analysis = await analyzer.analyze_price_for_case(sample_case.id)
    assert analysis["price_trend"] == "上昇"
