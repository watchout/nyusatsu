#!/bin/bash
# nyusatsu VPS Docker セットアップスクリプト
# 実行方法: VPSで bash vps-docker-setup.sh

set -e

echo "=== nyusatsu VPS Docker セットアップ ==="
echo ""

# 1. Docker インストール確認
echo "[1/5] Docker確認..."
if ! command -v docker &> /dev/null; then
    echo "Dockerをインストールします..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    echo "⚠️  ログアウト→再ログインしてDockerグループを反映してください"
    exit 0
else
    echo "✅ Docker already installed"
fi

# 2. Docker Compose確認
echo ""
echo "[2/5] Docker Compose確認..."
if ! command -v docker-compose &> /dev/null; then
    echo "Docker Composeをインストールします..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
else
    echo "✅ Docker Compose already installed"
fi

# 3. リポジトリクローン
echo ""
echo "[3/5] リポジトリ確認..."
if [ ! -d "/home/yuji/nyusatsu" ]; then
    echo "リポジトリをクローンしますか？ (y/n)"
    read -r CLONE_REPO
    if [ "$CLONE_REPO" = "y" ]; then
        echo "リポジトリURL:"
        read -r REPO_URL
        cd /home/yuji
        git clone "$REPO_URL" nyusatsu
    fi
else
    echo "✅ リポジトリ already exists"
fi

cd /home/yuji/nyusatsu

# 4. .env作成
echo ""
echo "[4/5] 環境変数設定..."
if [ ! -f ".env" ]; then
    echo "PostgreSQLパスワードを設定してください:"
    read -sp "DB_PASSWORD: " DB_PASSWORD
    echo ""
    echo "Claude API Keyを設定してください:"
    read -sp "CLAUDE_API_KEY: " CLAUDE_KEY
    echo ""
    echo "日次トークン上限 (推奨: 100000):"
    read -r TOKEN_LIMIT
    TOKEN_LIMIT=${TOKEN_LIMIT:-100000}

    cat > .env << EOF
DB_PASSWORD=$DB_PASSWORD
CLAUDE_API_KEY=$CLAUDE_KEY
LLM_DAILY_TOKEN_LIMIT=$TOKEN_LIMIT
EOF
    chmod 600 .env
    echo "✅ .env作成完了"
else
    echo "✅ .env already exists"
fi

# 5. データディレクトリ作成
mkdir -p data/raw logs

# 6. Nginx設定（参考）
echo ""
echo "[5/5] 完了 ✅"
echo ""
echo "=== 次のステップ ==="
echo "1. GitHub Container Registryにログイン:"
echo "   echo <GITHUB_TOKEN> | docker login ghcr.io -u <USERNAME> --password-stdin"
echo ""
echo "2. コンテナ起動:"
echo "   docker-compose -f docker-compose.prod.yml up -d"
echo ""
echo "3. ログ確認:"
echo "   docker-compose -f docker-compose.prod.yml logs -f app"
echo ""
echo "4. ヘルスチェック:"
echo "   curl http://localhost:3300/api/v1/health"
echo ""
echo "5. Nginx設定例 (/etc/nginx/sites-available/nyusatsu):"
echo ""
cat << 'NGINX'
server {
    listen 80;
    server_name nyusatsu.example.com;

    location / {
        proxy_pass http://127.0.0.1:3300;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
NGINX
