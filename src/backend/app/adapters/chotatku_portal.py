"""
ChotatkuPortalAdapter - 調達ポータル公告収集
最小MVP: HTMLスクレイピング + 基本フィルタリング
"""
from datetime import datetime

from .base import BaseSourceAdapter, RawCase


class ChotatkuPortalAdapter(BaseSourceAdapter):
    """調達ポータル入札公告アダプター"""
    
    BASE_URL = "https://www.p-portal.go.jp"
    
    def __init__(self):
        super().__init__("chotatku_portal")
        self.keywords = ["軽運送", "配送", "物品", "清掃", "内装"]
    
    async def fetch(self) -> list[RawCase]:
        """調達ポータルから案件取得（MVP: モックデータ）"""
        # TODO: 実際のスクレイピング実装
        # Phase1では調達ポータルのHTML構造調査が必要
        # MVPでは動作確認用のモックデータを返す
        
        cases = []
        
        # モックデータ（動作確認用）
        mock_cases = [
            {
                "source_id": "mock_001",
                "case_name": "○○省 軽運送業務委託",
                "issuing_org": "○○省 ○○局",
                "submission_deadline": "2026-03-25 17:00",
                "opening_date": "2026-03-28 10:00",
                "notice_url": f"{self.BASE_URL}/mock/001",
                "bid_type": "一般競争入札",
            },
            {
                "source_id": "mock_002",
                "case_name": "△△市 物品購入",
                "issuing_org": "△△市役所",
                "submission_deadline": "2026-03-30 17:00",
                "opening_date": "2026-04-05 14:00",
                "notice_url": f"{self.BASE_URL}/mock/002",
                "bid_type": "一般競争入札",
            },
            {
                "source_id": "mock_003",
                "case_name": "□□県 清掃業務",
                "issuing_org": "□□県庁",
                "submission_deadline": "2026-03-20 17:00",
                "opening_date": "2026-03-22 10:00",
                "notice_url": f"{self.BASE_URL}/mock/003",
                "bid_type": "一般競争入札",
            },
        ]
        
        for mock in mock_cases:
            cases.append(RawCase(
                source_id=mock["source_id"],
                case_name=mock["case_name"],
                issuing_org=mock["issuing_org"],
                submission_deadline=datetime.strptime(
                    mock["submission_deadline"], "%Y-%m-%d %H:%M"
                ) if mock.get("submission_deadline") else None,
                opening_date=datetime.strptime(
                    mock["opening_date"], "%Y-%m-%d %H:%M"
                ) if mock.get("opening_date") else None,
                notice_url=mock.get("notice_url"),
                bid_type=mock.get("bid_type"),
                raw_dict=mock,
            ))
        
        return cases
    
    def normalize(self, raw: RawCase) -> dict:
        """統一スキーマに変換"""
        return {
            "source": self.source_name,
            "source_id": raw.source_id,
            "case_name": raw.case_name,
            "issuing_org": raw.issuing_org,
            "issuing_org_code": raw.issuing_org_code,
            "bid_type": raw.bid_type,
            "category": raw.category,
            "region": raw.region,
            "grade": raw.grade,
            "submission_deadline": raw.submission_deadline,
            "opening_date": raw.opening_date,
            "spec_url": raw.spec_url,
            "notice_url": raw.notice_url,
            "detail_url": raw.detail_url,
            "status": "new",
            "raw_data": raw.raw_dict or {},
        }
    
    def filter_cases(self, cases: list[RawCase]) -> list[RawCase]:
        """キーワードフィルタリング（MVP: 簡易版）"""
        filtered = []
        
        for case in cases:
            # キーワードマッチ（OR条件）
            if any(kw in case.case_name for kw in self.keywords):
                filtered.append(case)
        
        return filtered
