"""Tests for grade_comparator (F-003)."""

from app.services.judgment.grade_comparator import grade_meets_requirement


class TestGradeComparator:
    def test_same_grade_passes(self) -> None:
        assert grade_meets_requirement("C", "C") is True

    def test_higher_grade_passes(self) -> None:
        """A company with grade A meets requirement for C."""
        assert grade_meets_requirement("A", "C") is True
        assert grade_meets_requirement("B", "C") is True

    def test_lower_grade_fails(self) -> None:
        """A company with grade D does not meet requirement for B."""
        assert grade_meets_requirement("D", "B") is False
        assert grade_meets_requirement("C", "A") is False

    def test_all_16_combinations(self) -> None:
        """Exhaustive test of all grade pairs."""
        grades = ["A", "B", "C", "D"]
        expected = {
            ("A", "A"): True, ("A", "B"): True, ("A", "C"): True, ("A", "D"): True,
            ("B", "A"): False, ("B", "B"): True, ("B", "C"): True, ("B", "D"): True,
            ("C", "A"): False, ("C", "B"): False, ("C", "C"): True, ("C", "D"): True,
            ("D", "A"): False, ("D", "B"): False, ("D", "C"): False, ("D", "D"): True,
        }
        for (mine, req), result in expected.items():
            assert grade_meets_requirement(mine, req) is result, (
                f"grade_meets_requirement({mine!r}, {req!r}) should be {result}"
            )

    def test_unknown_grade_fails(self) -> None:
        """Unknown grades return False."""
        assert grade_meets_requirement("X", "A") is False
        assert grade_meets_requirement("A", "X") is False
