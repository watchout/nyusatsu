"""Fixture factories for CompanyProfile model."""

from __future__ import annotations


def make_company_profile_data(**overrides) -> dict:
    """Return a dict of valid CompanyProfile fields for testing."""
    defaults = {
        "unified_qualification": True,
        "grade": "D",
        "business_categories": ["物品の販売", "役務の提供その他"],
        "regions": ["関東・甲信越"],
        "licenses": [],
        "certifications": [],
        "experience": [],
        "subcontractors": [
            {"name": "テスト運輸", "license": "運送業", "capabilities": ["軽運送"]},
        ],
    }
    defaults.update(overrides)
    return defaults
