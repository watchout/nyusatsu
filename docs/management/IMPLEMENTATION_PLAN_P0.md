# IMPLEMENTATION_PLAN_P0.md — P0 実装タスク分解

> **バージョン**: v1.1
> **最終更新**: 2026-02-18
> **ステータス**: Draft
> **対象マイルストーン**: M5（開発環境）→ M6（Phase0 検証）→ M7（Phase1 MVP）
> **開発者**: 金子 裕司（1人開発）
> **推定期間**: 約 2.5 ヶ月（Effort 合計: S×14 + M×31 + L×10 = 約 65 人日 + Spike 1.5 日）

---

## 変更履歴

| バージョン | 日付 | 変更内容 |
|-----------|------|---------|
| v1.0 | 2026-02-18 | 初版（55タスク: 実装50 + シミュレーション5） |
| v1.1 | 2026-02-18 | Walking Skeleton + fixtures + LLMコスト決定手順 + Spike 3件 + LAUNCH_CHECKLIST 追加 |

---

## 目次

- [概要](#概要)
  - [Walking Skeleton（最小縦切り）](#walking-skeleton最小縦切り)
  - [固定サンプルデータセット（fixtures）](#固定サンプルデータセットfixtures)
- [タスク一覧サマリ](#タスク一覧サマリ)
- [依存関係グラフ](#依存関係グラフ)
- [Phase 0: プロジェクトブートストラップ](#phase-0-プロジェクトブートストラップ)
- [Phase 1: データレイヤー](#phase-1-データレイヤー)
- [Phase 2: 共有インフラ](#phase-2-共有インフラ)
- [Phase 3: F-005 & F-001 実装](#phase-3-f-005--f-001-実装)
- [Phase 4: F-002, F-003, F-004 実装](#phase-4-f-002-f-003-f-004-実装)
- [Phase 5: API レイヤー](#phase-5-api-レイヤー)
- [Phase 6: フロントエンド](#phase-6-フロントエンド)
- [Phase 7: 運用ツール](#phase-7-運用ツール)
- [障害系シミュレーション](#障害系シミュレーション)
- [SSOT 参照マップ](#ssot-参照マップ)

---

## 概要

本ドキュメントは、M4 技術設計ゲート通過後の P0 実装を **55 タスク**（実装 50 + シミュレーション 5）に分解し、Claude Code で順次着手できる形式に整理したものである。

### 設計思想

1. **SSOT 完全準拠**: 全タスクが SSOT-2〜5 + F-001〜F-005 のセクション番号を参照
2. **即着手可能**: 各タスクの Input / Output / DoD を読めば、追加の仕様確認なしに着手可能
3. **テスト駆動**: 全タスクに pytest / vitest テスト要件を DoD に含む
4. **障害系重視**: SIM-01〜05 で障害パターンを再現・検証
5. **Walking Skeleton 優先**: Phase 横断で「1件 E2E」を早期に通す

### Walking Skeleton（最小縦切り）

Phase 0〜7 の順序実行と並行して、以下の最短パスを早期に通すことを推奨する。
「1件が end-to-end で通る」ことで全インフラの結合を検証できる。

| ステップ | 操作 | 依存タスク |
|---------|------|----------|
| 1 | PostgreSQL + seed（company_profile 1件） | TASK-03, 04〜07 |
| 2 | cases テーブルに手動 INSERT（1案件） | TASK-08 |
| 3 | mark-reviewed → mark-planned（手動 or curl） | TASK-10, 22 |
| 4 | cascade_pipeline 実行（F-002→F-003→F-004） | TASK-30 |
| 5 | case_cards / eligibility_results / checklists 確認 | TASK-11 |
| 6 | API 経由で GET /cases/:id?include=all | TASK-33, 34, 35 |
| 7 | フロントエンドで案件詳細 5 タブ表示 | TASK-41〜45 |

> Phase 2 完了 + TASK-23〜30 完了時点で Step 1〜5 を実行可能。
> Phase 5 完了で Step 6、Phase 6 完了で Step 7。

### 固定サンプルデータセット（fixtures）

Phase0 計測・SIM・CI テストの再現性を確保するため、以下のテストデータを用意する。

| # | 種別 | ファイル | 用途 |
|---|------|---------|------|
| 1 | 正常公告 HTML | fixtures/notices/normal.html | F-002 Stage1 正常系 |
| 2 | 正常仕様書 PDF | fixtures/specs/normal.pdf | F-002 Stage1 正常系 |
| 3 | スキャン PDF | fixtures/specs/scanned.pdf | F-002 スキャン検出 |
| 4 | 空 PDF | fixtures/specs/empty.pdf | F-002 エラー系 |
| 5 | OD CSV (10行) | fixtures/od/sample_full.csv | F-005 Layer1 |
| 6 | OD CSV (差分) | fixtures/od/sample_delta.csv | F-005 差分取得 |
| 7 | 落札詳細 HTML | fixtures/details/normal.html | F-005 Layer2 |
| 8 | company_profile JSON | fixtures/seed/company_profile.json | F-003 judgment |

> 配置先: `src/backend/tests/fixtures/`
> DoD 追記: TASK-08 の DoD に「fixtures/ ディレクトリと 8 ファイルのスタブを作成する」を追加。

### Effort 定義

| ランク | 目安 | 説明 |
|-------|------|------|
| S | 0.5 日 | 設定・小規模ユーティリティ |
| M | 1 日 | 標準的なモジュール実装 |
| L | 2 日 | 複雑なロジック・多テーブル操作 |

---

## タスク一覧サマリ

| Phase | タスク数 | Effort 合計 | 概要 |
|-------|---------|------------|------|
| Phase 0 | 3 | 3M = 3日 | FastAPI + React + Docker 環境構築 |
| Phase 1 | 5 | 4M + 1S + 1L = 6.5日 | Alembic + 9テーブル + SQLAlchemy モデル |
| Phase 2 | 7 | 4M + 1S + 2L = 8.5日 | 共有インフラ（エンベロープ・Event・バッチ等） |
| Phase 3 | 7 | 4M + 3L = 10日 | F-005 OD取込 + F-001 案件収集 |
| Phase 4 | 10 | 5M + 1S + 3L + 1S = 11.5日 | F-002 AI読解 + F-003 判定 + F-004 チェックリスト |
| Phase 5 | 6 | 4M + 1S + 1M = 5.5日 | 28 API エンドポイント + Pydantic スキーマ |
| Phase 6 | 8 | 6M + 1L + 1M = 9日 | React 4画面 + API クライアント |
| Phase 7 | 4 | 1M + 3S = 2.5日 | health_check + cron + ログ + 運用マニュアル |
| SIM | 5 | 4S + 1M = 3日 | 障害系シミュレーション 5パターン |
| **合計** | **55** | **約 59.5日** | |

---

## 依存関係グラフ

```
Phase 0 ─────────────────────────────────────────────────────
  TASK-01 (Backend scaffold)  ─┐
  TASK-02 (Frontend scaffold) ─┤── 全て並行可能
  TASK-03 (Docker + .env)     ─┘
                                │
Phase 1 ─────────────────────────────────────────────────────
  TASK-04 (基本テーブル4件)    ← TASK-01,03
    → TASK-05 (依存テーブル3件)
      → TASK-06 (checklists + events)
        → TASK-07 (インデックス + seed)
          → TASK-08 (SQLAlchemy モデル + CRUD)
                                │
Phase 2 ─────────────────────────────────────────────────────
  TASK-09 (エンベロープ)  ─┐
  TASK-15 (設定管理)       ─┤── 並行可能 ← TASK-08
    → TASK-10 (EventService)
    → TASK-11 (VersionManager)
      → TASK-12 (リトライ + サーキットブレーカ) ─┐
      → TASK-13 (LLM 抽象化)                    ─┤── 並行可能
        → TASK-14 (バッチフレームワーク)           ← 10,11,12,15
                                │
Phase 3 ─────────────────────────────────────────────────────
  TASK-16 (F-005 L1: OD CSV)   ← TASK-14
    → TASK-17 (F-005 L2: 詳細スクレイプ)
  TASK-18 (F-001: Adapter)     ← TASK-14
    → TASK-19 (F-001: フィルタ + スコア)  ← 16,17
      → TASK-20 (F-001: batch 統合)
  TASK-21 (価格分析)           ← 16,17
  TASK-22 (案件アクション API)  ← TASK-10
                                │
Phase 4 ─────────────────────────────────────────────────────
  TASK-23 (F-002 S1: フェッチ) ← TASK-11,12,13,14
    → TASK-24 (F-002 S2: LLM抽出)
      → TASK-25 (F-002 S3: エビデンス)
        → TASK-26 (F-003: Hard条件)
          → TASK-27 (F-003: Soft + 判定)
            → TASK-28 (F-004: 変換)
              → TASK-29 (F-004: スケジュール)
                → TASK-30 (cascade orchestrator) ← 23〜29全て
  TASK-31 (スタック検出)       ← TASK-10
  TASK-32 (コスト制御)         ← TASK-13
                                │
Phase 5 ─────────────────────────────────────────────────────
  TASK-33〜38 ← Phase 2〜4 完了後、並行可能
                                │
Phase 6 ─────────────────────────────────────────────────────
  TASK-39 (React scaffold)     ← TASK-02, Phase 5
    → TASK-40〜46              ← 39完了後、並行可能
                                │
Phase 7 ─────────────────────────────────────────────────────
  TASK-47〜50 ← Phase 5 完了後
                                │
SIM ─────────────────────────────────────────────────────────
  SIM-01 ← TASK-31   SIM-02 ← TASK-12,30
  SIM-03 ← TASK-32   SIM-04 ← TASK-10,22
  SIM-05 ← 全Phase完了
```

---

## Phase 0: プロジェクトブートストラップ

> M5 開発環境セットアップ。Pre-Code Gate A 通過が目標。

### TASK-01: バックエンド scaffold

| 項目 | 内容 |
|------|------|
| **Effort** | M（1日） |
| **Dependencies** | なし |
| **SSOT参照** | SSOT-5 §12-1（技術スタック） |

**Input**: SSOT-5 §12-1 の確定技術スタック

**Output**:
```
src/backend/
├── pyproject.toml        # uv, Python 3.12+, FastAPI 0.110+
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI app factory
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py     # Pydantic Settings
│   │   └── database.py   # async engine + session
│   ├── api/
│   │   ├── __init__.py
│   │   └── health.py     # GET /health
│   ├── models/
│   │   └── __init__.py
│   ├── services/
│   │   └── __init__.py
│   └── schemas/
│       └── __init__.py
└── tests/
    ├── conftest.py       # pytest fixtures
    └── test_health.py
```

**DoD**:
1. `uv sync` で依存解決が成功する
2. `uvicorn app.main:app` で起動し `GET /health` が `200 {"status": "ok"}` を返す
3. `pytest tests/test_health.py` が PASS する
4. pyproject.toml に全ライブラリ（fastapi, uvicorn, sqlalchemy, asyncpg, alembic, httpx, tenacity, beautifulsoup4, pdfplumber, pydantic, jpholiday, structlog）が記載されている
5. `app/core/config.py` が `.env` から `DATABASE_URL`, `APP_ENV`, `APP_LOG_LEVEL` を読み込む

---

### TASK-02: フロントエンド scaffold

| 項目 | 内容 |
|------|------|
| **Effort** | M（1日） |
| **Dependencies** | なし |
| **SSOT参照** | SSOT-5 §12-1, SSOT-2 §1（ページ一覧） |

**Input**: SSOT-5 §12-1（React 18+, TypeScript 5.x, bun）

**Output**:
```
src/frontend/
├── package.json          # bun, React 18, TypeScript 5
├── tsconfig.json
├── vite.config.ts
├── src/
│   ├── main.tsx
│   ├── App.tsx           # React Router (/, /cases/:id, /analytics, /settings)
│   ├── components/
│   │   └── Layout.tsx
│   ├── pages/
│   │   ├── Dashboard.tsx
│   │   ├── CaseDetail.tsx
│   │   ├── Analytics.tsx
│   │   └── Settings.tsx
│   ├── services/
│   │   └── api-client.ts  # stub
│   ├── hooks/
│   │   └── index.ts
│   └── types/
│       └── index.ts
└── tests/
    └── App.test.tsx
```

**DoD**:
1. `bun install` が成功する
2. `bun run dev` でローカルサーバーが起動し 4 ルートが表示される
3. `bun run test` で `App.test.tsx` が PASS する
4. TypeScript strict mode が有効で `bun run typecheck` がエラー 0 件

---

### TASK-03: Docker + PostgreSQL + .env

| 項目 | 内容 |
|------|------|
| **Effort** | M（1日） |
| **Dependencies** | なし |
| **SSOT参照** | SSOT-5 §12-3（環境変数一覧） |

**Input**: SSOT-5 §12-3 の全環境変数定義

**Output**:
```
docker-compose.yml        # PostgreSQL 16, port 5432
.env.example              # SSOT-5 §12-3 の全変数（値はプレースホルダ）
.env                      # .gitignore 対象
.gitignore                # .env, __pycache__, node_modules, data/raw/
data/raw/                 # 原文保存ディレクトリ（空）
  ├── portal/
  ├── notices/
  ├── specs/
  ├── texts/
  └── od/
logs/                     # ログ出力ディレクトリ
```

**DoD**:
1. `docker compose up -d` で PostgreSQL 16 が起動する
2. `psql -U user -d nyusatsu -c "SELECT 1"` が成功する
3. `.env.example` に SSOT-5 §12-3 の全 15 環境変数が記載されている
4. `data/raw/` 配下の 5 サブディレクトリが存在する
5. `.gitignore` に `.env`, `data/raw/`, `logs/`, `__pycache__/`, `node_modules/` が含まれる

---

## Phase 1: データレイヤー

> SSOT-4 のテーブル定義を Alembic マイグレーションとして実装。

### TASK-04: Alembic セットアップ + 基本テーブル 4 件

| 項目 | 内容 |
|------|------|
| **Effort** | M（1日） |
| **Dependencies** | TASK-01, TASK-03 |
| **SSOT参照** | SSOT-4 §2-1〜§2-5（company_profiles, base_bids, cases, batch_logs） |

**Input**: SSOT-4 の DDL 定義（4テーブル分）

**Output**:
```
src/backend/
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
│       ├── 001_company_profiles.py
│       ├── 002_base_bids.py
│       ├── 003_cases.py
│       └── 004_batch_logs.py
```

**DoD**:
1. `alembic upgrade head` で 4 テーブルが作成される
2. `alembic downgrade base` で全テーブルが削除される
3. 各テーブルの列定義が SSOT-4 と完全一致する（`\d+ テーブル名` で検証）
4. `cases` テーブルに `UNIQUE(source, source_id)` 制約がある
5. `pytest tests/test_migrations.py` で upgrade/downgrade のラウンドトリップが PASS

---

### TASK-05: 依存テーブル 3 件

| 項目 | 内容 |
|------|------|
| **Effort** | M（1日） |
| **Dependencies** | TASK-04 |
| **SSOT参照** | SSOT-4 §2-3（bid_details）, §2-6（case_cards）, §2-7（eligibility_results） |

**Input**: SSOT-4 DDL + TASK-04 完了状態

**Output**:
```
alembic/versions/
├── 005_bid_details.py
├── 006_case_cards.py
└── 007_eligibility_results.py
```

**DoD**:
1. `alembic upgrade head` で 3 テーブルが追加される
2. `bid_details.base_bid_id` → `base_bids.id` の FK が存在する
3. `case_cards` に `UNIQUE(case_id, version)` + 部分ユニーク `WHERE is_current = true` がある
4. `eligibility_results` に同様のユニーク制約がある
5. `pytest tests/test_migrations.py` が PASS

---

### TASK-06: checklists + case_events テーブル

| 項目 | 内容 |
|------|------|
| **Effort** | M（1日） |
| **Dependencies** | TASK-05 |
| **SSOT参照** | SSOT-4 §2-8（checklists）, §2-9（case_events） |

**Input**: SSOT-4 DDL + TASK-05 完了状態

**Output**:
```
alembic/versions/
├── 008_checklists.py
└── 009_case_events.py
```

**DoD**:
1. `checklists` テーブルに 3 FK（cases, case_cards, eligibility_results）が存在する
2. `checklists` に部分ユニーク `WHERE is_current = true` がある
3. `case_events` の `event_type` が VARCHAR(80) である
4. `case_events` に UPDATE / DELETE のトリガー禁止が文書化されている（コメント）
5. `pytest tests/test_migrations.py` が PASS

---

### TASK-07: インデックス + seed data

| 項目 | 内容 |
|------|------|
| **Effort** | S（0.5日） |
| **Dependencies** | TASK-06 |
| **SSOT参照** | SSOT-4 §5（インデックス定義）, F-003 §3-A（company_profile 初期データ） |

**Input**: SSOT-4 §5 のインデックス一覧 + 金子プロフィール初期データ

**Output**:
```
alembic/versions/
├── 010_indexes.py
└── 011_seed_company_profile.py
```

**DoD**:
1. 全テーブルの `created_at` インデックスが作成される
2. `cases` の `(current_lifecycle_stage, deadline_at)` 複合インデックスが存在する
3. `case_events` の `(case_id, created_at)` インデックスが存在する
4. `company_profiles` に 1 件の初期レコードが INSERT される
5. `SELECT * FROM company_profiles` で `unified_qualification`, `grade`, `business_categories`, `regions` が設定されている

---

### TASK-08: SQLAlchemy モデル + CRUD ベース関数

| 項目 | 内容 |
|------|------|
| **Effort** | L（2日） |
| **Dependencies** | TASK-07 |
| **SSOT参照** | SSOT-4 全セクション, SSOT-5 §5（冪等性）, §6（監査スパイン） |

**Input**: 全テーブル定義 + version/is_current パターン

**Output**:
```
src/backend/app/models/
├── __init__.py
├── base.py              # Base, UUID mixin, TimestampMixin
├── case.py              # Case, LifecycleStage enum
├── batch_log.py         # BatchLog, BatchType enum
├── case_card.py         # CaseCard (version + is_current)
├── eligibility_result.py # EligibilityResult (version + is_current)
├── checklist.py         # Checklist (version + is_current)
├── case_event.py        # CaseEvent (INSERT ONLY)
├── company_profile.py   # CompanyProfile
├── base_bid.py          # BaseBid
└── bid_detail.py        # BidDetail

src/backend/app/services/
└── crud/
    ├── __init__.py
    └── base.py          # get, get_multi, create, update (generic)

src/backend/tests/
├── test_models.py       # 全モデルの CRUD テスト
└── conftest.py          # テスト用 DB fixture (テスト毎にロールバック)
```

**DoD**:
1. 9 テーブル全てに対応する SQLAlchemy 2.0 モデルが定義されている
2. `LifecycleStage` enum が 17 値を持つ（SSOT-4 §1 準拠）
3. CaseCard / EligibilityResult / Checklist に `version`, `is_current` フィールドがある
4. CaseEvent モデルに `update()`, `delete()` メソッドが存在しない（INSERT ONLY 強制）
5. `pytest tests/test_models.py` で全モデルの INSERT / SELECT が PASS する（10テスト以上）
6. conftest.py でテスト毎のトランザクションロールバックが機能する
7. `tests/fixtures/` ディレクトリに 8 ファイルのスタブ（空ファイルまたは最小データ）を作成する（Walking Skeleton / SIM 用）

---

## Phase 2: 共有インフラ

> SSOT-3 / SSOT-5 で定義された横断的パターンを共有モジュールとして実装。

### TASK-09: レスポンスエンベロープ + エラーハンドラ

| 項目 | 内容 |
|------|------|
| **Effort** | M（1日） |
| **Dependencies** | TASK-08 |
| **SSOT参照** | SSOT-3 §3（レスポンス形式）, §5（エラーコード13種） |

**Input**: SSOT-3 §3 のエンベロープ仕様 + §5 のエラーコード一覧

**Output**:
```
src/backend/app/core/
├── response.py          # SuccessResponse, ErrorResponse, PaginatedResponse
├── errors.py            # AppError 基底 + 13 エラークラス
└── exception_handlers.py # FastAPI exception handlers

src/backend/tests/
└── test_response.py
```

**DoD**:
1. `SuccessResponse` が `{"data": ..., "meta": {"timestamp": ..., "request_id": ...}}` 形式を返す
2. `PaginatedResponse` が `meta` に `page, limit, total, total_pages` を含む
3. `ErrorResponse` が `{"data": null, "error": {"code": "...", "message": "...", "details": {}}, "meta": {...}}` 形式
4. 13 エラーコード全て（INVALID_TRANSITION, STAGE_MISMATCH, PIPELINE_IN_PROGRESS, BATCH_ALREADY_RUNNING, CHECKLIST_VERSION_MISMATCH, NOT_FOUND, CASE_CARD_NOT_FOUND, ELIGIBILITY_NOT_FOUND, CHECKLIST_NOT_FOUND, CHECKLIST_ITEM_NOT_FOUND, VALIDATION_ERROR, OVERRIDE_REASON_REQUIRED, SKIP_REASON_REQUIRED）がクラスとして定義されている
5. `pytest tests/test_response.py` が PASS（正常・エラー・ページネーション各1テスト以上）

---

### TASK-10: EventService

| 項目 | 内容 |
|------|------|
| **Effort** | L（2日） |
| **Dependencies** | TASK-08, TASK-09 |
| **SSOT参照** | SSOT-5 §6-1（case_events payload）, SSOT-4 §3-9（整合性ガード）, SSOT-2 §3（40遷移定義） |

**Input**: 27 イベントタイプ定義 + 40 状態遷移テーブル + payload 必須キー

**Output**:
```
src/backend/app/services/
├── event_service.py     # EventService クラス
└── lifecycle.py         # LifecycleManager (遷移テーブル + バリデーション)

src/backend/tests/
├── test_event_service.py
└── test_lifecycle.py
```

**DoD**:
1. `EventService.record_transition(case_id, event_type, from_stage, to_stage, triggered_by, payload)` が以下をアトミックに実行する:
   - `case_events` に INSERT
   - `cases.current_lifecycle_stage` を UPDATE
2. `LifecycleManager.validate_transition(from_stage, to_stage)` が SSOT-2 §3 の 40 遷移を参照し、不正遷移で `INVALID_TRANSITION` を発生させる
3. `expected_lifecycle_stage` 不一致時に `STAGE_MISMATCH (409)` を返す
4. 同じ遷移の重複呼び出しが冪等に処理される（200 OK + 既存イベント返却）
5. `pytest tests/test_event_service.py` で正常遷移・不正遷移・重複呼び出し各 3 テスト以上が PASS
6. `pytest tests/test_lifecycle.py` で 40 遷移の正当性テストが PASS

---

### TASK-11: VersionManager

| 項目 | 内容 |
|------|------|
| **Effort** | M（1日） |
| **Dependencies** | TASK-08 |
| **SSOT参照** | SSOT-4 §6（再実行データモデル）, SSOT-5 §3-2（scope=soft/force） |

**Input**: version + is_current パターン定義

**Output**:
```
src/backend/app/services/
└── version_manager.py   # VersionManager クラス

src/backend/tests/
└── test_version_manager.py
```

**DoD**:
1. `VersionManager.create_new_version(case_id, model_class, data)` が以下をアトミックに実行する:
   - 既存の `is_current=true` レコードを `is_current=false` に UPDATE
   - 新レコードを `version=MAX+1, is_current=true` で INSERT
2. `get_current(case_id, model_class)` が `is_current=true` のレコードを返す
3. `get_all_versions(case_id, model_class)` が全バージョンを version 降順で返す
4. 初回作成（既存なし）で `version=1, is_current=true` が正しく作成される
5. `pytest tests/test_version_manager.py` で初回作成・バージョンアップ・全履歴取得が PASS

---

### TASK-12: リトライラッパー + LLM サーキットブレーカ

| 項目 | 内容 |
|------|------|
| **Effort** | M（1日） |
| **Dependencies** | TASK-08, TASK-15 |
| **SSOT参照** | SSOT-5 §3-4（リトライ定義）, §3-4a（サーキットブレーカ）, §12-2（定数テーブル） |

**Input**: SSOT-5 §12-2 の全リトライ定数 + §3-4a のサーキットブレーカ仕様

**Output**:
```
src/backend/app/core/
├── retry.py             # http_retry, llm_retry, db_retry デコレータ
└── circuit_breaker.py   # LLMCircuitBreaker クラス

src/backend/tests/
├── test_retry.py
└── test_circuit_breaker.py
```

**DoD**:
1. `@http_retry` が tenacity で `max=3, backoff=[30,60,120], timeout=30s` を適用する
2. `@llm_retry` が `max=2, backoff=[10,30], timeout=60s` を適用する
3. `@db_retry` が `max=3, backoff=[1,2,4], timeout=10s` を適用する
4. `LLMCircuitBreaker` が連続 3 件の `llm_api_error` で `open` 状態に遷移し、以降の呼び出しで即座に `llm_circuit_open` エラーを返す
5. `reset()` で `closed` 状態に戻る
6. `pytest tests/test_retry.py` で各リトライパターン（成功・リトライ後成功・全失敗）が PASS
7. `pytest tests/test_circuit_breaker.py` で発動・即失敗・リセットが PASS

---

### TASK-13: LLM 抽象化レイヤー

| 項目 | 内容 |
|------|------|
| **Effort** | M（1日） |
| **Dependencies** | TASK-08, TASK-12 |
| **SSOT参照** | SSOT-5 §1 原則11（LLM Provider 抽象化）, §12-1（Claude API）, §12-3（LLM_API_KEY, LLM_MODEL） |

**Input**: 原則11 の抽象化要件 + Claude API 仕様

**Output**:
```
src/backend/app/services/
├── llm/
│   ├── __init__.py
│   ├── base.py          # LLMProvider ABC (extract, parse_response)
│   ├── claude.py         # ClaudeProvider (httpx + @llm_retry)
│   └── mock.py           # MockProvider (テスト用)

src/backend/tests/
└── test_llm_provider.py
```

**DoD**:
1. `LLMProvider` ABC に `async extract(prompt, text) -> LLMResponse` メソッドが定義されている
2. `ClaudeProvider` が `httpx` で Claude API を呼び出し、`token_usage` (input/output) を返す
3. `MockProvider` が固定レスポンスを返す（テスト用）
4. `@llm_retry` デコレータが適用されている
5. `LLMCircuitBreaker` と連携し、open 状態で即エラーを返す
6. `pytest tests/test_llm_provider.py` で MockProvider を使った正常・エラー・タイムアウトが PASS

---

### TASK-14: バッチフレームワーク

| 項目 | 内容 |
|------|------|
| **Effort** | L（2日） |
| **Dependencies** | TASK-10, TASK-11, TASK-12, TASK-15 |
| **SSOT参照** | SSOT-5 §2（バッチワークフロー全体）, SSOT-3 §7（BATCH_ALREADY_RUNNING） |

**Input**: SSOT-5 §2-1〜§2-5 のバッチ設計 + §12-2 のバッチタイムアウト定数

**Output**:
```
src/backend/app/services/
├── batch/
│   ├── __init__.py
│   ├── base.py          # BaseBatchRunner ABC
│   ├── runner.py         # BatchRunner (排他制御 + ログ + 部分失敗)
│   └── types.py          # BatchType enum, BatchResult

src/backend/tests/
└── test_batch_runner.py
```

**DoD**:
1. `BatchRunner.run(batch_type, source, process_fn)` が以下を実行する:
   - `batch_logs` に `status='running'` で INSERT
   - `process_fn` を各アイテムに適用（失敗しても次へ継続）
   - 完了後: success/partial/failed を判定して `batch_logs` を UPDATE
2. 同一 `batch_type` の並行実行を `BATCH_ALREADY_RUNNING (409)` で拒否する
3. `BATCH_*_TIMEOUT_MIN` 超過でバッチをタイムアウト終了する
4. 部分失敗時に `error_details` JSONB に失敗詳細が記録される
5. `pytest tests/test_batch_runner.py` で全成功・部分失敗・全失敗・排他制御・タイムアウトが PASS

---

### TASK-15: 設定管理

| 項目 | 内容 |
|------|------|
| **Effort** | S（0.5日） |
| **Dependencies** | TASK-08 |
| **SSOT参照** | SSOT-5 §12-2（定数テーブル全 31 定数）, §12-3（環境変数） |

**Input**: SSOT-5 §12-2 の全定数 + §12-3 の環境変数

**Output**:
```
src/backend/app/core/
└── constants.py         # 全31定数を定義

src/backend/tests/
└── test_constants.py
```

**DoD**:
1. SSOT-5 §12-2 の全 31 定数が `constants.py` に UPPER_SNAKE_CASE で定義されている
2. 環境変数で上書き可能な定数（`LLM_DAILY_TOKEN_LIMIT` 等）が `config.py` 経由で読み込まれる
3. `pytest tests/test_constants.py` で定数値の存在と型チェックが PASS

---

## Phase 3: F-005 & F-001 実装

> データ収集の 2 機能を実装。F-005 が先行（F-001 のスコアリングに必要）。

### TASK-16: F-005 Layer1 — OD CSV ダウンロード + パース + base_bids UPSERT

| 項目 | 内容 |
|------|------|
| **Effort** | L（2日） |
| **Dependencies** | TASK-14 |
| **SSOT参照** | F-005 §3-A〜D（Layer1 処理）, SSOT-4 §2-2（base_bids テーブル）, SSOT-5 §4-1（エラーハンドリング） |

**Input**: F-005 仕様書 Layer1 + base_bids DDL

**Output**:
```
src/backend/app/services/
├── od_import/
│   ├── __init__.py
│   ├── downloader.py    # OD CSV ZIP ダウンロード + 解凍
│   ├── parser.py        # CSV パース + 正規化
│   └── importer.py      # base_bids UPSERT (deduplication on source_id)

src/backend/app/batch/
└── od_import.py         # ODImportBatch (BaseBatchRunner 継承)

src/backend/tests/
├── test_od_downloader.py
├── test_od_parser.py
└── test_od_importer.py
```

**DoD**:
1. ZIP ファイルをダウンロードし、UTF-8 BOM CSV を抽出・パースできる
2. `base_bids` に UPSERT（`source_id` で重複排除）が機能する
3. 不正行（金額がマイナス、必須項目 NULL）はスキップしてログ出力する
4. raw CSV ファイルが `data/raw/od/YYYYMMDD_full.csv` に保存される
5. `@http_retry` が適用されている（3回リトライ）
6. `pytest tests/test_od_*.py` で正常・不正行スキップ・空ファイル・HTTP エラーが PASS（8テスト以上）

---

### TASK-17: F-005 Layer2 — 落札公告詳細スクレイピング

| 項目 | 内容 |
|------|------|
| **Effort** | M（1日） |
| **Dependencies** | TASK-16 |
| **SSOT参照** | F-005 §3-A〜D（Layer2 処理）, SSOT-4 §2-3（bid_details テーブル） |

**Input**: F-005 Layer2 仕様 + bid_details DDL

**Output**:
```
src/backend/app/services/
├── od_import/
│   └── detail_scraper.py  # HTML スクレイプ → bid_details 格納

src/backend/app/batch/
└── detail_scrape.py       # DetailScrapeBatch

src/backend/tests/
└── test_detail_scraper.py
```

**DoD**:
1. `base_bids` から対象レコードを抽出し、詳細ページ URL を生成できる
2. HTML から `num_participants`, `budget_amount`, `bidder_details` を抽出できる
3. `SCRAPE_RATE_LIMIT_SEC` (1 req/sec) のレートリミットが適用される
4. HTML 構造変更時にパースエラーをログ出力してスキップする
5. `pytest tests/test_detail_scraper.py` で正常・HTML変更・レートリミットが PASS（5テスト以上）

---

### TASK-18: F-001 Adapter 基盤 + ChotatkuPortalAdapter

| 項目 | 内容 |
|------|------|
| **Effort** | L（2日） |
| **Dependencies** | TASK-14 |
| **SSOT参照** | F-001 §3-A〜C（Adapter パターン 6ステージ）, SSOT-4 §2-4（cases テーブル） |

**Input**: F-001 仕様書 Adapter パターン + cases DDL

**Output**:
```
src/backend/app/services/
├── case_fetch/
│   ├── __init__.py
│   ├── base_adapter.py   # BaseAdapter ABC (fetch, normalize, store)
│   ├── chotaku_adapter.py # ChotatkuPortalAdapter (調達ポータル)
│   └── normalizer.py     # 統一スキーマ変換

src/backend/app/batch/
└── case_fetch.py          # CaseFetchBatch

src/backend/tests/
├── test_base_adapter.py
├── test_chotaku_adapter.py
└── test_normalizer.py
```

**DoD**:
1. `BaseAdapter` ABC に `fetch()`, `normalize()`, `store()` メソッドが定義されている
2. `ChotatkuPortalAdapter.fetch()` が HTML をダウンロードしてパースする
3. `store()` が `UPSERT ON (source, source_id)` で new/updated/unchanged を判別する
4. raw HTML が `data/raw/portal/YYYYMMDD/` に保存される
5. `@http_retry` + `SCRAPE_RATE_LIMIT_SEC` が適用される
6. `pytest tests/test_chotaku_adapter.py` で正常・HTMLエラー・重複排除が PASS（8テスト以上）

---

### TASK-19: F-001 フィルタリング + 4因子スコアリング

| 項目 | 内容 |
|------|------|
| **Effort** | M（1日） |
| **Dependencies** | TASK-16, TASK-17, TASK-18 |
| **SSOT参照** | F-001 §3-D（フィルタ条件 + スコア 4因子）, F-005（base_bids/bid_details 参照） |

**Input**: F-001 フィルタ + スコア仕様 + F-005 テーブル

**Output**:
```
src/backend/app/services/
├── case_fetch/
│   ├── filter.py         # キーワード/入札種別/地域/等級/締切フィルタ
│   └── scorer.py         # 4因子スコアリング (competition/scale/deadline/domain)

src/backend/tests/
├── test_filter.py
└── test_scorer.py
```

**DoD**:
1. キーワード OR マッチ、入札種別、地域、等級、締切の 5 フィルタが機能する
2. 4 因子（competition 30pt, scale 25pt, deadline 25pt, domain 20pt）の合計 100pt でスコア算出
3. F-005 データ未取得時にデフォルトスコア（competition=15, scale=15）が適用される
4. `score_detail` JSONB に各因子の内訳が記録される
5. `pytest tests/test_scorer.py` で全データあり・F-005データなし・高/低スコアが PASS（8テスト以上）

---

### TASK-20: F-001 case_fetch バッチ統合

| 項目 | 内容 |
|------|------|
| **Effort** | M（1日） |
| **Dependencies** | TASK-18, TASK-19 |
| **SSOT参照** | SSOT-5 §2-1（case_fetch バッチ）, F-001 §4（NFR） |

**Input**: Adapter + Filter + Scorer + BatchRunner

**Output**:
```
src/backend/app/batch/
└── case_fetch.py         # CaseFetchBatch (完全版)

src/backend/tests/
└── test_case_fetch_batch.py
```

**DoD**:
1. `CaseFetchBatch.run()` が fetch → normalize → store → filter → score の 5 ステージを順次実行する
2. 1 データソースの失敗が他のソースの処理を止めない（部分失敗許容）
3. batch_logs に success/partial/failed が正しく記録される
4. 新規高スコア案件のログ出力（INFO）が確認できる
5. `pytest tests/test_case_fetch_batch.py` で正常・部分失敗・全失敗が PASS

---

### TASK-21: 価格分析サービス

| 項目 | 内容 |
|------|------|
| **Effort** | M（1日） |
| **Dependencies** | TASK-16, TASK-17 |
| **SSOT参照** | F-005 §3-E〜F（集計ロジック）, SSOT-3 §4-8（GET /analytics/price-summary） |

**Input**: base_bids + bid_details テーブル + F-005 集計仕様

**Output**:
```
src/backend/app/services/
└── analytics/
    ├── __init__.py
    └── price_service.py   # PriceAnalyticsService

src/backend/tests/
└── test_price_service.py
```

**DoD**:
1. キーワード / 発注機関 / カテゴリ / 期間でフィルタした集計が返る
2. 集計項目: 件数、落札金額（中央値・平均・最小・最大）、参加者数（平均）、月別推移
3. 不正金額（0, マイナス）は集計から除外される
4. `pytest tests/test_price_service.py` で正常・フィルタ・空データが PASS（5テスト以上）

---

### TASK-22: 案件アクション API

| 項目 | 内容 |
|------|------|
| **Effort** | M（1日） |
| **Dependencies** | TASK-10 |
| **SSOT参照** | SSOT-3 §4-2（9 POST アクション）, SSOT-2 §3（遷移テーブル + ゲート G1〜G9） |

**Input**: 9 アクションエンドポイント仕様 + 遷移テーブル

**Output**:
```
src/backend/app/api/
└── actions.py           # 9 POST /cases/:id/actions/* エンドポイント

src/backend/tests/
└── test_actions_api.py
```

**DoD**:
1. 9 エンドポイント（mark-reviewed, mark-planned, mark-skipped, restore, archive, retry-reading, retry-judging, retry-checklist, override）が実装されている
2. 各アクションが `EventService.record_transition()` を呼び出す
3. `expected_lifecycle_stage` 不一致で 409 を返す
4. `PIPELINE_IN_PROGRESS` 時に 409 を返す（retry 系エンドポイント）
5. `mark-skipped` で reason 未指定時に 422 `SKIP_REASON_REQUIRED` を返す
6. `pytest tests/test_actions_api.py` で正常遷移・不正遷移・409・422 が PASS（15テスト以上）

---

## Phase 4: F-002, F-003, F-004 実装

> AI 読解 → 適格性判定 → チェックリスト生成のパイプライン実装。

### ⚡ Spike タスク（ブロッカー先行検証）

Phase 4〜6 で詰まりやすい 3 箇所を、本実装前に小規模検証する。
Spike は各 0.5 日（S）。成功基準を満たせば本タスクに着手。

| Spike | 対象 | 検証内容 | 成功基準 | 関連タスク |
|-------|------|---------|---------|----------|
| SPIKE-A | PDF 抽出揺れ | fixtures/specs/*.pdf 3 種を pdfplumber で抽出 → LLM に投げて根拠付与率を計測 | 根拠付与率 80%+ | TASK-23, 24, 25 |
| SPIKE-B | スキャンPDF 誤検知 | fixtures/specs/ の正常/スキャン各 5 ファイルで is_scanned 判定 | 誤検知率 10% 未満 | TASK-23 |
| SPIKE-C | 409 UI 制御 | React で expected_lifecycle_stage 不一致 → 自動再取得 → リトライのフロー | 5 秒以内にリカバリ表示 | TASK-41 |

> Spike が不合格の場合: 閾値調整（SPIKE-A/B）、UI フロー修正（SPIKE-C）を行い再検証。
> Spike の工数は Phase 4〜6 の Effort に含めない（追加 1.5 日）。

### TASK-23: F-002 Stage1 — HTML/PDF フェッチ + テキスト抽出

| 項目 | 内容 |
|------|------|
| **Effort** | L（2日） |
| **Dependencies** | TASK-11, TASK-12, TASK-13, TASK-14 |
| **SSOT参照** | F-002 §3-A〜B（Stage1）, SSOT-5 §10（原文保存ポリシー） |

**Input**: F-002 Stage1 仕様 + pdfplumber + beautifulsoup4

**Output**:
```
src/backend/app/services/
├── reading/
│   ├── __init__.py
│   ├── fetcher.py        # HTML/PDF ダウンロード + raw 保存
│   ├── text_extractor.py # HTML: bs4, PDF: pdfplumber
│   └── scan_detector.py  # スキャンPDF検出 (chars/page < 50)

src/backend/tests/
├── test_fetcher.py
├── test_text_extractor.py
└── test_scan_detector.py
```

**DoD**:
1. notice HTML を `data/raw/notices/{case_id}.html` に保存する
2. spec PDF を `data/raw/specs/{case_id}.pdf` に保存する
3. pdfplumber でテキスト抽出し、ページ番号を保持する
4. スキャンPDF検出: `chars/page < SCANNED_PDF_CHAR_THRESHOLD(50)` → `is_scanned=true`
5. SHA-256 キャッシュ: 同一ハッシュの PDF はスキップ（Stage2 も省略）
6. `pytest tests/test_*.py` で正常・PDFエラー・スキャンPDF・キャッシュヒットが PASS（10テスト以上）

---

### TASK-24: F-002 Stage2 — LLM 構造化抽出

| 項目 | 内容 |
|------|------|
| **Effort** | L（2日） |
| **Dependencies** | TASK-23 |
| **SSOT参照** | F-002 §3-C（5カテゴリ抽出）, §4（セクション分割）, SSOT-5 §12-2（CHUNK_SPLIT_TOKEN_THRESHOLD） |

**Input**: F-002 Stage2 仕様 + LLM 抽象化レイヤー + Pydantic バリデーション

**Output**:
```
src/backend/app/services/
├── reading/
│   ├── extractor.py      # LLM 呼び出し + 5カテゴリ抽出
│   ├── prompts.py        # プロンプトテンプレート
│   ├── schemas.py        # 抽出結果の Pydantic スキーマ
│   └── chunker.py        # 5000トークン超時のセクション分割

src/backend/tests/
├── test_extractor.py
└── test_chunker.py
```

**DoD**:
1. 5 カテゴリ（eligibility, schedule, business_content, submission_items, risk_factors）の構造化抽出ができる
2. 各項目に `assertion_type` (fact/inferred/caution) と `evidence` が付与される
3. `CHUNK_SPLIT_TOKEN_THRESHOLD` (5000) 超過時にセクション分割する
4. LLM レスポンスの Pydantic バリデーション失敗時に 1 回リトライ（`LLM_PARSE_RETRY_MAX`）
5. `token_usage` (input/output) が記録される
6. `pytest tests/test_extractor.py` で MockProvider を使った正常・分割・パースエラーが PASS（8テスト以上）

---

### TASK-25: F-002 Stage3 — エビデンスマッピング + 品質スコア

| 項目 | 内容 |
|------|------|
| **Effort** | M（1日） |
| **Dependencies** | TASK-24 |
| **SSOT参照** | F-002 §6（エビデンスマッピング）, §3-D（品質スコア計算）, SSOT-5 §12-2（EVIDENCE_MATCH_*） |

**Input**: F-002 Stage3 仕様 + Jaccard 類似度閾値

**Output**:
```
src/backend/app/services/
├── reading/
│   ├── evidence_mapper.py  # Jaccard + Levenshtein エビデンスマッチ
│   └── quality_scorer.py   # confidence_score + risk_level 算出

src/backend/tests/
├── test_evidence_mapper.py
└── test_quality_scorer.py
```

**DoD**:
1. Jaccard >= 0.8 → confidence="high", 0.65-0.8 → "medium", < 0.65 → "low"
2. Levenshtein 距離でフォールバック（medium→high 昇格）
3. `quality_score = (high_count + medium_count * 0.5) / total_items`
4. `risk_level`: any high-severity → "high", medium only → "medium", none → "low"
5. `confidence_score < CONFIDENCE_THRESHOLD(0.6)` → `status='needs_review'`
6. `VersionManager` 経由で `case_cards` を作成する
7. `pytest tests/test_evidence_mapper.py` と `test_quality_scorer.py` で全パターンが PASS（10テスト以上）

---

### TASK-26: F-003 Prerequisites + Hard 条件 5 件

| 項目 | 内容 |
|------|------|
| **Effort** | M（1日） |
| **Dependencies** | TASK-25 |
| **SSOT参照** | F-003 §3-A〜B（Prerequisites + Hard 条件） |

**Input**: F-003 Phase1-2 仕様 + company_profiles テーブル + case_cards テーブル

**Output**:
```
src/backend/app/services/
├── judgment/
│   ├── __init__.py
│   ├── prerequisites.py   # 3件のプリチェック
│   └── hard_conditions.py # 5件のHard条件チェック

src/backend/tests/
├── test_prerequisites.py
└── test_hard_conditions.py
```

**DoD**:
1. Prerequisites 3 件（company_profile 存在、confidence >= 0.6、eligibility != null）をチェック
2. Hard-1〜Hard-5 の各チェック（unified_qualification, grade, business_category, region, licenses）が実装されている
3. 等級比較が A > B > C > D の順序で正しく判定される
4. "その他" がワイルドカードとして機能する
5. `pytest tests/test_hard_conditions.py` で各 Hard 条件の pass/fail/uncertain が PASS（15テスト以上）

---

### TASK-27: F-003 Soft 条件 + 最終判定 + Override

| 項目 | 内容 |
|------|------|
| **Effort** | M（1日） |
| **Dependencies** | TASK-26 |
| **SSOT参照** | F-003 §3-C〜D（Soft条件 + 最終判定）, SSOT-3 §4-2（override エンドポイント） |

**Input**: F-003 Phase3-4 仕様 + Override 仕様

**Output**:
```
src/backend/app/services/
├── judgment/
│   ├── soft_conditions.py  # 4件のSoft条件チェック
│   ├── verdict_engine.py   # 最終判定 (eligible/ineligible/uncertain)
│   └── override.py         # 人間上書き (メタデータのみ、ステージ不変)

src/backend/tests/
├── test_soft_conditions.py
├── test_verdict_engine.py
└── test_override.py
```

**DoD**:
1. Soft-1〜Soft-4（experience, ISO/Pmark, location, staffing）が severity=high/medium/low で判定される
2. 最終判定: hard_fail → ineligible, uncertain → uncertain, soft_gap severity=high → uncertain, else → eligible
3. confidence 計算: `min(F-002 confidence, Hard evidence confidence, profile completeness)`
4. Override: verdict + reason を保持、ステージは変更しない。eligible 判定時に F-004 がトリガーされる
5. `VersionManager` 経由で `eligibility_results` を作成する
6. `pytest tests/test_verdict_engine.py` で eligible/ineligible/uncertain 全パターンが PASS（10テスト以上）

---

### TASK-28: F-004 提出物 → チェックリスト変換 + 固定項目

| 項目 | 内容 |
|------|------|
| **Effort** | M（1日） |
| **Dependencies** | TASK-27 |
| **SSOT参照** | F-004 §3-A〜B（Phase1-2: トリガーチェック + 提出物変換）, §3-D（uncertain 確認タスク） |

**Input**: F-004 Phase1-2 仕様 + submission_items from case_cards

**Output**:
```
src/backend/app/services/
├── checklist/
│   ├── __init__.py
│   ├── trigger.py         # 生成トリガーチェック (eligible or uncertain+override)
│   ├── item_converter.py  # submission_items → checklist items
│   └── fixed_items.py     # 固定項目 (封筒、提出方法、下見積もり書)

src/backend/tests/
├── test_trigger.py
├── test_item_converter.py
└── test_fixed_items.py
```

**DoD**:
1. `verdict="eligible"` or `uncertain+override=eligible` でのみ生成される
2. `bid_time_items` → `phase="bid_time"`, `performance_time_items` → `phase="performance_time"` に変換
3. `has_quote_requirement=true` の場合、下見積もり書がトップ優先度で追加される
4. `uncertain+override` 時に `auto_confirm` タスクが先頭に挿入される
5. `submission_items` が NULL の場合、スケジュールのみのスケルトンが生成される
6. `pytest tests/test_item_converter.py` で 2フェーズ・見積もり要件・NULL各パターンが PASS（8テスト以上）

---

### TASK-29: F-004 逆算スケジュール + 警告マッピング

| 項目 | 内容 |
|------|------|
| **Effort** | M（1日） |
| **Dependencies** | TASK-28 |
| **SSOT参照** | F-004 §3-B〜C（Phase3-4: スケジュール + 警告）, SSOT-5 §12-2（SCHEDULE_REVERSE_*_BD） |

**Input**: F-004 Phase3-4 仕様 + jpholiday + SCHEDULE_REVERSE 定数

**Output**:
```
src/backend/app/services/
├── checklist/
│   ├── schedule_calc.py   # 営業日逆算 (jpholiday)
│   └── warning_mapper.py  # risk_factors + soft_gaps → 警告マッピング

src/backend/tests/
├── test_schedule_calc.py
└── test_warning_mapper.py
```

**DoD**:
1. `deadline_at` から -5BD / -2BD / -1BD / 0BD の 4 ステップスケジュールが生成される
2. jpholiday で祝日をスキップした営業日計算が正しい
3. `has_quote_requirement=true` の場合、`quote_deadline` からも同様のスケジュールが生成される
4. `deadline_at` が過去の場合、⚠️ 警告 + `status='archived'`
5. risk_factors が対応するチェックリスト項目に warnings として付与される
6. `VersionManager` 経由で `checklists` を作成する
7. `pytest tests/test_schedule_calc.py` で標準・祝日跨ぎ・過去締切・見積もり各パターンが PASS（8テスト以上）

---

### TASK-30: cascade_pipeline オーケストレータ

| 項目 | 内容 |
|------|------|
| **Effort** | L（2日） |
| **Dependencies** | TASK-23, TASK-24, TASK-25, TASK-26, TASK-27, TASK-28, TASK-29 |
| **SSOT参照** | SSOT-5 §2-4（cascade 詳細）, §3-4a（サーキットブレーカ）, §2-5（部分失敗） |

**Input**: SSOT-5 §2-4 の cascade フロー + 全 F-002/F-003/F-004 サービス

**Output**:
```
src/backend/app/batch/
└── cascade_pipeline.py   # CascadePipelineBatch

src/backend/tests/
└── test_cascade_pipeline.py
```

**DoD**:
1. `planned` ステージの案件を対象に F-002 → F-003 → F-004 を順次実行する
2. F-002 失敗 → その案件の F-003/F-004 をスキップして次の案件へ
3. F-003 verdict=ineligible/uncertain → F-004 をスキップ
4. `scope=soft`: SHA-256 キャッシュ利用、`scope=force`: 全ステップ再実行
5. `LLMCircuitBreaker` が open 状態で残り案件を即 `reading_failed` (llm_circuit_open) にする
6. 部分失敗時に `batch_logs.status='partial'` + `error_details` に各案件の結果が記録される
7. `pytest tests/test_cascade_pipeline.py` で正常フロー・部分失敗・サーキットブレーカ・キャッシュが PASS（10テスト以上）

---

### TASK-31: スタック検出 + 自動タイムアウト処理

| 項目 | 内容 |
|------|------|
| **Effort** | M（1日） |
| **Dependencies** | TASK-10 |
| **SSOT参照** | SSOT-5 §3-5（スタック検出テーブル）, §12-2（TIMEOUT 定数 3 種） |

**Input**: SSOT-5 §3-5 のタイムアウト仕様

**Output**:
```
src/backend/app/services/
└── stuck_detector.py     # StuckDetector

src/backend/tests/
└── test_stuck_detector.py
```

**DoD**:
1. `reading_in_progress` が 5 分超（is_scanned=true は 10 分超）で `reading_failed` + タイムアウトイベント
2. `judging_in_progress` が 2 分超で `judging_failed` + タイムアウトイベント
3. `checklist_generating` が 1 分超で `checklist_generation_failed` + タイムアウトイベント
4. `EventService` 経由でイベントが記録される
5. `pytest tests/test_stuck_detector.py` で各タイムアウト・正常（時間内）・is_scanned 例外が PASS（8テスト以上）

---

### TASK-32: コスト制御

| 項目 | 内容 |
|------|------|
| **Effort** | S（0.5日） |
| **Dependencies** | TASK-13 |
| **SSOT参照** | SSOT-5 §8-3a（LLM コスト制御）, §12-2（LLM_DAILY_TOKEN_LIMIT） |

**Input**: SSOT-5 §8-3a のコスト制御仕様

**Output**:
```
src/backend/app/services/
└── cost_controller.py    # CostController

src/backend/tests/
└── test_cost_controller.py
```

**DoD**:
1. 当日の累計 token 使用量を `case_cards.token_usage` から集計できる
2. `LLM_DAILY_TOKEN_LIMIT > 0` かつ累計超過時に `cost_cap_exceeded` エラーを返す
3. `LLM_DAILY_TOKEN_LIMIT = 0` の場合は無制限（チェックスキップ）
4. `pytest tests/test_cost_controller.py` で無制限・超過・未超過が PASS（4テスト以上）

> **LLM_DAILY_TOKEN_LIMIT 暫定値の決定手順**（Phase0 計測後に実施）
> 1. 代表 5 案件を cascade_pipeline で処理
> 2. `case_cards.token_usage` から p95 を算出
> 3. `daily_limit = p95_tokens_per_case × daily_cases_target × 1.2`（20% バッファ）
> 4. 値を `.env` に設定、`constants.py` に反映

---

## Phase 5: API レイヤー

> SSOT-3 の 28 エンドポイントを FastAPI ルーターとして実装。

### TASK-33: Cases API

| 項目 | 内容 |
|------|------|
| **Effort** | M（1日） |
| **Dependencies** | TASK-08, TASK-09, TASK-10 |
| **SSOT参照** | SSOT-3 §4-1（GET /cases, GET /cases/:id） |

**Input**: SSOT-3 §4-1 のクエリパラメータ + include 仕様

**Output**:
```
src/backend/app/api/
└── cases.py             # GET /cases, GET /cases/:id

src/backend/tests/
└── test_cases_api.py
```

**DoD**:
1. `GET /cases` のフィルタ（lifecycle_stage, status, score_min/max, deadline_before/after, needs_review, has_failed, search, exclude_archived）が全て機能する
2. ソート（deadline_at:asc/desc, score:desc, created_at:desc）が機能する
3. ページネーション（page, limit, total, total_pages）が meta に含まれる
4. `GET /cases/:id` の `include` パラメータ（card_current, eligibility_current, checklist_current, latest_events）が機能する
5. `pytest tests/test_cases_api.py` でフィルタ・ソート・ページネーション・include が PASS（12テスト以上）

---

### TASK-34: Case Cards / Eligibility API

| 項目 | 内容 |
|------|------|
| **Effort** | M（1日） |
| **Dependencies** | TASK-08, TASK-09, TASK-11 |
| **SSOT参照** | SSOT-3 §4-3（Case Cards 3エンドポイント）, §4-4（Eligibility 2エンドポイント） |

**Input**: SSOT-3 §4-3, §4-4

**Output**:
```
src/backend/app/api/
├── case_cards.py        # GET card, GET cards, POST mark-reviewed
└── eligibility.py       # GET eligibility, GET eligibilities

src/backend/tests/
├── test_case_cards_api.py
└── test_eligibility_api.py
```

**DoD**:
1. `GET /cases/:id/card` が `is_current=true` のレコードを返す
2. `GET /cases/:id/cards` が全バージョンを version 降順で返す
3. `POST /case-cards/:id/actions/mark-reviewed` が `reviewed_at`, `reviewed_by` をセットする
4. `GET /cases/:id/eligibility` が current を返す
5. 存在しない場合に 404 `CASE_CARD_NOT_FOUND` / `ELIGIBILITY_NOT_FOUND` を返す
6. `pytest tests/test_case_cards_api.py` と `test_eligibility_api.py` で正常・404 が PASS（8テスト以上）

---

### TASK-35: Checklists API

| 項目 | 内容 |
|------|------|
| **Effort** | M（1日） |
| **Dependencies** | TASK-08, TASK-09, TASK-11 |
| **SSOT参照** | SSOT-3 §4-5（Checklists 4エンドポイント）, §6（楽観ロック） |

**Input**: SSOT-3 §4-5 + expected_checklist_version

**Output**:
```
src/backend/app/api/
└── checklists.py        # GET checklist, GET checklists, PATCH items/:item_id, POST items

src/backend/tests/
└── test_checklists_api.py
```

**DoD**:
1. `GET /cases/:id/checklist` が current を返す
2. `PATCH /checklists/:id/items/:item_id` が check/uncheck を冪等に実行する
3. `expected_checklist_version` 不一致で 409 `CHECKLIST_VERSION_MISMATCH` を返す
4. `POST /checklists/:id/items` で手動項目追加ができる
5. 全アイテム完了時に `checklist_completed` イベントが記録される
6. `pytest tests/test_checklists_api.py` で正常・409・手動追加・全完了が PASS（10テスト以上）

---

### TASK-36: Events / Batch / Company Profile API

| 項目 | 内容 |
|------|------|
| **Effort** | M（1日） |
| **Dependencies** | TASK-08, TASK-09, TASK-14 |
| **SSOT参照** | SSOT-3 §4-6〜§4-8（Events, Batch, Company Profile, Analytics） |

**Input**: SSOT-3 §4-6〜§4-8

**Output**:
```
src/backend/app/api/
├── events.py            # GET /cases/:id/events
├── batch.py             # GET latest, GET logs, GET logs/:id, POST trigger
└── company_profile.py   # GET, PATCH

src/backend/tests/
├── test_events_api.py
├── test_batch_api.py
└── test_company_profile_api.py
```

**DoD**:
1. `GET /cases/:id/events` の `since_event_id`, `since_ts`, `fold`, `feature_origin` フィルタが機能する
2. `POST /batch/trigger` が batch_type + source を受け取りバッチを起動する
3. `GET /company-profile` が Phase1 唯一のプロフィールを返す
4. `PATCH /company-profile` で部分更新ができる
5. `pytest tests/test_*.py` で各エンドポイントの正常・エラーが PASS（10テスト以上）

---

### TASK-37: Analytics API

| 項目 | 内容 |
|------|------|
| **Effort** | S（0.5日） |
| **Dependencies** | TASK-21 |
| **SSOT参照** | SSOT-3 §4-8（GET /analytics/price-summary） |

**Input**: PriceAnalyticsService + SSOT-3 §4-8

**Output**:
```
src/backend/app/api/
└── analytics.py         # GET /analytics/price-summary

src/backend/tests/
└── test_analytics_api.py
```

**DoD**:
1. `GET /analytics/price-summary` が keyword, issuing_org, category, period_months でフィルタした集計を返す
2. レスポンスが SuccessResponse エンベロープに包まれている
3. `pytest tests/test_analytics_api.py` で正常・空データが PASS

---

### TASK-38: Pydantic スキーマ全量定義 + OpenAPI 検証

| 項目 | 内容 |
|------|------|
| **Effort** | M（1日） |
| **Dependencies** | TASK-33, TASK-34, TASK-35, TASK-36, TASK-37 |
| **SSOT参照** | SSOT-3 §2（Enum 定義）, §3（レスポンス形式）, 全エンドポイント |

**Input**: 全 API エンドポイントのリクエスト/レスポンス型

**Output**:
```
src/backend/app/schemas/
├── __init__.py
├── case.py              # CaseResponse, CaseListResponse
├── case_card.py         # CaseCardResponse
├── eligibility.py       # EligibilityResponse
├── checklist.py         # ChecklistResponse, ChecklistItemUpdate
├── event.py             # EventResponse
├── batch.py             # BatchLogResponse, BatchTriggerRequest
├── company_profile.py   # CompanyProfileResponse, CompanyProfileUpdate
├── analytics.py         # PriceSummaryResponse
├── actions.py           # ActionRequest (各アクション用)
└── enums.py             # LifecycleStage, Verdict, CaseStatus, etc.

src/backend/tests/
└── test_schemas.py
```

**DoD**:
1. 全エンドポイントのリクエスト/レスポンスに Pydantic v2 スキーマが定義されている
2. 8 Enum（LifecycleStage, CaseStatus, Verdict, ChecklistItemStatus, TriggeredBy, IncludeParam, SortField, SortDirection）が定義されている
3. `GET /docs` で OpenAPI スキーマが表示される
4. `pytest tests/test_schemas.py` でスキーマのバリデーションが PASS
5. LifecycleStage enum が 17 値を持つことを検証するテストが PASS

---

## Phase 6: フロントエンド

> SSOT-2 の 4 画面を React コンポーネントとして実装。

### TASK-39: React アプリ scaffold + API クライアント + AppState

| 項目 | 内容 |
|------|------|
| **Effort** | M（1日） |
| **Dependencies** | TASK-02, Phase 5 完了 |
| **SSOT参照** | SSOT-2 §1（ページ一覧）, §6（ポーリング）, SSOT-3 §3（レスポンスエンベロープ） |

**Input**: SSOT-2 AppState 定義 + SSOT-3 エンベロープ

**Output**:
```
src/frontend/src/
├── services/
│   └── api-client.ts    # axios/fetch wrapper (エンベロープ自動アンラップ)
├── hooks/
│   ├── useApi.ts        # useQuery wrapper
│   └── usePolling.ts    # ポーリング制御 (5s/30s/60s)
├── contexts/
│   └── AppContext.tsx    # AppState (cases, activeCase, companyProfile, batchStatus)
└── types/
    ├── api.ts           # SuccessResponse, ErrorResponse, PaginatedResponse
    ├── case.ts          # Case, CaseCard, EligibilityResult, Checklist
    └── enums.ts         # LifecycleStage, Verdict, CaseStatus, etc.
```

**DoD**:
1. API クライアントがレスポンスエンベロープを自動アンラップする
2. エラーレスポンスを統一的にハンドリングする（409, 404, 422, 500）
3. `usePolling` が stage に応じて 5s / 30s / 60s を切り替える
4. TypeScript 型が SSOT-3 の全 Enum を反映している
5. `bun run test` で api-client のモックテストが PASS

---

### TASK-40: P1 ダッシュボード

| 項目 | 内容 |
|------|------|
| **Effort** | L（2日） |
| **Dependencies** | TASK-39 |
| **SSOT参照** | SSOT-2 §2-1（P1 ダッシュボード）, §5（アクションボタン制御） |

**Input**: SSOT-2 P1 仕様

**Output**:
```
src/frontend/src/
├── pages/
│   └── Dashboard.tsx     # 案件一覧 + フィルタ + バッチステータス
├── components/
│   ├── CaseList.tsx      # 案件テーブル
│   ├── CaseFilters.tsx   # フィルタパネル
│   ├── BatchStatusBar.tsx # バッチ実行状態
│   └── ScoreBadge.tsx    # スコアバッジ (色分け)
└── tests/
    └── Dashboard.test.tsx
```

**DoD**:
1. ライフサイクルステージフィルタ + スコア範囲 + 締切期間でフィルタできる
2. 締切日昇順 / スコア降順 / 作成日降順でソートできる
3. ページネーション（limit=20, 次/前ページ）が機能する
4. バッチステータスバーが最新のバッチ状態を表示する
5. 30 秒ポーリングで一覧が自動更新される
6. `bun run test` で Dashboard.test.tsx が PASS

---

### TASK-41: P2 案件詳細 — 概要タブ + アクションボタン

| 項目 | 内容 |
|------|------|
| **Effort** | M（1日） |
| **Dependencies** | TASK-39 |
| **SSOT参照** | SSOT-2 §2-2（P2 概要タブ）, §5-1〜§5-4（ボタン制御ルール） |

**Input**: SSOT-2 概要タブ仕様 + ゲート G1〜G9

**Output**:
```
src/frontend/src/
├── pages/
│   └── CaseDetail.tsx    # 5タブレイアウト
├── components/
│   ├── CaseOverview.tsx   # 概要タブ
│   └── ActionButtons.tsx  # G1〜G9 アクションボタン

src/frontend/tests/
└── CaseOverview.test.tsx
```

**DoD**:
1. case_name, issuing_org, bid_type, category, deadline, score が表示される
2. ゲート G1〜G9 のボタンがステージに応じて表示/非表示/無効化される
3. `*_queued`, `*_in_progress`, `*_generating` 時に全アクションボタンが無効化される（archive 除く）
4. 409 エラー時に自動再取得 + リトライ促進メッセージが表示される
5. `bun run test` で ActionButtons のステージ別表示テストが PASS

---

### TASK-42: P2 案件詳細 — AI 読解タブ

| 項目 | 内容 |
|------|------|
| **Effort** | M（1日） |
| **Dependencies** | TASK-39 |
| **SSOT参照** | SSOT-2 §2-2（AI読解タブ）, §5-5（品質警告バッジ） |

**Input**: SSOT-2 AI読解タブ仕様

**Output**:
```
src/frontend/src/
├── components/
│   ├── ReadingTab.tsx     # 5カテゴリ表示
│   ├── EvidencePanel.tsx  # 根拠パネル (原文引用 + confidence)
│   ├── ConfidenceBadge.tsx # 信頼度バッジ (赤/黄/緑)
│   └── AssertionLabel.tsx  # fact/inferred/caution ラベル

src/frontend/tests/
└── ReadingTab.test.tsx
```

**DoD**:
1. 5 カテゴリ（eligibility, schedule, business_content, submission_items, risk_factors）が表示される
2. confidence_score: red (<0.4), yellow (0.4-0.6), green (>0.6) のバッジが表示される
3. assertion_type が fact/inferred/caution で色分けされる
4. needs_review バッジ + mark-reviewed ボタンが機能する
5. `bun run test` で ReadingTab.test.tsx が PASS

---

### TASK-43: P2 案件詳細 — 適格性タブ + Override パネル

| 項目 | 内容 |
|------|------|
| **Effort** | M（1日） |
| **Dependencies** | TASK-39 |
| **SSOT参照** | SSOT-2 §2-2（適格性タブ）, SSOT-3 §4-2（override エンドポイント） |

**Input**: SSOT-2 適格性タブ仕様

**Output**:
```
src/frontend/src/
├── components/
│   ├── EligibilityTab.tsx  # verdict + check_details
│   ├── VerdictBadge.tsx    # eligible(緑)/ineligible(赤)/uncertain(橙)
│   └── OverridePanel.tsx   # G4: uncertain 時のみ表示

src/frontend/tests/
└── EligibilityTab.test.tsx
```

**DoD**:
1. verdict バッジが eligible/ineligible/uncertain で色分けされる
2. hard_fail_reasons, soft_gaps, check_details が一覧表示される
3. Override パネルが `judging_completed + verdict=uncertain` 時のみ表示される
4. Override 実行後に verdict が更新される
5. `bun run test` で EligibilityTab.test.tsx が PASS

---

### TASK-44: P2 案件詳細 — チェックリストタブ

| 項目 | 内容 |
|------|------|
| **Effort** | M（1日） |
| **Dependencies** | TASK-39 |
| **SSOT参照** | SSOT-2 §2-2（チェックリストタブ）, SSOT-3 §4-5（PATCH items） |

**Input**: SSOT-2 チェックリストタブ仕様

**Output**:
```
src/frontend/src/
├── components/
│   ├── ChecklistTab.tsx    # チェックリスト表示
│   ├── ChecklistItem.tsx   # 個別アイテム (check/uncheck)
│   ├── ProgressBar.tsx     # 進捗バー
│   └── ScheduleTimeline.tsx # 逆算スケジュール表示

src/frontend/tests/
└── ChecklistTab.test.tsx
```

**DoD**:
1. checklist_items が phase (bid_time/performance_time) で分類表示される
2. check/uncheck がクリックで即時反映される
3. プログレスバーが完了率を表示する
4. スケジュールタイムラインが表示される（is_critical アイテムをハイライト）
5. 手動項目追加ボタンが機能する
6. `bun run test` で ChecklistTab.test.tsx が PASS

---

### TASK-45: P2 案件詳細 — 履歴タブ + ポーリング制御

| 項目 | 内容 |
|------|------|
| **Effort** | M（1日） |
| **Dependencies** | TASK-39 |
| **SSOT参照** | SSOT-2 §2-2（履歴タブ）, §6-6（ポーリング制御） |

**Input**: SSOT-2 履歴タブ + ポーリング仕様

**Output**:
```
src/frontend/src/
├── components/
│   ├── HistoryTab.tsx     # イベントタイムライン
│   └── EventCard.tsx      # 個別イベント表示

src/frontend/tests/
└── HistoryTab.test.tsx
```

**DoD**:
1. case_events がタイムライン形式で表示される
2. `fold` オプションで check 操作が折りたたまれる
3. `feature_origin` フィルタで特定機能のイベントのみ表示できる
4. *_queued / *_in_progress ステージで 5 秒ポーリング、安定ステージでポーリング停止
5. `since_event_id` による差分取得で重複表示がない
6. `bun run test` で HistoryTab.test.tsx が PASS

---

### TASK-46: P3 価格分析 + P4 設定画面

| 項目 | 内容 |
|------|------|
| **Effort** | M（1日） |
| **Dependencies** | TASK-39 |
| **SSOT参照** | SSOT-2 §2-3（P3 価格分析）, §2-4（P4 設定） |

**Input**: SSOT-2 P3/P4 仕様

**Output**:
```
src/frontend/src/
├── pages/
│   ├── Analytics.tsx      # 価格分析画面
│   └── Settings.tsx       # 設定画面
├── components/
│   ├── PriceSummary.tsx   # 集計テーブル
│   └── CompanyProfileForm.tsx # 会社プロフィール編集

src/frontend/tests/
├── Analytics.test.tsx
└── Settings.test.tsx
```

**DoD**:
1. P3: キーワード / 発注機関 / カテゴリ / 期間でフィルタした集計が表示される
2. P4: company_profile の 4 必須フィールドが編集・保存できる
3. P4: 保存成功時にフィードバックメッセージが表示される
4. `bun run test` で Analytics.test.tsx と Settings.test.tsx が PASS

---

## Phase 7: 運用ツール

> Phase1 運用に必要な監視・リカバリツール。

### TASK-47: health_check スクリプト

| 項目 | 内容 |
|------|------|
| **Effort** | M（1日） |
| **Dependencies** | Phase 5 完了 |
| **SSOT参照** | SSOT-5 §4-4a（Phase1 致命アラート 5 条件） |

**Input**: SSOT-5 §4-4a の 5 致命条件

**Output**:
```
src/backend/app/scripts/
└── health_check.py      # python -m app.scripts.health_check

src/backend/tests/
└── test_health_check.py
```

**DoD**:
1. `python -m app.scripts.health_check` で 5 条件をチェックする:
   - HIGH: cascade_pipeline 全件失敗（batch_logs.status='failed'）
   - HIGH: raw ドキュメント保存失敗（ログ ERROR + ファイル存在チェック）
   - HIGH: LLM サーキットブレーカ発動（case_events に llm_circuit_open）
   - MEDIUM: 24h バッチ未実行（batch_logs.started_at が 24h 前）
   - MEDIUM: 3+ スタック案件（*_in_progress が同時 3 件以上）
2. 各条件の結果を構造化 JSON でログ出力する
3. HIGH 条件に該当する場合、exit code 1 で終了する
4. `pytest tests/test_health_check.py` で各条件の検出・非検出が PASS（5テスト以上）

---

### TASK-48: cron セットアップ

| 項目 | 内容 |
|------|------|
| **Effort** | S（0.5日） |
| **Dependencies** | TASK-20, TASK-16, TASK-17, TASK-30, TASK-31, TASK-47 |
| **SSOT参照** | SSOT-5 §2-3（実行順序）, §12-3（BATCH_SCHEDULE_*） |

**Input**: SSOT-5 §2-3 のバッチスケジュール

**Output**:
```
src/backend/
├── crontab.example      # cron 設定例
└── app/scripts/
    ├── run_od_import.py
    ├── run_case_fetch.py
    ├── run_detail_scrape.py
    ├── run_cascade.py
    └── run_stuck_detector.py
```

**DoD**:
1. `crontab.example` に 6 エントリ（od_import 06:00, case_fetch 06:30, detail_scrape 07:00, cascade 07:30, stuck_detector 毎5分, health_check 毎日）が記載されている
2. 各スクリプトが単独で実行可能（`python -m app.scripts.run_od_import`）
3. ログが `logs/` ディレクトリに出力される

---

### TASK-49: ログ設計

| 項目 | 内容 |
|------|------|
| **Effort** | S（0.5日） |
| **Dependencies** | TASK-01 |
| **SSOT参照** | SSOT-5 §11（ログ設計全セクション） |

**Input**: SSOT-5 §11-1〜§11-6

**Output**:
```
src/backend/app/core/
└── logging.py           # structlog 設定 (JSON + case_id + feature_origin)

src/backend/tests/
└── test_logging.py
```

**DoD**:
1. structlog で構造化 JSON ログが出力される
2. 全ログに `timestamp`, `level`, `logger`, `message` が含まれる
3. `case_id`, `feature_origin`, `batch_log_id` がコンテキストに応じて付与される
4. ログレベル（DEBUG/INFO/WARN/ERROR）が SSOT-5 §11-3 の基準に従う
5. `pytest tests/test_logging.py` でフォーマット検証が PASS

---

### TASK-50: 運用マニュアル

| 項目 | 内容 |
|------|------|
| **Effort** | S（0.5日） |
| **Dependencies** | Phase 7 の他タスク完了 |
| **SSOT参照** | SSOT-5 §7（復旧手順 Recovery Runbook） |

**Input**: SSOT-5 §7 全復旧手順

**Output**:
```
docs/operations/
├── RUNBOOK.md           # 運用マニュアル + 復旧手順
└── LAUNCH_CHECKLIST.md  # 運用開始チェックリスト（1ページ）
```

**DoD**:
1. 以下の手順が RUNBOOK.md に記載されている:
   - 日常確認（health_check 結果の読み方）
   - バッチ手動トリガー方法（POST /batch/trigger）
   - スタック案件の手動復旧（UPDATE + retry）
   - サーキットブレーカ発動時の対応
   - DB バックアップ/リストア手順
2. 各手順に具体的な SQL / curl コマンドが含まれる
3. LAUNCH_CHECKLIST.md に以下の項目が含まれる:
   - [ ] health_check が exit 0 で通過する
   - [ ] 過去 24h に全 4 バッチが 1 回以上成功している
   - [ ] スタック案件が 0 件
   - [ ] サーキットブレーカが closed 状態
   - [ ] LLM_DAILY_TOKEN_LIMIT が計測値に基づいて設定されている
   - [ ] company_profile の 4 必須フィールドが入力済み
   - [ ] RUNBOOK.md が最新の手順と一致している
   - 異常時の確認順序: health_check → batch_logs → case_events → logs/app.log
   - 復旧優先度: サーキットブレーカ > スタック > バッチ失敗 > 個別案件エラー

---

## 障害系シミュレーション

> 各障害パターンを人為的に再現し、検出・復旧が正しく機能することを検証。

### SIM-01: スタック検出 & 自動リカバリ

| 項目 | 内容 |
|------|------|
| **Effort** | S（0.5日） |
| **Dependencies** | TASK-31 |
| **SSOT参照** | SSOT-5 §3-5, §7-1 |

**手順**:
```bash
# 1. 案件をスタック状態にする
psql -d nyusatsu -c "
  UPDATE cases
  SET current_lifecycle_stage = 'reading_in_progress',
      updated_at = NOW() - INTERVAL '10 minutes'
  WHERE id = '<test_case_id>';
"

# 2. スタック検出を実行
python -m app.scripts.run_stuck_detector

# 3. 検証
psql -d nyusatsu -c "
  SELECT current_lifecycle_stage FROM cases WHERE id = '<test_case_id>';
  -- 期待: reading_failed
"

psql -d nyusatsu -c "
  SELECT event_type, payload FROM case_events
  WHERE case_id = '<test_case_id>'
  ORDER BY created_at DESC LIMIT 1;
  -- 期待: event_type = 'reading_failed', payload.error_type = 'stuck_timeout'
"

# 4. is_scanned=true の場合の検証 (10分タイムアウト)
psql -d nyusatsu -c "
  UPDATE cases
  SET current_lifecycle_stage = 'reading_in_progress',
      updated_at = NOW() - INTERVAL '7 minutes'
  WHERE id = '<test_case_id_scanned>';
"
# → スタック検出実行 → まだ reading_in_progress のまま（10分未満）
```

**期待結果**: 5分超のスタック案件が `reading_failed` に遷移し、イベントが記録される。is_scanned=true は 10 分閾値が適用される。

---

### SIM-02: LLM サーキットブレーカ発動 & リセット

| 項目 | 内容 |
|------|------|
| **Effort** | S（0.5日） |
| **Dependencies** | TASK-12, TASK-30 |
| **SSOT参照** | SSOT-5 §3-4a |

**手順**:
```bash
# 1. LLM API をモックで連続失敗させる（テスト用設定）
export LLM_MOCK_MODE=error  # MockProvider が常にエラーを返す

# 2. cascade_pipeline を3件以上の案件で実行
python -m app.scripts.run_cascade --source test

# 3. 検証: 最初の3件は llm_api_error、4件目以降は llm_circuit_open
psql -d nyusatsu -c "
  SELECT ce.event_type, ce.payload->>'error_type'
  FROM case_events ce
  JOIN cases c ON ce.case_id = c.id
  WHERE ce.event_type = 'reading_failed'
  ORDER BY ce.created_at;
  -- 期待: 1-3件目 = llm_api_error, 4件目以降 = llm_circuit_open
"

# 4. 手動リトライがサーキットブレーカをバイパスすることを検証
export LLM_MOCK_MODE=success
curl -X POST http://localhost:8000/api/v1/cases/<case_id>/actions/retry-reading
# 期待: 200 OK → reading_queued → reading_completed
```

**期待結果**: 3 連続失敗でサーキットブレーカ発動。残り案件は即失敗。手動リトライは常に成功。

---

### SIM-03: コストキャップ超過

| 項目 | 内容 |
|------|------|
| **Effort** | S（0.5日） |
| **Dependencies** | TASK-32 |
| **SSOT参照** | SSOT-5 §8-3a |

**手順**:
```bash
# 1. 日次トークン上限を低く設定
export LLM_DAILY_TOKEN_LIMIT=1000

# 2. 既に超過状態を作る
psql -d nyusatsu -c "
  UPDATE case_cards
  SET token_usage = '{\"input\": 800, \"output\": 300}'
  WHERE created_at::date = CURRENT_DATE AND is_current = true
  LIMIT 1;
"

# 3. cascade_pipeline を実行
python -m app.scripts.run_cascade --source test

# 4. 検証
psql -d nyusatsu -c "
  SELECT event_type, payload->>'error_type'
  FROM case_events
  WHERE event_type = 'reading_failed'
  ORDER BY created_at DESC LIMIT 1;
  -- 期待: error_type = 'cost_cap_exceeded'
"
```

**期待結果**: トークン上限超過で `reading_failed` (cost_cap_exceeded) が記録される。

---

### SIM-04: 楽観ロック競合（409）

| 項目 | 内容 |
|------|------|
| **Effort** | S（0.5日） |
| **Dependencies** | TASK-10, TASK-22 |
| **SSOT参照** | SSOT-3 §6, SSOT-5 §5 |

**手順**:
```bash
# 1. 案件のステージを確認
curl http://localhost:8000/api/v1/cases/<case_id> | jq '.data.current_lifecycle_stage'
# 例: "under_review"

# 2. 古いステージを指定してアクションを実行
curl -X POST http://localhost:8000/api/v1/cases/<case_id>/actions/mark-planned \
  -H "Content-Type: application/json" \
  -d '{"expected_lifecycle_stage": "discovered"}'
# 期待: 409 {"error": {"code": "STAGE_MISMATCH", ...}}

# 3. 正しいステージを指定して再実行
curl -X POST http://localhost:8000/api/v1/cases/<case_id>/actions/mark-planned \
  -H "Content-Type: application/json" \
  -d '{"expected_lifecycle_stage": "under_review"}'
# 期待: 200 OK

# 4. チェックリスト version 競合
curl -X PATCH http://localhost:8000/api/v1/checklists/<cl_id>/items/<item_id> \
  -H "Content-Type: application/json" \
  -d '{"is_checked": true, "expected_checklist_version": 0}'
# 期待: 409 {"error": {"code": "CHECKLIST_VERSION_MISMATCH", ...}}
```

**期待結果**: ステージ不一致で 409 STAGE_MISMATCH、バージョン不一致で 409 CHECKLIST_VERSION_MISMATCH が返る。

---

### SIM-05: 全 cascade E2E（正常 + 部分失敗）

| 項目 | 内容 |
|------|------|
| **Effort** | M（1日） |
| **Dependencies** | 全 Phase 完了 |
| **SSOT参照** | SSOT-5 §2-4, 全機能仕様 |

**手順**:
```bash
# === 正常フロー ===

# 1. OD import 実行
python -m app.scripts.run_od_import
# 検証: base_bids にレコードが追加される

# 2. Case fetch 実行
python -m app.scripts.run_case_fetch
# 検証: cases にレコードが追加され、スコアが付与される

# 3. 案件を planned にする
curl -X POST http://localhost:8000/api/v1/cases/<case_id>/actions/mark-reviewed
curl -X POST http://localhost:8000/api/v1/cases/<case_id>/actions/mark-planned

# 4. Cascade pipeline 実行
python -m app.scripts.run_cascade
# 検証:
psql -d nyusatsu -c "
  SELECT current_lifecycle_stage FROM cases WHERE id = '<case_id>';
  -- 期待: checklist_active (eligible の場合) or judging_completed (uncertain の場合)
"

psql -d nyusatsu -c "
  SELECT event_type FROM case_events WHERE case_id = '<case_id>' ORDER BY created_at;
  -- 期待: reading_queued → reading_started → reading_completed →
  --        judging_queued → judging_completed → checklist_generating → checklist_active
"

# 5. チェックリスト操作
curl -X PATCH http://localhost:8000/api/v1/checklists/<cl_id>/items/<item_id> \
  -H "Content-Type: application/json" \
  -d '{"is_checked": true}'

# 6. Health check
python -m app.scripts.health_check
# 期待: exit code 0 (全条件 OK)

# === 部分失敗フロー ===

# 7. 複数案件で一部だけ PDF がない状態を作る
# → 1件: reading_completed, 1件: reading_failed (PDF 404)
# 検証: batch_logs.status = 'partial', error_details に失敗案件が記録される
```

**期待結果**: 正常フローで全ステージを通過。部分失敗で partial が記録され、成功案件は正常に完了。

---

## SSOT 参照マップ

> 各 SSOT セクションがどの TASK から参照されるかの逆引き。

| SSOT | セクション | 参照タスク |
|------|-----------|----------|
| SSOT-2 | §1 ページ一覧 | TASK-02, 39 |
| SSOT-2 | §2-1 P1 ダッシュボード | TASK-40 |
| SSOT-2 | §2-2 P2 案件詳細 | TASK-41, 42, 43, 44, 45 |
| SSOT-2 | §2-3 P3 価格分析 | TASK-46 |
| SSOT-2 | §2-4 P4 設定 | TASK-46 |
| SSOT-2 | §3 状態遷移テーブル | TASK-10, 22 |
| SSOT-2 | §5 アクションボタン制御 | TASK-22, 41 |
| SSOT-2 | §6 ポーリング | TASK-39, 45 |
| SSOT-3 | §2 Enum 定義 | TASK-38 |
| SSOT-3 | §3 レスポンスエンベロープ | TASK-09, 39 |
| SSOT-3 | §4-1 Cases API | TASK-33 |
| SSOT-3 | §4-2 Case Actions | TASK-22 |
| SSOT-3 | §4-3 Case Cards | TASK-34 |
| SSOT-3 | §4-4 Eligibility | TASK-34 |
| SSOT-3 | §4-5 Checklists | TASK-35 |
| SSOT-3 | §4-6 Events | TASK-36 |
| SSOT-3 | §4-7 Batch | TASK-36 |
| SSOT-3 | §4-8 Company Profile / Analytics | TASK-36, 37 |
| SSOT-3 | §5 エラーコード | TASK-09 |
| SSOT-3 | §6 冪等性 | TASK-10, 35, SIM-04 |
| SSOT-3 | §7 バッチ排他 | TASK-14 |
| SSOT-4 | §2-1〜§2-5 基本テーブル | TASK-04 |
| SSOT-4 | §2-3 bid_details | TASK-05 |
| SSOT-4 | §2-6 case_cards | TASK-05 |
| SSOT-4 | §2-7 eligibility_results | TASK-05 |
| SSOT-4 | §2-8 checklists | TASK-06 |
| SSOT-4 | §2-9 case_events | TASK-06 |
| SSOT-4 | §5 インデックス | TASK-07 |
| SSOT-4 | §6 再実行モデル | TASK-08, 11 |
| SSOT-5 | §1 設計原則 | TASK-13 (原則11) |
| SSOT-5 | §2 バッチワークフロー | TASK-14, 20, 30 |
| SSOT-5 | §3-4 リトライ定義 | TASK-12 |
| SSOT-5 | §3-4a サーキットブレーカ | TASK-12, 30, SIM-02 |
| SSOT-5 | §3-5 スタック検出 | TASK-31, SIM-01 |
| SSOT-5 | §4-1 エラーハンドリング | TASK-09 |
| SSOT-5 | §4-4a 致命アラート | TASK-47 |
| SSOT-5 | §5 冪等性 | TASK-10, SIM-04 |
| SSOT-5 | §6-1 case_events payload | TASK-10 |
| SSOT-5 | §7 復旧手順 | TASK-50 |
| SSOT-5 | §8-3a コスト制御 | TASK-32, SIM-03 |
| SSOT-5 | §10 データ保持 | TASK-23 |
| SSOT-5 | §11 ログ設計 | TASK-49 |
| SSOT-5 | §12-1 技術スタック | TASK-01, 02 |
| SSOT-5 | §12-2 定数テーブル | TASK-15 |
| SSOT-5 | §12-3 環境変数 | TASK-03 |
| F-001 | §3-A〜D | TASK-18, 19, 20 |
| F-002 | §3-A〜B Stage1 | TASK-23 |
| F-002 | §3-C Stage2 | TASK-24 |
| F-002 | §6 エビデンス | TASK-25 |
| F-003 | §3-A〜B | TASK-26 |
| F-003 | §3-C〜D | TASK-27 |
| F-004 | §3-A〜B | TASK-28 |
| F-004 | §3-B〜C | TASK-29 |
| F-005 | §3-A〜D Layer1 | TASK-16 |
| F-005 | §3-A〜D Layer2 | TASK-17 |
| F-005 | §3-E〜F 集計 | TASK-21 |
