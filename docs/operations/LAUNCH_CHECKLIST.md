# 運用開始チェックリスト (LAUNCH CHECKLIST)

> **バージョン**: v1.0
> **最終更新**: 2026-02-26
> **対象**: 入札ラクダAI P0 (Phase1 MVP)

---

## 運用開始前チェック

### インフラ

- [ ] PostgreSQL が起動し接続可能（`psql -h localhost -p 5433 -U nyusatsu`）
- [ ] `alembic upgrade head` でマイグレーション完了
- [ ] `data/raw/` ディレクトリが存在し書き込み可能
- [ ] `logs/` ディレクトリが存在し書き込み可能
- [ ] `.env` ファイルが設定済み（DATABASE_URL, LLM_API_KEY 等）

### アプリケーション

- [ ] `uv run uvicorn app.main:app` でサーバー起動確認
- [ ] `GET /api/v1/health` が 200 を返す
- [ ] `uv run pytest tests/` が全テスト PASS

### ヘルスチェック

- [ ] `uv run python -m app.scripts.health_check` が exit 0 で通過する
- [ ] 過去 24h に全 4 バッチが 1 回以上成功している（初回は手動実行）
- [ ] スタック案件が 0 件
- [ ] サーキットブレーカが closed 状態（llm_circuit_open イベントなし）

### コスト制御

- [ ] `LLM_DAILY_TOKEN_LIMIT` が計測値に基づいて設定されている（0=無制限のままの場合は要確認）

### 会社プロフィール

- [ ] `company_profile` の 4 必須フィールドが入力済み:
  - [ ] `unified_qualification`（全省庁統一資格）
  - [ ] `grade`（等級: A/B/C/D）
  - [ ] `business_categories`（営業品目）
  - [ ] `regions`（競争参加地域）

### バッチスケジュール

- [ ] crontab が設定済み（`crontab -l` で確認）
- [ ] 各バッチの手動実行が成功:
  - [ ] `uv run python -m app.scripts.run_case_fetch`
  - [ ] `uv run python -m app.scripts.run_cascade`
  - [ ] `uv run python -m app.scripts.run_stuck_detector`
  - [ ] `uv run python -m app.scripts.health_check`

### ドキュメント

- [ ] RUNBOOK.md が最新の手順と一致している

---

## 異常時の確認順序

```
health_check → batch_logs → case_events → logs/app.log
```

## 復旧優先度

```
サーキットブレーカ > スタック > バッチ失敗 > 個別案件エラー
```
