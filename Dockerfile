# nyusatsu Dockerfile (FastAPI + Vite)
FROM python:3.12-slim AS backend-builder

WORKDIR /app

# uv インストール
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# バックエンド依存関係
COPY src/backend/pyproject.toml src/backend/uv.lock ./
RUN uv sync --frozen --no-dev

# バックエンドコード
COPY src/backend ./

# ===== フロントエンド ビルド =====
FROM node:20-slim AS frontend-builder

WORKDIR /app

COPY src/frontend/package.json ./
RUN npm install

COPY src/frontend ./
RUN npx vite build

# ===== 最終イメージ =====
FROM python:3.12-slim

WORKDIR /app

# uv インストール
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# PostgreSQLクライアント（alembic用）
RUN apt-get update && apt-get install -y \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# バックエンド
COPY --from=backend-builder /app/.venv /app/.venv
COPY --from=backend-builder /app /app

# フロントエンド（ビルド済み）
COPY --from=frontend-builder /app/dist /app/static

# データディレクトリ
RUN mkdir -p data/raw logs

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
