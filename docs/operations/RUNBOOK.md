# 運用マニュアル (RUNBOOK)

> **バージョン**: v1.0
> **最終更新**: 2026-02-26
> **対象**: 入札ラクダAI P0 (Phase1 MVP)
> **参照**: SSOT-5 §7

---

## 目次

1. [日常確認](#1-日常確認)
2. [バッチ手動トリガー](#2-バッチ手動トリガー)
3. [スタック案件の復旧](#3-スタック案件の復旧)
4. [サーキットブレーカ発動時の対応](#4-サーキットブレーカ発動時の対応)
5. [バッチ全体失敗の対応](#5-バッチ全体失敗の対応)
6. [データ不整合の復旧](#6-データ不整合の復旧)
7. [DBバックアップ/リストア](#7-dbバックアップリストア)
8. [異常時の確認順序](#8-異常時の確認順序)

---

## 1. 日常確認

### health_check の実行

```bash
cd src/backend
uv run python -m app.scripts.health_check
```

**出力**: JSON 形式の構造化レポート（stdout）。

**判読方法**:

| overall_status | 意味 | 対応 |
|---|---|---|
| PASS | 全チェック通過 | 対応不要 |
| FAIL (high_failures > 0) | 致命度 HIGH の問題あり | 即時対応（§3〜§5 参照） |
| FAIL (medium_failures のみ) | 軽度の問題あり | 当日中に確認 |

**5 つのチェック項目**:

| # | チェック | 致命度 | 意味 |
|---|---|---|---|
| 1 | cascade_failure | HIGH | AI 読解/判定パイプラインが全件失敗 |
| 2 | raw_document_storage | HIGH | ファイル保存先が利用不可 |
| 3 | circuit_breaker | HIGH | LLM API サーキットブレーカが発動 |
| 4 | batch_freshness | MEDIUM | 24 時間以上バッチが実行されていない |
| 5 | stuck_cases | MEDIUM | 処理中の案件が 3 件以上滞留 |

### ログ確認

```bash
# 最新のアプリケーションログ
tail -100 src/backend/logs/app.log

# バッチ実行ログ
tail -50 src/backend/logs/cascade.log
tail -50 src/backend/logs/case_fetch.log

# エラーのみ抽出
grep '"level": "error"' src/backend/logs/app.log | tail -20
```

---

## 2. バッチ手動トリガー

### API 経由

```bash
# カスケードパイプライン全体（推奨）
curl -X POST http://localhost:8000/api/v1/batch/trigger

# レスポンス例:
# {"data": {"batch_log_id": "...", "status": "success", ...}}
```

### スクリプト経由

```bash
cd src/backend

# 個別バッチ実行
uv run python -m app.scripts.run_case_fetch       # F-001: 案件収集
uv run python -m app.scripts.run_od_import         # F-005: OpenData インポート
uv run python -m app.scripts.run_detail_scrape     # F-005: 詳細スクレイピング
uv run python -m app.scripts.run_cascade           # F-002→F-003→F-004: AI パイプライン

# スタック検出（5 分毎の cron でも実行）
uv run python -m app.scripts.run_stuck_detector
```

### UI 経由

Dashboard 画面の右上「バッチ実行」ボタンをクリック。

---

## 3. スタック案件の復旧

### 症状

案件が `reading_in_progress` / `judging_in_progress` / `checklist_generating` のまま動かない。

### 自動復旧（通常はこれで解決）

`run_stuck_detector` が 5 分毎に実行され、10 分以上スタックした案件を自動で `*_failed` に遷移。

```bash
# 手動で即座に実行
uv run python -m app.scripts.run_stuck_detector
```

### 手動確認（SQL）

```sql
-- スタック案件の一覧
SELECT id, case_name, current_lifecycle_stage, last_updated_at
FROM cases
WHERE current_lifecycle_stage IN (
    'reading_in_progress',
    'judging_in_progress',
    'checklist_generating'
)
AND last_updated_at < NOW() - INTERVAL '10 minutes';
```

### 手動リカバリ後のリトライ

UI から個別に「再読解」「再判定」ボタンをクリック。または:

```bash
curl -X POST http://localhost:8000/api/v1/cases/{case_id}/actions/retry-reading
curl -X POST http://localhost:8000/api/v1/cases/{case_id}/actions/retry-judging
```

---

## 4. サーキットブレーカ発動時の対応

### 症状

health_check で `circuit_breaker` が FAIL。LLM API が長時間ダウンまたはレート制限。

### 影響範囲

- **影響あり**: F-002（AI 読解）のみ
- **影響なし**: F-001（案件収集）、F-003（判定）、F-004（チェックリスト）、F-005（価格分析）

### 対応手順

1. Claude API の障害情報を確認: https://status.anthropic.com/
2. 一時的な障害なら待機（自動リトライが 3 回まで試行）
3. 長期障害の場合:
   - F-001 と F-005 は通常通り運用を継続
   - LLM 復旧後、失敗案件を一括リトライ:

```bash
# 失敗した読解を再試行
curl -X POST http://localhost:8000/api/v1/batch/trigger
```

### 確認（SQL）

```sql
-- サーキットブレーカ発動イベント
SELECT * FROM case_events
WHERE event_type = 'llm_circuit_open'
ORDER BY created_at DESC
LIMIT 10;
```

---

## 5. バッチ全体失敗の対応

### 症状

health_check で `cascade_failure` が FAIL。

### 確認

```sql
-- 最新のバッチログ
SELECT id, batch_type, feature_origin, status, error_count,
       started_at, finished_at
FROM batch_logs
ORDER BY started_at DESC
LIMIT 10;

-- エラー詳細
SELECT id, batch_type, error_details
FROM batch_logs
WHERE status = 'failed'
ORDER BY started_at DESC
LIMIT 5;
```

### 原因別対応

| 原因 | 対応 |
|---|---|
| データソースの HTML レイアウト変更 | アダプターのパーサーを修正 → 手動バッチトリガー |
| ネットワーク障害 | 時間を置いて手動バッチトリガー |
| DB 接続障害 | DB 復旧を確認 → 手動バッチトリガー |
| CSV スキーマ変更（F-005） | マッピングレイヤを修正 → 手動バッチトリガー |

---

## 6. データ不整合の復旧

### 症状

`cases.current_lifecycle_stage` と `case_events` の最新イベントが不一致。

### 確認

```sql
SELECT c.id, c.case_name, c.current_lifecycle_stage,
       (SELECT to_status FROM case_events
        WHERE case_id = c.id ORDER BY created_at DESC LIMIT 1) AS events_latest
FROM cases c
WHERE c.current_lifecycle_stage != (
    SELECT to_status FROM case_events
    WHERE case_id = c.id ORDER BY created_at DESC LIMIT 1
);
```

### 復旧

case_events を正として cases を修正:

```sql
-- 不整合案件を case_events の最新状態に修正
UPDATE cases SET current_lifecycle_stage = (
    SELECT to_status FROM case_events
    WHERE case_id = cases.id
    ORDER BY created_at DESC LIMIT 1
)
WHERE id IN (
    -- 不整合の案件ID一覧
    SELECT c.id FROM cases c
    WHERE c.current_lifecycle_stage != (
        SELECT to_status FROM case_events
        WHERE case_id = c.id ORDER BY created_at DESC LIMIT 1
    )
);
```

---

## 7. DB バックアップ/リストア

### バックアップ

```bash
# 全体バックアップ
pg_dump -h localhost -p 5433 -U nyusatsu nyusatsu > backup_$(date +%Y%m%d_%H%M%S).sql

# テーブル単位
pg_dump -h localhost -p 5433 -U nyusatsu -t cases nyusatsu > cases_backup.sql
```

### リストア

```bash
# 全体リストア（データベース再作成が必要）
psql -h localhost -p 5433 -U nyusatsu -d nyusatsu < backup_20260226_100000.sql
```

---

## 8. 異常時の確認順序

**復旧優先度**: サーキットブレーカ > スタック > バッチ失敗 > 個別案件エラー

```
1. health_check を実行
   → HIGH アラートがあれば §3〜§5 の該当セクションへ

2. batch_logs を確認
   → 最新バッチの status と error_details を確認

3. case_events を確認
   → 直近のイベントに異常がないか確認

4. ログファイルを確認
   → logs/app.log の ERROR レベルを確認

5. 個別案件を確認
   → UI の CaseDetail 画面で該当案件のステージを確認
```
