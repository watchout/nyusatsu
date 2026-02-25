"""Tests for ChecklistBuilder (F-004)."""

from app.services.checklist_gen.checklist_builder import ChecklistBuilder


def _base_extraction(**overrides) -> dict:
    """Base extraction with minimal data."""
    data = {
        "submission_items": {
            "bid_time_items": [
                {"name": "入札書", "assertion_type": "fact"},
                {"name": "資格審査結果通知書", "assertion_type": "fact"},
            ],
            "performance_time_items": [
                {"name": "契約書", "assertion_type": "fact"},
            ],
        },
        "business_content": {},
    }
    data.update(overrides)
    return data


class TestChecklistBuilder:
    def test_bid_and_performance_items(self) -> None:
        """Bid + performance items are included."""
        builder = ChecklistBuilder()
        result = builder.build(_base_extraction())

        names = [i["name"] for i in result.checklist_items]
        assert "入札書" in names
        assert "資格審査結果通知書" in names
        assert "契約書" in names
        # Fixed items
        assert "封筒（二重封筒）" in names
        assert "配送方法の確認" in names

    def test_bid_time_only(self) -> None:
        """Only bid-time items when no performance items."""
        extraction = _base_extraction(
            submission_items={
                "bid_time_items": [{"name": "入札書", "assertion_type": "fact"}],
                "performance_time_items": [],
            },
        )
        builder = ChecklistBuilder()
        result = builder.build(extraction)

        categories = {i["category"] for i in result.checklist_items}
        assert "bid_time" in categories
        assert "performance_time" not in categories

    def test_quote_requirement_prioritized(self) -> None:
        """Quote item is added first when has_quote_requirement."""
        extraction = _base_extraction(
            business_content={"has_quote_requirement": True},
        )
        builder = ChecklistBuilder()
        result = builder.build(extraction)

        assert result.checklist_items[0]["name"] == "下見積もり書"

    def test_envelope_always_added(self) -> None:
        """Envelope is always in the checklist."""
        builder = ChecklistBuilder()
        result = builder.build(_base_extraction())

        names = [i["name"] for i in result.checklist_items]
        assert "封筒（二重封筒）" in names

    def test_empty_submission_items(self) -> None:
        """Empty submission_items still produces fixed items."""
        extraction = {
            "submission_items": None,
            "business_content": {},
        }
        builder = ChecklistBuilder()
        result = builder.build(extraction)

        # Should have at least the 2 fixed items
        assert len(result.checklist_items) >= 2

    def test_null_submission_items(self) -> None:
        """Null submission_items handled gracefully."""
        extraction = {"business_content": {}}
        builder = ChecklistBuilder()
        result = builder.build(extraction)

        assert len(result.checklist_items) >= 2

    def test_inferred_item_label(self) -> None:
        """Inferred items get label suffix."""
        extraction = _base_extraction(
            submission_items={
                "bid_time_items": [
                    {"name": "委任状", "assertion_type": "inferred"},
                ],
                "performance_time_items": [],
            },
        )
        builder = ChecklistBuilder()
        result = builder.build(extraction)

        inferred = [i for i in result.checklist_items if i.get("name") == "委任状"]
        assert len(inferred) == 1
        assert inferred[0].get("label_suffix") == "（推定）"

    def test_uncertain_confirmation_tasks(self) -> None:
        """Uncertain checks produce confirmation tasks."""
        extraction = _base_extraction()
        check_details = {
            "hard_checks": [
                {"rule_id": "H5", "label": "資格・免許", "result": "uncertain", "required": "建設業許可"},
            ],
            "soft_checks": [
                {"rule_id": "S1", "label": "実績", "result": "gap", "required": "同種業務"},
            ],
        }
        builder = ChecklistBuilder()
        result = builder.build(extraction, eligibility_check_details=check_details)

        confirm_items = [i for i in result.checklist_items if i["category"] == "confirmation"]
        assert len(confirm_items) == 2
        assert any("資格・免許" in i["name"] for i in confirm_items)

    def test_eligible_no_confirmation_tasks(self) -> None:
        """All-pass checks produce no confirmation tasks."""
        extraction = _base_extraction()
        check_details = {
            "hard_checks": [
                {"rule_id": "H1", "label": "統一資格", "result": "pass"},
            ],
            "soft_checks": [
                {"rule_id": "S1", "label": "実績", "result": "pass"},
            ],
        }
        builder = ChecklistBuilder()
        result = builder.build(extraction, eligibility_check_details=check_details)

        confirm_items = [i for i in result.checklist_items if i["category"] == "confirmation"]
        assert len(confirm_items) == 0

    def test_warnings_from_risk_factors(self) -> None:
        """Risk factors produce warnings."""
        extraction = _base_extraction()
        risk_factors = [
            {"severity": "high", "label": "見積期限逼迫", "description": "見積期限まで3日"},
        ]
        builder = ChecklistBuilder()
        result = builder.build(extraction, risk_factors=risk_factors)

        assert len(result.warnings) >= 1
        assert any("HIGH" in w for w in result.warnings)

    def test_warnings_from_soft_gaps(self) -> None:
        """Soft gaps produce warnings."""
        extraction = _base_extraction()
        soft_gaps = [
            {"label": "実績", "required": "同種業務実績"},
        ]
        builder = ChecklistBuilder()
        result = builder.build(extraction, soft_gaps=soft_gaps)

        assert len(result.warnings) >= 1
        assert any("ソフト条件" in w for w in result.warnings)

    def test_warnings_from_assertion_counts(self) -> None:
        """Assertion counts with inferred items produce warnings."""
        extraction = _base_extraction()
        assertion_counts = {"fact": 5, "inferred": 3, "caution": 1}
        builder = ChecklistBuilder()
        result = builder.build(extraction, assertion_counts=assertion_counts)

        assert any("推定項目" in w for w in result.warnings)

    def test_no_warnings_when_clean(self) -> None:
        """No warnings when everything is clean."""
        extraction = _base_extraction()
        builder = ChecklistBuilder()
        result = builder.build(extraction)

        assert len(result.warnings) == 0
