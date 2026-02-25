"""OD (Open Data) import package — F-005 Layer 1.

Downloads CSV from the government procurement open data portal,
parses rows into normalized dicts, and upserts into base_bids.

Modules:
    downloader — HTTP download + ZIP extraction + raw file storage
    parser     — CSV parse + normalize amounts / dates
    importer   — source_id dedup → INSERT or UPSERT into base_bids
"""
