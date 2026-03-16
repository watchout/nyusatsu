#!/usr/bin/env python3
"""
案件収集バッチスクリプト（MVP）
"""
import asyncio
import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.adapters.chotatku_portal import ChotatkuPortalAdapter
from app.services.scoring import add_score_to_cases
from app.models.batch_log import BatchLog
from app.core.database import get_db
from datetime import datetime, timezone


async def main():
    print("=== 案件収集バッチ開始 ===")
    
    # アダプター初期化
    adapter = ChotatkuPortalAdapter()
    
    # バッチログ作成
    batch_log = BatchLog(
        source=adapter.source_name,
        feature_origin="F-001",
        batch_type="case_collection",
        started_at=datetime.now(timezone.utc),
        status="running",
    )
    
    try:
        # 1. データ取得
        print(f"[1/4] {adapter.source_name} から案件取得中...")
        raw_cases = await adapter.fetch()
        print(f"  → {len(raw_cases)}件取得")
        
        # 2. フィルタリング
        print("[2/4] フィルタリング中...")
        filtered_cases = adapter.filter_cases(raw_cases)
        print(f"  → {len(filtered_cases)}件がキーワードに合致")
        
        # 3. DB格納
        print("[3/4] DB格納中...")
        store_result = await adapter.store(filtered_cases)
        print(f"  → 新規: {store_result.new}件")
        print(f"  → 更新: {store_result.updated}件")
        print(f"  → 変更なし: {store_result.unchanged}件")
        print(f"  → エラー: {store_result.errors}件")
        
        # 4. スコアリング
        print("[4/4] スコアリング中...")
        from app.models.case import Case
        from sqlalchemy import select, update
        
        async for db in get_db():
            # 全アクティブ案件取得
            result = await db.execute(
                select(Case).where(Case.status == "new")
            )
            active_cases = result.scalars().all()
            
            # スコア計算
            cases_dict = [
                {
                    "id": str(c.id),
                    "submission_deadline": c.submission_deadline,
                }
                for c in active_cases
            ]
            scored_cases = add_score_to_cases(cases_dict)
            
            # スコア更新
            for case in scored_cases:
                await db.execute(
                    update(Case)
                    .where(Case.id == case["id"])
                    .values(
                        score=case["score"],
                        score_detail=case["score_detail"]
                    )
                )
            
            await db.commit()
            print(f"  → {len(scored_cases)}件にスコア付与")
        
        # バッチログ更新
        batch_log.finished_at = datetime.now(timezone.utc)
        batch_log.status = "success"
        batch_log.total_fetched = len(raw_cases)
        batch_log.new_count = store_result.new
        batch_log.updated_count = store_result.updated
        batch_log.unchanged_count = store_result.unchanged
        batch_log.error_count = store_result.errors
        batch_log.error_details = store_result.error_details
        
        async for db in get_db():
            db.add(batch_log)
            await db.commit()
        
        print("=== 完了 ===")
        
    except Exception as e:
        print(f"エラー: {e}")
        batch_log.finished_at = datetime.now(timezone.utc)
        batch_log.status = "failed"
        batch_log.error_details = [{"error": str(e)}]
        
        async for db in get_db():
            db.add(batch_log)
            await db.commit()
        
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
