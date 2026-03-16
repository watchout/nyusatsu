"""
簡易スコアリングサービス（MVP）
期限余裕のみでスコアリング
"""
from datetime import datetime, timedelta, timezone


def calculate_simple_score(case: dict) -> int:
    """簡易スコア算出（期限余裕のみ、0-100点）"""
    if not case.get("submission_deadline"):
        return 50  # デフォルト
    
    deadline = case["submission_deadline"]
    if isinstance(deadline, str):
        deadline = datetime.fromisoformat(deadline)
    
    # timezone-aware datetime に統一
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    
    now = datetime.now(timezone.utc)
    days_left = (deadline - now).days
    
    # 期限余裕でスコアリング
    if days_left >= 14:
        return 100
    elif days_left >= 10:
        return 80
    elif days_left >= 7:
        return 60
    elif days_left >= 4:
        return 40
    elif days_left >= 1:
        return 20
    else:
        return 0


def add_score_to_cases(cases: list) -> list:
    """案件リストにスコアを追加"""
    for case in cases:
        case["score"] = calculate_simple_score(case)
        case["score_detail"] = {
            "deadline_score": case["score"],
            "method": "simple_deadline_only"
        }
    
    return cases
