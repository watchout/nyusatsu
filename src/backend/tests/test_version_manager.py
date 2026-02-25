"""Tests for TASK-11: VersionManager.

Validates atomic version rotation for case_cards, eligibility_results,
and checklists models.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.models.case import Case
from app.models.case_card import CaseCard
from app.models.checklist import Checklist
from app.models.eligibility_result import EligibilityResult
from app.services.version_manager import VersionManager


@pytest.fixture
async def sample_case(db):
    """Create a minimal case for version tests."""
    case = Case(
        source="test",
        source_id="vm-test-001",
        case_name="VersionManager Test Case",
        issuing_org="Test Org",
    )
    db.add(case)
    await db.flush()
    await db.refresh(case)
    return case


@pytest.mark.anyio
class TestVersionManagerWithCaseCard:
    """Test VersionManager using CaseCard model."""

    async def test_create_initial_version(self, db, sample_case):
        vm = VersionManager(CaseCard)
        card = await vm.create_initial(db, data={
            "case_id": sample_case.id,
            "status": "completed",
        })
        assert card.version == 1
        assert card.is_current is True
        assert card.case_id == sample_case.id

    async def test_rotate_sets_old_to_not_current(self, db, sample_case):
        vm = VersionManager(CaseCard)
        v1 = await vm.create_initial(db, data={
            "case_id": sample_case.id,
            "status": "completed",
        })

        _v2 = await vm.rotate(db, case_id=sample_case.id, new_data={
            "status": "completed",
        })

        await db.refresh(v1)
        assert v1.is_current is False

    async def test_rotate_creates_new_version(self, db, sample_case):
        vm = VersionManager(CaseCard)
        await vm.create_initial(db, data={
            "case_id": sample_case.id,
            "status": "completed",
        })

        v2 = await vm.rotate(db, case_id=sample_case.id, new_data={
            "status": "completed",
        })

        assert v2.version == 2
        assert v2.is_current is True

    async def test_get_current_returns_latest(self, db, sample_case):
        vm = VersionManager(CaseCard)
        await vm.create_initial(db, data={
            "case_id": sample_case.id,
            "status": "completed",
        })
        v2 = await vm.rotate(db, case_id=sample_case.id, new_data={
            "status": "completed",
        })

        current = await vm.get_current(db, case_id=sample_case.id)
        assert current is not None
        assert current.id == v2.id
        assert current.version == 2

    async def test_get_current_none_when_empty(self, db, sample_case):
        vm = VersionManager(CaseCard)
        current = await vm.get_current(db, case_id=sample_case.id)
        assert current is None

    async def test_get_all_versions_ordered_desc(self, db, sample_case):
        vm = VersionManager(CaseCard)
        await vm.create_initial(db, data={
            "case_id": sample_case.id,
            "status": "completed",
        })
        await vm.rotate(db, case_id=sample_case.id, new_data={
            "status": "completed",
        })
        await vm.rotate(db, case_id=sample_case.id, new_data={
            "status": "completed",
        })

        all_versions = await vm.get_all_versions(db, case_id=sample_case.id)
        assert len(all_versions) == 3
        assert all_versions[0].version == 3
        assert all_versions[1].version == 2
        assert all_versions[2].version == 1

    async def test_multiple_rotations(self, db, sample_case):
        """Three sequential rotations produce v1, v2, v3 with only v3 current."""
        vm = VersionManager(CaseCard)
        await vm.create_initial(db, data={
            "case_id": sample_case.id,
            "status": "completed",
        })
        await vm.rotate(db, case_id=sample_case.id, new_data={
            "status": "completed",
        })
        v3 = await vm.rotate(db, case_id=sample_case.id, new_data={
            "status": "completed",
        })

        assert v3.version == 3
        current = await vm.get_current(db, case_id=sample_case.id)
        assert current is not None
        assert current.version == 3

        # Only one should be current
        all_v = await vm.get_all_versions(db, case_id=sample_case.id)
        current_count = sum(1 for v in all_v if v.is_current)
        assert current_count == 1


@pytest.mark.anyio
class TestVersionManagerWithEligibility:
    """Test VersionManager using EligibilityResult model."""

    async def test_rotate_with_eligibility_results(self, db, sample_case):
        vm_card = VersionManager(CaseCard)
        card = await vm_card.create_initial(db, data={
            "case_id": sample_case.id,
            "status": "completed",
        })

        vm = VersionManager(EligibilityResult)
        v1 = await vm.create_initial(db, data={
            "case_id": sample_case.id,
            "case_card_id": card.id,
            "verdict": "eligible",
            "confidence": Decimal("0.85"),
            "hard_fail_reasons": [],
            "soft_gaps": [],
            "check_details": {"tested": True},
            "company_profile_snapshot": {"name": "Test"},
        })
        assert v1.version == 1

        v2 = await vm.rotate(db, case_id=sample_case.id, new_data={
            "case_card_id": card.id,
            "verdict": "uncertain",
            "confidence": Decimal("0.55"),
            "hard_fail_reasons": [],
            "soft_gaps": [{"gap": "missing cert"}],
            "check_details": {"tested": True},
            "company_profile_snapshot": {"name": "Test"},
        })
        assert v2.version == 2
        assert v2.verdict == "uncertain"


@pytest.mark.anyio
class TestVersionManagerWithChecklist:
    """Test VersionManager using Checklist model."""

    async def test_rotate_with_checklists(self, db, sample_case):
        vm_card = VersionManager(CaseCard)
        card = await vm_card.create_initial(db, data={
            "case_id": sample_case.id,
            "status": "completed",
        })

        vm_elig = VersionManager(EligibilityResult)
        elig = await vm_elig.create_initial(db, data={
            "case_id": sample_case.id,
            "case_card_id": card.id,
            "verdict": "eligible",
            "confidence": Decimal("0.85"),
            "hard_fail_reasons": [],
            "soft_gaps": [],
            "check_details": {},
            "company_profile_snapshot": {},
        })

        vm = VersionManager(Checklist)
        v1 = await vm.create_initial(db, data={
            "case_id": sample_case.id,
            "case_card_id": card.id,
            "eligibility_result_id": elig.id,
            "checklist_items": [{"id": "1", "text": "Submit form", "done": False}],
            "schedule_items": [{"date": "2026-03-01", "task": "Prepare"}],
        })
        assert v1.version == 1

        v2 = await vm.rotate(db, case_id=sample_case.id, new_data={
            "case_card_id": card.id,
            "eligibility_result_id": elig.id,
            "checklist_items": [
                {"id": "1", "text": "Submit form", "done": True},
                {"id": "2", "text": "Attach docs", "done": False},
            ],
            "schedule_items": [{"date": "2026-03-01", "task": "Prepare"}],
        })
        assert v2.version == 2
        assert len(v2.checklist_items) == 2
