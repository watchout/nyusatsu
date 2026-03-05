#!/bin/bash
# nyusatsu VPSセットアップスクリプト
# 実行方法: VPSにログインして bash vps-setup.sh

set -e

echo "=== nyusatsu VPSセットアップ ==="
echo ""

# 1. PostgreSQL インストール確認
echo "[1/7] PostgreSQL確認..."
if ! command -v psql &> /dev/null; then
    echo "PostgreSQLをインストールします..."
    sudo apt update
    sudo apt install -y postgresql postgresql-contrib
    sudo systemctl enable postgresql
    sudo systemctl start postgresql
else
    echo "✅ PostgreSQL already installed"
fi

# 2. Python 3.12 確認
echo ""
echo "[2/7] Python 3.12確認..."
if ! command -v python3.12 &> /dev/null; then
    echo "Python 3.12をインストールします..."
    sudo apt update
    sudo apt install -y software-properties-common
    sudo add-apt-repository -y ppa:deadsnakes/ppa
    sudo apt install -y python3.12 python3.12-venv python3.12-dev
else
    echo "✅ Python 3.12 already installed"
fi

# 3. uv インストール
echo ""
echo "[3/7] uvインストール..."
if ! command -v uv &> /dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.cargo/env
else
    echo "✅ uv already installed"
fi

# 4. データベース作成
echo ""
echo "[4/7] PostgreSQLデータベース作成..."
echo "⚠️  PostgreSQLパスワードを設定します（入力は表示されません）"
read -sp "nyusatsuユーザーのパスワード: " DB_PASSWORD
echo ""

sudo -u postgres psql << EOF
-- データベース作成
DROP DATABASE IF EXISTS nyusatsu;
CREATE DATABASE nyusatsu;

-- ユーザー作成
DROP USER IF EXISTS nyusatsu;
CREATE USER nyusatsu WITH PASSWORD '$DB_PASSWORD';

-- 権限付与
GRANT ALL PRIVILEGES ON DATABASE nyusatsu TO nyusatsu;
ALTER DATABASE nyusatsu OWNER TO nyusatsu;

-- 接続確認
\c nyusatsu
GRANT ALL ON SCHEMA public TO nyusatsu;
EOF

echo "✅ データベース作成完了"

# 5. リポジトリクローン（存在しない場合）
echo ""
echo "[5/7] リポジトリ確認..."
if [ ! -d "/home/yuji/nyusatsu" ]; then
    echo "リポジトリURLを入力してください:"
    read REPO_URL
    cd /home/yuji
    git clone "$REPO_URL" nyusatsu
else
    echo "✅ リポジトリ already exists"
    cd /home/yuji/nyusatsu
    git pull
fi

cd /home/yuji/nyusatsu

# 6. .env作成
echo ""
echo "[6/7] 環境変数設定..."
echo "⚠️  Claude API Keyを入力してください:"
read -sp "CLAUDE_API_KEY: " CLAUDE_KEY
echo ""

cat > .env << EOF
# === データベース ===
DATABASE_URL=postgresql+asyncpg://nyusatsu:$DB_PASSWORD@localhost:5432/nyusatsu
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10

# === LLM API ===
LLM_API_KEY=$CLAUDE_KEY
LLM_MODEL=claude-sonnet-4-20250514
LLM_MAX_TOKENS=4096

# === アプリケーション ===
APP_ENV=production
APP_LOG_LEVEL=INFO
APP_LOG_DIR=logs/

# === バッチ ===
BATCH_SCHEDULE_CASE_FETCH=0 6 * * *
BATCH_SCHEDULE_OD_IMPORT=0 6 * * *
BATCH_SCHEDULE_DETAIL_SCRAPE=0 7 * * *

# === データ保存 ===
DATA_RAW_DIR=data/raw/

# === コスト制御 ===
LLM_DAILY_TOKEN_LIMIT=100000
EOF

chmod 600 .env
echo "✅ .env作成完了"

# 7. ディレクトリ・依存関係
echo ""
echo "[7/7] 最終セットアップ..."
mkdir -p data/raw logs

cd src/backend
uv sync

# マイグレーション実行
uv run alembic upgrade head

echo ""
echo "=== セットアップ完了 ✅ ==="
echo ""
echo "次のステップ:"
echo "1. サーバー起動: cd /home/yuji/nyusatsu/src/backend && uv run uvicorn app.main:app --host 0.0.0.0 --port 3300"
echo "2. ヘルスチェック: curl http://localhost:3300/api/v1/health"
echo "3. cron設定: crontab /home/yuji/nyusatsu/src/backend/crontab.example"
