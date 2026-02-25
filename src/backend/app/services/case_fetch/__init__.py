"""Case fetch package — F-001 案件自動収集.

Adapter-based architecture for fetching cases from multiple sources.
Each source has its own adapter implementing BaseSourceAdapter.

Modules:
    base_adapter      — BaseSourceAdapter ABC + RawCase / StoreResult
    chotatku_adapter  — ChotatkuPortalAdapter (調達ポータル)
    normalizer        — CaseNormalizer (正規化 + 差分検知)
"""
