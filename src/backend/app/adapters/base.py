"""
BaseSourceAdapter - データソースアダプターの基底クラス
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class RawCase:
    """データソースから取得した生データ"""
    source_id: str
    case_name: str
    issuing_org: str
    submission_deadline: Optional[datetime] = None
    opening_date: Optional[datetime] = None
    spec_url: Optional[str] = None
    notice_url: Optional[str] = None
    detail_url: Optional[str] = None
    bid_type: Optional[str] = None
    category: Optional[str] = None
    region: Optional[str] = None
    grade: Optional[str] = None
    issuing_org_code: Optional[str] = None
    raw_html: Optional[str] = None
    raw_dict: Optional[dict] = None


@dataclass
class StoreResult:
    """格納結果"""
    total: int
    new: int
    updated: int
    unchanged: int
    errors: int
    error_details: List[dict]


class BaseSourceAdapter(ABC):
    """データソースアダプターの基底クラス"""
    
    def __init__(self, source_name: str):
        self.source_name = source_name
    
    @abstractmethod
    async def fetch(self) -> List[RawCase]:
        """データソースからデータ取得"""
        pass
    
    @abstractmethod
    def normalize(self, raw: RawCase) -> dict:
        """統一スキーマに変換"""
        pass
    
    async def store(self, cases: List[RawCase]) -> StoreResult:
        """DB格納（UPSERT + 差分検知）"""
        from app.core.database import get_db
        from app.models.case import Case
        from sqlalchemy import select
        from sqlalchemy.dialects.postgresql import insert
        
        result = StoreResult(
            total=len(cases),
            new=0,
            updated=0,
            unchanged=0,
            errors=0,
            error_details=[]
        )
        
        async for db in get_db():
            for raw in cases:
                try:
                    normalized = self.normalize(raw)
                    
                    # UPSERT
                    stmt = insert(Case).values(**normalized)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['source', 'source_id'],
                        set_={
                            **normalized,
                            'last_updated_at': datetime.utcnow()
                        }
                    )
                    
                    # 新規 or 更新の判定
                    existing = await db.execute(
                        select(Case).where(
                            Case.source == normalized['source'],
                            Case.source_id == normalized['source_id']
                        )
                    )
                    existing_case = existing.scalar_one_or_none()
                    
                    await db.execute(stmt)
                    
                    if existing_case is None:
                        result.new += 1
                    elif self._has_changes(existing_case, normalized):
                        result.updated += 1
                    else:
                        result.unchanged += 1
                        
                except Exception as e:
                    result.errors += 1
                    result.error_details.append({
                        'source_id': raw.source_id,
                        'error': str(e)
                    })
            
            await db.commit()
        
        return result
    
    def _has_changes(self, existing: 'Case', new: dict) -> bool:
        """変更があるかチェック"""
        compare_fields = ['case_name', 'submission_deadline', 'opening_date']
        for field in compare_fields:
            if getattr(existing, field) != new.get(field):
                return True
        return False
