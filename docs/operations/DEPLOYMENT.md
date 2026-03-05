# デプロイ手順書 (DEPLOYMENT)

> **バージョン**: v1.0
> **最終更新**: 2026-03-05
> **対象**: 入札ラクダAI P0 (Phase1 MVP)

---

## 前提条件

- Python 3.12+
- PostgreSQL 15+ (ポート 5433)
- uv (Python パッケージマネージャー)
- bun (フロントエンド)

---

## 1. 初期セットアップ

### 1.1 リポジトリクローン

```bash
git clone <repository-url> nyusatsu
cd nyusatsu
```

### 1.2 環境変数設定

```bash
cp .env.example .env
# .env を編集して以下を設定:
#   DATABASE_URL=postgresql+asyncpg://nyusatsu:PASSWORD@localhost:5433/nyusatsu
#   LLM_API_KEY=sk-ant-...（本番用キー）
#   APP_ENV=production
#   LLM_DAILY_TOKEN_LIMIT=（適切な値を設定）
```

### 1.3 ディレクトリ作成

```bash
mkdir -p data/raw logs
```

### 1.4 バックエンド依存パッケージ

```bash
cd src/backend
uv sync
```

### 1.5 フロントエンド依存パッケージ

```bash
cd src/frontend
bun install
```

---

## 2. データベースセットアップ

### 2.1 PostgreSQL 起動確認

```bash
psql -h localhost -p 5433 -U nyusatsu -c "SELECT 1;"
```

### 2.2 マイグレーション実行

```bash
cd src/backend
uv run alembic upgrade head
```

---

## 3. アプリケーション起動

### 3.1 バックエンド

```bash
cd src/backend
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3.2 フロントエンド

```bash
cd src/frontend
bun run dev
```

### 3.3 起動確認

```bash
curl http://localhost:8000/api/v1/health
# 期待: {"data": {"status": "ok", "db": "connected"}}
```

---

## 4. バッチスケジュール設定

### 4.1 crontab 設定

```bash
# crontab.example を編集して PROJ_DIR を設定
sed -i '' "s|/path/to/nyusatsu|$(pwd)|g" src/backend/crontab.example
crontab src/backend/crontab.example
```

### 4.2 手動実行で動作確認

```bash
cd src/backend
uv run python -m app.scripts.run_case_fetch
uv run python -m app.scripts.run_cascade
uv run python -m app.scripts.run_stuck_detector
uv run python -m app.scripts.health_check
```

---

## 5. 本番運用チェック

LAUNCH_CHECKLIST.md の全項目を確認すること。

```bash
# ヘルスチェック
uv run python -m app.scripts.health_check

# crontab 確認
crontab -l
```

---

## 6. 本番環境の環境変数

| 変数 | 説明 | 本番設定 |
|------|------|----------|
| `DATABASE_URL` | PostgreSQL 接続文字列 | 本番DB URL (`?ssl=require`) |
| `LLM_API_KEY` | Claude API キー | 本番用キー |
| `LLM_MODEL` | 使用モデル | `claude-sonnet-4-20250514` |
| `APP_ENV` | 環境 | `production` |
| `APP_LOG_LEVEL` | ログレベル | `INFO` |
| `LLM_DAILY_TOKEN_LIMIT` | 日次トークン上限 | 計測値に基づき設定 |
| `DATABASE_POOL_SIZE` | DB接続プール | `5`（負荷に応じて調整） |
| `DATABASE_MAX_OVERFLOW` | DB最大接続数 | `10` |
