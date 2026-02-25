"""Grade comparison utilities for F-003.

Compares company grade against case requirements using the JQA unified
qualification grade hierarchy: A > B > C > D.
"""

from __future__ import annotations

# Grade hierarchy: lower number = higher rank
GRADE_ORDER: dict[str, int] = {"A": 1, "B": 2, "C": 3, "D": 4}


def grade_meets_requirement(mine: str, required: str) -> bool:
    """Check if the company's grade meets the required grade.

    A company with a higher-ranked grade (e.g. A) meets a requirement
    for a lower-ranked grade (e.g. C).  Equal grades also pass.

    Returns False if either grade is not in the known hierarchy.
    """
    mine_rank = GRADE_ORDER.get(mine.upper())
    req_rank = GRADE_ORDER.get(required.upper())
    if mine_rank is None or req_rank is None:
        return False
    return mine_rank <= req_rank
