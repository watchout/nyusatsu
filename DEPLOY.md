# nyusatsu デプロイ手順

## GitHub Actions自動デプロイ方式

### 1. 初回セットアップ（VPS側）

```bash
# VPSにログイン
ssh yuji@160.251.209.16

# セットアップスクリプト実行
cd /home/yuji
git clone <repository-url> nyusatsu
cd nyusatsu
bash scripts/vps-docker-setup.sh
```

対話形式で入力：
- PostgreSQLパスワード
- Claude API Key
- 日次トークン上限

### 2. GitHub Container Registryログイン

```bash
# GitHubトークン生成（Settings > Developer settings > Personal access tokens）
# 権限: read:packages

echo <GITHUB_TOKEN> | docker login ghcr.io -u watchout --password-stdin
```

### 3. コンテナ起動

```bash
cd /home/yuji/nyusatsu
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d
```

### 4. 動作確認

```bash
# ログ確認
docker-compose -f docker-compose.prod.yml logs -f app

# ヘルスチェック
curl http://localhost:3300/api/v1/health
```

### 5. Nginx設定（ドメイン公開）

```bash
sudo nano /etc/nginx/sites-available/nyusatsu
```

```nginx
server {
    listen 80;
    server_name nyusatsu.iyasaka.co;  # ドメイン

    location / {
        proxy_pass http://127.0.0.1:3300;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/nyusatsu /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# SSL証明書（Let's Encrypt）
sudo certbot --nginx -d nyusatsu.iyasaka.co
```

---

## 自動デプロイフロー

### mainブランチへpush → 自動デプロイ

```bash
# ローカルで開発
git add .
git commit -m "feat: ..."
git push origin main
```

**自動実行される処理**：
1. GitHub Actionsがコンテナイメージビルド
2. ghcr.io/watchout/nyusatsu:latestにpush
3. VPS上のWatchtowerが5分ごとに新イメージ検知
4. 自動でコンテナ再起動

---

## cron設定（バッチ処理）

```bash
# crontab編集
crontab -e
```

```cron
# 毎日6:00 案件取得
0 6 * * * docker exec nyusatsu-app python -m app.scripts.run_case_fetch >> /var/log/nyusatsu/cron.log 2>&1

# 毎日7:00 AI処理実行
0 7 * * * docker exec nyusatsu-app python -m app.scripts.run_cascade >> /var/log/nyusatsu/cron.log 2>&1

# 30分ごと スタック検出
*/30 * * * * docker exec nyusatsu-app python -m app.scripts.run_stuck_detector >> /var/log/nyusatsu/cron.log 2>&1
```

---

## トラブルシューティング

### コンテナが起動しない
```bash
docker-compose -f docker-compose.prod.yml logs app
```

### データベース接続エラー
```bash
docker-compose -f docker-compose.prod.yml exec postgres psql -U nyusatsu -d nyusatsu
```

### 手動でイメージ更新
```bash
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d
```

---

## コスト監視

### トークン使用量確認
```bash
docker exec nyusatsu-app python -m app.scripts.health_check
```

### 日次上限の調整
```bash
# .envを編集
nano .env
# LLM_DAILY_TOKEN_LIMIT=200000  # 値を変更

# コンテナ再起動
docker-compose -f docker-compose.prod.yml restart app
```
