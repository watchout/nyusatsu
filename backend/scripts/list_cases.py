#!/usr/bin/env python3
"""
案件一覧表示CLI（MVP）
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.case import Case
from app.database import get_db
from sqlalchemy import select


async def main():
    print("=" * 80)
    print("案件一覧（スコア順）")
    print("=" * 80)
    
    async for db in get_db():
        result = await db.execute(
            select(Case)
            .where(Case.status == "new")
            .order_by(Case.score.desc())
        )
        cases = result.scalars().all()
        
        if not cases:
            print("案件がありません")
            return
        
        for i, case in enumerate(cases, 1):
            print(f"\n[{i}] スコア: {case.score or 0}点")
            print(f"  案件名: {case.case_name}")
            print(f"  発注機関: {case.issuing_org}")
            print(f"  提出期限: {case.submission_deadline}")
            print(f"  開札日: {case.opening_date}")
            print(f"  公告URL: {case.notice_url}")
            
            if case.score_detail:
                print(f"  スコア詳細: {case.score_detail}")
        
        print(f"\n合計: {len(cases)}件")


if __name__ == "__main__":
    asyncio.run(main())
