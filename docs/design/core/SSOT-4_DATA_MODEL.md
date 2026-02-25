# SSOT-4: データモデル — 入札ラクダAI

> P0 全5機能（F-001〜F-005）のデータ基盤を統合定義する。
> 各機能仕様書（§3-B, §3-C）で個別に定義されたテーブルを、
> ここで正式な DDL・JSONB スキーマ・インデックス戦略として一元管理する。

---

## 基本情報

| 項目 | 内容 |
|------|------|
| ドキュメントID | SSOT-4 |
| ドキュメント名 | データモデル |
| バージョン | v2.0 |
| 作成日 | 2026-02-17 |
| 最終更新日 | 2026-02-18 |
| 作成者 | Claude / 金子 裕司 |
| ステータス | Draft |
| DB | **PostgreSQL 16+** |

### 参照ドキュメント

| ドキュメント | パス |
|------------|------|
| F-001 案件自動収集 | docs/design/features/project/F-001_案件自動収集.md |
| F-002 AI読解 | docs/design/features/project/F-002_AI読解.md |
| F-003 参加可否判定 | docs/design/features/project/F-003_参加可否判定.md |
| F-004 チェックリスト生成 | docs/design/features/project/F-004_チェックリスト生成.md |
| F-005 価格分析 | docs/design/features/project/F-005_価格分析.md |
| SSOT-2 UI/状態遷移 | docs/design/core/SSOT-2_UI_STATE.md |
| SSOT-3 API規約 | docs/design/core/SSOT-3_API_CONTRACT.md |
| SSOT-5 横断的関心事 | docs/design/core/SSOT-5_CROSS_CUTTING.md |

---

## §1 設計原則

| # | 原則 | 詳細 |
|---|------|------|
| 1 | **3NF基本** | 正規化を基本とし、検索性能のために最小限の非正規化（キーカラム昇格）を許容 |
| 2 | **JSONB使用ポリシー** | 構造が可変・ネストが深い・スキーマが未確定のデータに JSONB を使用。検索頻度が高いフィールドは正規化カラムに昇格 |
| 3 | **UUID PK** | 全テーブルの主キーは UUID v4。`gen_random_uuid()` で自動採番 |
| 4 | **ソフトデリート** | 物理削除は禁止。`deleted_at TIMESTAMPTZ` で論理削除（Phase1 では削除自体を行わない設計だが、将来に備えてカラムは用意しない ← 不要になるまで追加しない YAGNI） |
| 5 | **TIMESTAMPTZ(UTC)** | 全日時カラムは `TIMESTAMPTZ` 型。アプリケーション層で UTC → JST 変換 |
| 6 | **監査スパイン** | `case_events` テーブルがイベントの正規化された真実（SSOT）。各テーブルの `status` カラムは非正規化キャッシュ |
| 7 | **再実行履歴** | `version` + `is_current` フラグ方式で再読解・再判定の履歴を保持 |
| 8 | **NOT NULL 優先** | 原則 NOT NULL。NULL を許容するカラムは明示的に理由をコメント |

---

## §2 ER概要図

```
┌─────────────────────────────────────────────────────────────────────┐
│                        テーブル関連図                                │
│                                                                     │
│  ┌──────────────┐                                                   │
│  │ base_bids    │──┐  F-005: 落札実績データ                         │
│  │ (Layer 1 OD) │  │                                               │
│  └──────────────┘  │  1:1                                          │
│                    ▼                                               │
│  ┌──────────────┐                                                   │
│  │ bid_details  │     F-005: 公告詳細補完データ                     │
│  │ (Layer 2)    │                                                   │
│  └──────────────┘                                                   │
│                                                                     │
│  ┌──────────────┐     F-001: 案件自動収集                           │
│  │ cases        │────────────────────────────────────┐              │
│  │ (案件マスタ) │──┐                                 │              │
│  └──────┬───────┘  │                                 │              │
│         │          │                                 │              │
│         │ 1:N      │ 1:N                             │ 1:N          │
│         ▼          ▼                                 ▼              │
│  ┌──────────────┐  ┌──────────────────┐  ┌────────────────────┐    │
│  │ case_cards   │  │ eligibility_     │  │ checklists         │    │
│  │ (AI読解結果) │  │ results          │  │ (チェックリスト)   │    │
│  │ F-002        │  │ (参加可否判定)   │  │ F-004              │    │
│  └──────────────┘  │ F-003            │  └────────────────────┘    │
│                    └──────────────────┘                             │
│                                                                     │
│  ┌──────────────┐     独立テーブル                                  │
│  │ company_     │     F-003: 会社プロフィール                       │
│  │ profiles     │     （Phase1: 1レコード固定）                     │
│  └──────────────┘                                                   │
│                                                                     │
│  ┌──────────────┐     横断テーブル                                  │
│  │ batch_logs   │     F-001/F-005: バッチ実行ログ                   │
│  └──────────────┘                                                   │
│                                                                     │
│  ┌──────────────┐     イベントスパイン（新設）                      │
│  │ case_events  │     全機能: 案件ライフサイクルの監査ログ           │
│  │ (監査ログ)   │     cases.id への FK                              │
│  └──────────────┘                                                   │
└─────────────────────────────────────────────────────────────────────┘
```

### FK 連鎖

```
cases ─────┬──→ case_cards         (case_id FK, 1:N — version管理)
           ├──→ eligibility_results (case_id FK, 1:N — version管理)
           ├──→ checklists          (case_id FK, 1:N — version管理)
           └──→ case_events         (case_id FK, 1:N — イベントログ)

case_cards ──→ eligibility_results  (case_card_id FK)
case_cards ──→ checklists           (case_card_id FK)
eligibility_results ──→ checklists  (eligibility_result_id FK)

base_bids ──→ bid_details           (base_bid_id FK, 1:1)

batch_logs: 独立（FK なし）
company_profiles: 独立（FK なし。Phase1は1レコード）
```

---

## §3 テーブル DDL

### §3-1. cases（案件マスタ）— F-001

> ソース: F-001 §3-B-2

```sql
CREATE TABLE cases (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- データソース識別
    source                  VARCHAR(50)   NOT NULL,       -- 'chotatku_portal', 'gov_xxx' 等
    source_id               VARCHAR(200)  NOT NULL,       -- データソースでの案件識別子
    -- 案件基本情報
    case_name               TEXT          NOT NULL,
    issuing_org             VARCHAR(200)  NOT NULL,
    issuing_org_code        VARCHAR(50),                  -- NULL許容: ODに含まれない場合
    bid_type                VARCHAR(50),                  -- '一般競争入札' 等
    category                VARCHAR(100),                 -- '物品の販売', '役務の提供' 等
    region                  VARCHAR(100),                 -- '関東・甲信越' 等
    grade                   VARCHAR(10),                  -- 'A','B','C','D'
    -- 日程
    submission_deadline     TIMESTAMPTZ,                  -- 入札書提出期限
    opening_date            TIMESTAMPTZ,                  -- 開札日時
    -- URL
    spec_url                TEXT,                         -- 仕様書URL
    notice_url              TEXT,                         -- 公告URL
    detail_url              TEXT,                         -- 公告詳細ページURL
    -- ステータス・スコア
    status                  VARCHAR(30)   NOT NULL DEFAULT 'new',
        -- new / reviewed / planned / skipped / archived
    skip_reason             TEXT,                         -- NULL許容: status=skipped の場合のみ
    score                   INTEGER,                      -- 0-100, NULL=未スコアリング
    score_detail            JSONB,                        -- §4-1 参照
    -- 統一ライフサイクル（SSOT-2 で定義する状態遷移の非正規化キャッシュ）
    current_lifecycle_stage VARCHAR(50)   NOT NULL DEFAULT 'discovered',
        -- SSOT-2 で定義。case_events の最新行が真実
    -- 原本・メタ
    raw_data                JSONB,                        -- 取得した元データ全体
    first_seen_at           TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    last_updated_at         TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    archived_at             TIMESTAMPTZ,                  -- NULL許容: 受付終了時にセット
    -- 制約
    CONSTRAINT uq_cases_source UNIQUE (source, source_id)
);

COMMENT ON TABLE  cases IS 'F-001: 案件マスタ。全データソースから収集した案件の統一スキーマ';
COMMENT ON COLUMN cases.current_lifecycle_stage IS '非正規化キャッシュ。真実は case_events の最新行';
COMMENT ON COLUMN cases.raw_data IS 'スキーマ変更への備え。取得した元データを丸ごと保存';
```

### §3-1a. current_lifecycle_stage 許容値一覧

> SSOT-2 で状態遷移テーブル（全有効遷移）を正式定義する。
> ここでは **値の一覧** と **差し戻し挙動** のみを固定する。

#### 許容値（enum 相当 — 17 ステージ）

| # | ステージ | グループ | 説明 |
|---|---------|---------|------|
| 1 | `discovered` | Discovery | 新規案件として検出済み |
| 2 | `scored` | Discovery | スコアリング完了 |
| 3 | `under_review` | Discovery | ユーザーが確認中 |
| 4 | `planned` | Discovery | 応札予定 |
| 5 | `skipped` | Discovery | 見送り |
| 6 | `reading_queued` | Reading | AI読解キューに追加 |
| 7 | `reading_in_progress` | Reading | AI読解実行中 |
| 8 | `reading_completed` | Reading | AI読解完了 |
| 9 | `reading_failed` | Reading | AI読解失敗 |
| 10 | `judging_queued` | Judging | 参加可否判定キューに追加 |
| 11 | `judging_in_progress` | Judging | 判定実行中 |
| 12 | `judging_completed` | Judging | 判定完了 |
| 13 | `judging_failed` | Judging | 判定失敗 |
| 14 | `checklist_generating` | Preparation | チェックリスト生成中 |
| 15 | `checklist_active` | Preparation | チェックリスト運用中 |
| 16 | `checklist_completed` | Preparation | 全チェック項目完了 |
| 17 | `archived` | Archive | アーカイブ（受付終了 or 手動） |

> **注**: cases.status（new/reviewed/planned/skipped/archived）は F-001 レベルの粗いステータス。
> current_lifecycle_stage は全機能を横断する細粒度ステージ。両者の対応表は SSOT-2 §4 で定義。

#### 差し戻し（re-run）時の遷移

| 操作 | from | to | 新 version 作成先 |
|------|------|----|-----------------|
| 再読解 | `reading_completed` | `reading_queued` | case_cards |
| 再判定 | `judging_completed` | `judging_queued` | eligibility_results |
| チェックリスト再生成 | `checklist_active` | `checklist_generating` | checklists |
| skipped 復帰 | `skipped` | `under_review` | — |

---

### §3-2. batch_logs（バッチ実行ログ）— F-001 / F-005

> ソース: F-001 §3-B-2

```sql
CREATE TABLE batch_logs (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source            VARCHAR(50)   NOT NULL,       -- 'chotatku_portal', 'od_csv' 等
    feature_origin    VARCHAR(10)   NOT NULL,       -- 'F-001', 'F-005'
    batch_type        VARCHAR(30)   NOT NULL,       -- 'case_fetch', 'od_import', 'detail_scrape'
    started_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    finished_at       TIMESTAMPTZ,                  -- NULL許容: 実行中
    status            VARCHAR(20)   NOT NULL DEFAULT 'running',
        -- running / success / failed / partial
    total_fetched     INTEGER       NOT NULL DEFAULT 0,
    new_count         INTEGER       NOT NULL DEFAULT 0,
    updated_count     INTEGER       NOT NULL DEFAULT 0,
    unchanged_count   INTEGER       NOT NULL DEFAULT 0,
    error_count       INTEGER       NOT NULL DEFAULT 0,
    error_details     JSONB,                        -- §4-2 参照
    metadata          JSONB                         -- 追加メタ情報（ファイルハッシュ等）
);

COMMENT ON TABLE batch_logs IS 'F-001/F-005: バッチ実行ログ。データ取得パイプラインの実行記録';
```

### §3-3. case_cards（AI読解結果）— F-002

> ソース: F-002 §3-C-1

```sql
CREATE TABLE case_cards (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id             UUID          NOT NULL REFERENCES cases(id),
    -- バージョン管理（再読解対応）
    version             INTEGER       NOT NULL DEFAULT 1,
    is_current          BOOLEAN       NOT NULL DEFAULT true,
    -- JSONB（5カテゴリ詳細）
    eligibility         JSONB,                        -- §4-3 参照
    schedule            JSONB,                        -- §4-4 参照
    business_content    JSONB,                        -- §4-5 参照
    submission_items    JSONB,                        -- §4-6 参照
    risk_factors        JSONB,                        -- §4-7 参照
    -- 正規化キーカラム（JSONB から昇格）
    deadline_at         TIMESTAMPTZ,                  -- = schedule.submission_deadline
    business_type       VARCHAR(50),                  -- '物品の販売' / '役務の提供'
    risk_level          VARCHAR(10),                  -- 'low' / 'medium' / 'high'
    extraction_method   VARCHAR(20)   NOT NULL DEFAULT 'text',
        -- 'text' / 'ocr' / 'text_failed'
    is_scanned          BOOLEAN       NOT NULL DEFAULT false,
    assertion_counts    JSONB,                        -- §4-8 参照
    -- 根拠・品質
    evidence            JSONB,                        -- §4-9 参照
    confidence_score    DECIMAL(3,2),                 -- 0.00〜1.00
    file_hash           VARCHAR(64),                  -- PDFのSHA-256ハッシュ（キャッシュ判定用）
    -- ステータス・メタデータ
    status              VARCHAR(20)   NOT NULL DEFAULT 'pending',
        -- pending / processing / completed / failed / needs_review
    raw_notice_text     TEXT,                         -- 公告の抽出テキスト
    raw_spec_text       TEXT,                         -- 仕様書の抽出テキスト
    llm_model           VARCHAR(100),                 -- 使用LLMモデル名・バージョン
    llm_request_id      VARCHAR(200),                 -- LLM APIリクエストID
    token_usage         JSONB,                        -- {"input": N, "output": N}
    extracted_at        TIMESTAMPTZ,                  -- 読解実行日時
    reviewed_at         TIMESTAMPTZ,                  -- NULL許容: 人間確認日時
    reviewed_by         VARCHAR(100),                 -- NULL許容: Phase1は 'kaneko'
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    -- 制約
    CONSTRAINT uq_case_cards_version UNIQUE (case_id, version)
);

COMMENT ON TABLE  case_cards IS 'F-002: AI読解結果（案件カード）。version + is_current で再読解履歴を管理';
COMMENT ON COLUMN case_cards.is_current IS 'true = 最新版。再読解時に旧版を false にし、新版を true + version+1 で INSERT';
COMMENT ON COLUMN case_cards.deadline_at IS 'schedule.submission_deadline から昇格。INDEX対象';
COMMENT ON COLUMN case_cards.risk_level IS 'risk_factors から自動算出。高リスク1件以上→high、中リスクのみ→medium、なし→low';
```

### §3-4. eligibility_results（参加可否判定）— F-003

> ソース: F-003 §3-C-1

```sql
CREATE TABLE eligibility_results (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id                     UUID          NOT NULL REFERENCES cases(id),
    case_card_id                UUID          NOT NULL REFERENCES case_cards(id),
    -- バージョン管理（再判定対応）
    version                     INTEGER       NOT NULL DEFAULT 1,
    is_current                  BOOLEAN       NOT NULL DEFAULT true,
    -- 判定結果
    verdict                     VARCHAR(20)   NOT NULL,
        -- 'eligible' / 'ineligible' / 'uncertain'
    confidence                  DECIMAL(3,2)  NOT NULL,  -- 0.00〜1.00
    hard_fail_reasons           JSONB         NOT NULL DEFAULT '[]'::JSONB,  -- §4-10 参照
    soft_gaps                   JSONB         NOT NULL DEFAULT '[]'::JSONB,  -- §4-11 参照
    evidence_refs               JSONB,                        -- F-002 evidence へのポインタ
    check_details               JSONB         NOT NULL,       -- §4-12 参照
    company_profile_snapshot    JSONB         NOT NULL,       -- 判定時のプロフィールスナップショット
    -- 人間オーバーライド
    human_override              VARCHAR(20),                  -- NULL=未上書き, 'eligible'/'ineligible'/'uncertain'
    override_reason             TEXT,                         -- NULL許容
    overridden_at               TIMESTAMPTZ,                  -- NULL許容
    overridden_by               VARCHAR(100),                 -- Phase1: 'kaneko'
    -- タイムスタンプ
    judged_at                   TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    created_at                  TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    -- 制約
    CONSTRAINT uq_eligibility_version UNIQUE (case_id, version)
);

COMMENT ON TABLE  eligibility_results IS 'F-003: 参加可否判定結果。version + is_current で再判定履歴を管理';
COMMENT ON COLUMN eligibility_results.verdict IS 'eligible=参加可, ineligible=参加不可, uncertain=確認必要';
COMMENT ON COLUMN eligibility_results.company_profile_snapshot IS '判定の再現性のため、判定時点のプロフィールを保存';
```

### §3-5. company_profiles（会社プロフィール）— F-003

> ソース: F-003 §3-A-2

```sql
CREATE TABLE company_profiles (
    id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- 必須4項目
    unified_qualification     BOOLEAN       NOT NULL,       -- 全省庁統一資格の保有
    grade                     VARCHAR(10)   NOT NULL,       -- 'A','B','C','D'
    business_categories       JSONB         NOT NULL,       -- ["物品の販売", "役務の提供その他"]
    regions                   JSONB         NOT NULL,       -- ["関東・甲信越"]
    -- 任意項目
    licenses                  JSONB         NOT NULL DEFAULT '[]'::JSONB,  -- 保有許認可
    certifications            JSONB         NOT NULL DEFAULT '[]'::JSONB,  -- ISO/Pマーク等
    experience                JSONB         NOT NULL DEFAULT '[]'::JSONB,  -- 過去の官公庁実績
    subcontractors            JSONB         NOT NULL DEFAULT '[]'::JSONB,  -- §4-13 参照
    -- メタ
    updated_at                TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    created_at                TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE company_profiles IS 'F-003: 会社プロフィール。Phase1は1レコード固定（金子の会社情報）';
```

### §3-6. checklists（チェックリスト）— F-004

> ソース: F-004 §3-C-1

```sql
CREATE TABLE checklists (
    id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id                   UUID          NOT NULL REFERENCES cases(id),
    case_card_id              UUID          NOT NULL REFERENCES case_cards(id),
    eligibility_result_id     UUID          NOT NULL REFERENCES eligibility_results(id),
    -- バージョン管理（再生成対応）
    version                   INTEGER       NOT NULL DEFAULT 1,
    is_current                BOOLEAN       NOT NULL DEFAULT true,
    -- チェックリスト内容
    checklist_items           JSONB         NOT NULL,       -- §4-14 参照
    schedule_items            JSONB         NOT NULL,       -- §4-15 参照
    warnings                  JSONB         NOT NULL DEFAULT '[]'::JSONB,
    progress                  JSONB         NOT NULL DEFAULT '{"total": 0, "done": 0, "rate": 0.0}'::JSONB,
    -- ステータス
    status                    VARCHAR(20)   NOT NULL DEFAULT 'draft',
        -- draft / active / completed / archived
    generated_at              TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    completed_at              TIMESTAMPTZ,                  -- NULL許容: 全項目完了時にセット
    created_at                TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    -- 制約
    CONSTRAINT uq_checklists_version UNIQUE (case_id, version)
);

COMMENT ON TABLE checklists IS 'F-004: チェックリスト。version + is_current で再生成履歴を管理';
```

### §3-7. base_bids（落札実績ベースデータ）— F-005

> ソース: F-005 §3-B-2

```sql
CREATE TABLE base_bids (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id           VARCHAR(200)  NOT NULL UNIQUE,    -- ODでの案件識別子
    case_name           TEXT          NOT NULL,
    issuing_org         VARCHAR(200)  NOT NULL,
    issuing_org_code    VARCHAR(50),                      -- NULL許容: ODに含まれない場合
    bid_type            VARCHAR(50),
    category            VARCHAR(100),
    winning_amount      BIGINT,                           -- 落札金額（円）。NULL許容: データ欠損
    winning_bidder      VARCHAR(200),
    opening_date        DATE,
    contract_date       DATE,
    detail_url          TEXT,                             -- 落札公告詳細ページURL（Layer 2スクレイピング対象）
    raw_data            JSONB,                            -- OD元データ全体（スキーマ変更への備え）
    imported_at         TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  base_bids IS 'F-005 Layer 1: 調達ポータル落札実績OD由来のベースデータ。スキーマ変化耐性は §7-4 参照';
COMMENT ON COLUMN base_bids.source_id IS '重複排除のキー。同一source_idが存在する場合はUPSERT';
COMMENT ON COLUMN base_bids.winning_amount IS '[要確認] 税抜 or 税込は ODの仕様に準拠。Phase0で確定';
COMMENT ON COLUMN base_bids.raw_data IS 'ODの元CSVを丸ごと保存。CSVスキーマ変更時はraw_dataから段階的にカラム昇格。§7-4 参照';
```

### §3-8. bid_details（公告詳細補完データ）— F-005

> ソース: F-005 §3-B-2

```sql
CREATE TABLE bid_details (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    base_bid_id         UUID          NOT NULL UNIQUE REFERENCES base_bids(id),
        -- 1:1 関係（base_bids ごとに1レコード）
    num_participants    INTEGER,                          -- 参加社数（応札者数）
    budget_amount       BIGINT,                           -- 予定価格。NULL許容: 非公表
    winning_rate        DECIMAL(5,4),                     -- 落札率 = winning_amount / budget_amount
    bidder_details      JSONB,                            -- §4-16 参照
    raw_html            TEXT,                             -- 取得したHTMLの原本（再パース用）
    scraped_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  bid_details IS 'F-005 Layer 2: 落札公告詳細ページ由来の補完データ（参加社数・予定価格等）';
COMMENT ON COLUMN bid_details.budget_amount IS '事後公表の場合のみ。非公表案件はNULL';
COMMENT ON COLUMN bid_details.winning_rate IS 'budget_amountがある場合に自動計算。INSERT/UPDATEトリガーで算出';
```

### §3-9. case_events（イベントスパイン / 監査ログ）— 新設

> 全機能の案件ライフサイクルイベントを一元記録する。
> 各テーブルの status カラムは非正規化キャッシュ。case_events の最新行が真実。

```sql
CREATE TABLE case_events (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id             UUID          NOT NULL REFERENCES cases(id),
    -- イベント情報
    event_type          VARCHAR(80)   NOT NULL,
        -- 下記 §3-9a のイベントタイプ一覧を参照
    from_status         VARCHAR(50),                      -- NULL許容: 初回イベント時
    to_status           VARCHAR(50)   NOT NULL,           -- 遷移後のステータス
    -- 発火元
    triggered_by        VARCHAR(20)   NOT NULL,
        -- 'system' / 'user' / 'batch' / 'cascade'
    actor_id            VARCHAR(100)  NOT NULL DEFAULT 'system',
        -- Phase1: 'kaneko' or 'system'
    feature_origin      VARCHAR(10)   NOT NULL,
        -- 'F-001' / 'F-002' / 'F-003' / 'F-004' / 'F-005'
    -- ペイロード
    payload             JSONB,                            -- §4-17 参照（イベント種別ごとに構造が異なる）
    -- タイムスタンプ
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  case_events IS '全機能: 案件ライフサイクルのイベントスパイン兼監査ログ。SSOT-2で定義する状態遷移の正規化された真実';
COMMENT ON COLUMN case_events.triggered_by IS 'system=自動処理, user=人間操作, batch=バッチ処理, cascade=他機能からの連鎖';
COMMENT ON COLUMN case_events.payload IS 'イベント種別ごとに構造が異なる。§4-17 JSOBスキーマ定義を参照';
```

#### §3-9a. イベントタイプ一覧

| event_type | feature | 説明 | triggered_by |
|-----------|---------|------|-------------|
| `case_discovered` | F-001 | 新規案件を検出 | batch |
| `case_updated` | F-001 | 案件情報が更新された | batch |
| `case_scored` | F-001 | スコアリング完了 | batch |
| `case_marked_planned` | F-001 | ユーザーが「応札予定」に変更 | user |
| `case_marked_skipped` | F-001 | ユーザーが「見送り」に変更 | user |
| `case_marked_reviewed` | F-001 | ユーザーが「確認済み」に変更 | user |
| `case_archived` | F-001 | 受付終了で自動アーカイブ | system |
| `reading_queued` | F-002 | AI読解キューに追加 | cascade |
| `reading_started` | F-002 | AI読解開始 | system |
| `reading_completed` | F-002 | AI読解完了 | system |
| `reading_failed` | F-002 | AI読解失敗 | system |
| `reading_reviewed` | F-002 | 人間が読解結果を確認 | user |
| `reading_requeued` | F-002 | 再読解をリクエスト | user |
| `judging_queued` | F-003 | 参加可否判定キューに追加 | cascade |
| `judging_completed` | F-003 | 判定完了 | system |
| `judging_failed` | F-003 | 判定失敗 | system |
| `eligibility_overridden` | F-003 | 人間が判定を上書き | user |
| `judging_requeued` | F-003 | 再判定をリクエスト | user |
| `checklist_generating` | F-004 | チェックリスト生成開始 | cascade |
| `checklist_generated` | F-004 | チェックリスト生成完了 | system |
| `checklist_generation_failed` | F-004 | チェックリスト生成失敗 | system |
| `checklist_item_checked` | F-004 | チェック項目を完了 | user |
| `checklist_item_unchecked` | F-004 | チェック項目を未完了に戻す | user |
| `checklist_completed` | F-004 | 全チェック項目完了 | system |
| `checklist_requeued` | F-004 | チェックリスト再生成をリクエスト | user |
| `bid_data_imported` | F-005 | 落札実績データ取り込み | batch |
| `bid_detail_scraped` | F-005 | 公告詳細ページスクレイピング | batch |

#### §3-9b. case_events 整合性ガード

> DDL 変更なし。payload の **運用ルール** として明文化する。

##### payload 必須キー一覧（event_type カテゴリ別）

| カテゴリ | 対象 event_type | 必須キー | 備考 |
|---------|----------------|---------|------|
| batch 系 | `case_discovered`, `case_updated`, `bid_data_imported`, `bid_detail_scraped` | `batch_log_id` | バッチ実行との紐付け |
| completed 系 | `reading_completed`, `judging_completed`, `checklist_generated` | 対象エンティティの `id` + `version` | どの version が生成されたかを記録 |
| failed 系 | `reading_failed`, `judging_failed`, `checklist_generation_failed` | `error_type`, `error_message` | 障害対応時に即座に原因を特定するため |
| override 系 | `eligibility_overridden` | `previous_verdict`, `new_verdict`, `override_reason` | 監査証跡として必須 |
| requeued 系 | `reading_requeued`, `judging_requeued`, `checklist_requeued` | `previous_version` | どの version からの差し戻しかを記録 |
| user 操作系 | `case_marked_planned`, `case_marked_skipped` | `reason`（空文字可） | ユーザー意図の記録 |
| チェック操作系 | `checklist_item_checked`, `checklist_item_unchecked` | `checklist_id`, `item_id`, `progress` | 進捗追跡 |

> 上記以外のキーは任意。バリデーションはアプリケーション層（Pydantic モデル）で実施。

##### actor_id の運用方針

| Phase | 値 | 説明 |
|-------|-----|------|
| Phase1 | `"kaneko"` | ユーザー操作（UI 経由） |
| Phase1 | `"system"` | 自動処理（パイプライン内の自律判断） |
| Phase1 | `"batch:{batch_log_id}"` | バッチ処理（batch_logs と紐付け可能） |
| Phase2 | `user_id` に移行 | マルチテナント化時。actor_id はそのまま VARCHAR(100) で十分 |

##### correlation_id の方針

- **Phase1: 導入しない**。カスケード（reading → judging → checklist）の追跡は `case_id + created_at の近傍` で十分。
- **Phase2 検討**: 高トラフィック時にカスケード追跡が困難になったら `correlation_id UUID` カラムを case_events に追加する。マイグレーションは `ALTER TABLE case_events ADD COLUMN correlation_id UUID;` のみ（NOT NULL ではない）。

---

## §4 JSONB スキーマ定義

### §4-1. cases.score_detail

```json
{
  "competition": 25,      // 競争度（30点満点）
  "scale": 20,            // 案件規模（25点満点）
  "deadline_margin": 22,  // 期限余裕（25点満点）
  "relevance": 18,        // 領域適合度（20点満点）
  "total": 85             // 合計（0-100）
}
```

### §4-2. batch_logs.error_details

```json
[
  {
    "url": "https://...",
    "error_type": "http_timeout",
    "message": "Connection timed out after 30s",
    "retry_count": 3,
    "timestamp": "2026-03-01T04:15:30Z"
  }
]
```

### §4-3. case_cards.eligibility

```json
{
  "unified_qualification": true,
  "grade": "D",
  "business_category": "物品の販売",
  "region": "関東・甲信越",
  "additional_requirements": [
    {
      "type": "license",
      "name": "一般貨物自動車運送事業許可",
      "assertion_type": "fact"
    }
  ]
}
```

### §4-4. case_cards.schedule

```json
{
  "spec_meeting_date": "2026-03-05T10:00:00Z",
  "submission_deadline": "2026-03-15T17:00:00Z",
  "opening_date": "2026-03-20T10:00:00Z",
  "equivalent_deadline": null,
  "quote_deadline": "2026-03-05T17:00:00Z",
  "performance_deadline": "2026-04-30T00:00:00Z"
}
```

### §4-5. case_cards.business_content

```json
{
  "business_type": "物品の販売",
  "summary": "○○省本省に対する事務用品の納入業務",
  "items": [
    {"name": "コピー用紙 A4", "quantity": 500, "unit": "箱"}
  ],
  "delivery_locations": [
    {"name": "○○省本省 1階受付", "address": "千代田区..."}
  ],
  "contract_type": "スポット",
  "has_quote_requirement": true,
  "has_spec_meeting": false
}
```

### §4-6. case_cards.submission_items

```json
{
  "bid_time_items": [
    {
      "name": "入札書",
      "template_source": "発注機関指定書式",
      "deadline": "2026-03-15",
      "notes": "機関の書式以外は無効",
      "assertion_type": "fact"
    }
  ],
  "performance_time_items": [
    {
      "name": "作業者名簿",
      "template_source": null,
      "deadline": null,
      "notes": "落札後、作業開始前に提出",
      "assertion_type": "fact"
    }
  ]
}
```

### §4-7. case_cards.risk_factors

```json
[
  {
    "risk_type": "special_license",
    "label": "特殊許認可要件",
    "severity": "high",
    "description": "一般貨物自動車運送事業許可が必要",
    "assertion_type": "fact",
    "evidence_ref": {
      "source_type": "html",
      "selector": "#section-eligibility",
      "heading_path": "入札公告 > 参加資格",
      "quote": "一般貨物自動車運送事業の許可を受けている者",
      "assertion_type": "fact"
    }
  }
]
```

### §4-8. case_cards.assertion_counts

```json
{
  "fact": 12,
  "inferred": 3,
  "caution": 1
}
```

### §4-9. case_cards.evidence

> 全抽出カテゴリの根拠情報を格納する。構造は F-002 §3-B-1 Stage 3 で固定。

```json
{
  "eligibility": {
    "unified_qualification": {
      "source_type": "html",
      "selector": "#section-eligibility",
      "heading_path": "入札公告 > 参加資格",
      "quote": "全省庁統一資格を有する者であること",
      "quote_max_chars": 100,
      "assertion_type": "fact",
      "confidence": "high"
    }
  },
  "schedule": { ... },
  "business_content": { ... },
  "submission_items": { ... },
  "risk_factors": { ... }
}
```

### §4-10. eligibility_results.hard_fail_reasons

```json
[
  {
    "rule_id": "hard_2_grade",
    "label": "等級不適合",
    "description": "A等級が必要ですが、自社はD等級です",
    "required": "A",
    "actual": "D",
    "evidence_ref": {
      "source_type": "pdf",
      "page": 1,
      "section": "参加資格",
      "quote": "A等級に格付けされている者"
    }
  }
]
```

### §4-11. eligibility_results.soft_gaps

```json
[
  {
    "rule_id": "soft_1_experience",
    "label": "実績要件",
    "description": "同種業務の履行実績が求められています",
    "severity": "high",
    "required": "同種業務の履行実績",
    "actual": null,
    "source": "company_profile.experience が空",
    "evidence_ref": {
      "source_type": "html",
      "heading_path": "入札公告 > 参加資格 > その他",
      "quote": "同種の業務について履行実績を有する者"
    }
  }
]
```

### §4-12. eligibility_results.check_details

```json
{
  "hard_checks": [
    {
      "rule_id": "hard_1_qualification",
      "label": "全省庁統一資格",
      "result": "pass",
      "required": true,
      "actual": true,
      "evidence_confidence": "high"
    },
    {
      "rule_id": "hard_2_grade",
      "label": "等級",
      "result": "pass",
      "required": "D",
      "actual": "D",
      "evidence_confidence": "high"
    }
  ],
  "soft_checks": [
    {
      "rule_id": "soft_1_experience",
      "label": "実績要件",
      "result": "gap",
      "severity": "high",
      "required": "同種業務の履行実績",
      "actual": null
    }
  ]
}
```

### §4-13. company_profiles.subcontractors

```json
[
  {
    "name": "クローバー運輸",
    "license": "運送業",
    "capabilities": ["軽運送", "配送"]
  },
  {
    "name": "電気工事会社",
    "license": "電気工事業",
    "capabilities": ["電気工事"]
  },
  {
    "name": "内装関係",
    "license": "内装業",
    "capabilities": ["内装工事"]
  }
]
```

### §4-14. checklists.checklist_items

> ソース: F-004 §3-C-2

```json
[
  {
    "item_id": "bid_001",
    "name": "入札書の記入",
    "phase": "bid_time",
    "deadline": "2026-03-15",
    "recommended_start": "2026-03-10",
    "template_type": "agency_form",
    "template_url": "https://...",
    "template_guide": "発注機関のひな形を使用",
    "status": "pending",
    "checked_at": null,
    "notes": null,
    "source": "extraction",
    "warnings": [],
    "evidence_ref": {
      "source_type": "html",
      "selector": "#section-submission",
      "heading_path": "入札公告 > 提出書類",
      "quote": "入札書1通",
      "assertion_type": "fact"
    }
  }
]
```

> `source` フィールドの値:
> - `"extraction"` — F-002 の submission_items から自動生成
> - `"knowledge_base"` — ナレッジベース（封筒・提出方法等）から固定追加
> - `"auto_confirm"` — uncertain 案件の確認タスク（F-004 §3-B-1 ④-b）

### §4-15. checklists.schedule_items

> ソース: F-004 §3-C-3

```json
[
  {
    "label": "提出物 作成開始",
    "date": "2026-03-10",
    "type": "recommended_start",
    "related_item_id": "bid_001",
    "is_critical": false
  },
  {
    "label": "社内レビュー",
    "date": "2026-03-13",
    "type": "deadline",
    "related_item_id": "bid_001",
    "is_critical": true
  },
  {
    "label": "入札書提出期限",
    "date": "2026-03-15",
    "type": "deadline",
    "related_item_id": null,
    "is_critical": true
  }
]
```

### §4-16. bid_details.bidder_details

```json
[
  {"name": "A社", "amount": 1000000},
  {"name": "B社", "amount": 1200000},
  {"name": "C社", "amount": 950000}
]
```

### §4-17. case_events.payload（イベント種別ごと）

**case_discovered / case_updated:**
```json
{
  "source": "chotatku_portal",
  "source_id": "2026-0001234",
  "batch_log_id": "uuid-of-batch-log",
  "changes": ["case_name", "submission_deadline"]  // updated時のみ
}
```

**case_scored:**
```json
{
  "score": 85,
  "score_detail": {"competition": 25, "scale": 20, "deadline_margin": 22, "relevance": 18}
}
```

**case_marked_planned / case_marked_skipped:**
```json
{
  "reason": "相場が合いそう",   // planned
  "reason": "等級が合わない"     // skipped
}
```

**reading_completed:**
```json
{
  "case_card_id": "uuid",
  "case_card_version": 1,
  "confidence_score": 0.85,
  "extraction_method": "text",
  "token_usage": {"input": 5000, "output": 2000}
}
```

**reading_failed:**
```json
{
  "case_card_id": "uuid",
  "error_type": "llm_api_error",
  "error_message": "Rate limit exceeded",
  "retry_count": 2
}
```

**judging_completed:**
```json
{
  "eligibility_result_id": "uuid",
  "eligibility_result_version": 1,
  "verdict": "eligible",
  "confidence": 0.92,
  "hard_fail_count": 0,
  "soft_gap_count": 1
}
```

**eligibility_overridden:**
```json
{
  "eligibility_result_id": "uuid",
  "previous_verdict": "uncertain",
  "new_verdict": "eligible",
  "override_reason": "仕様書を確認し、等級Dで問題ないことを確認"
}
```

**checklist_generated:**
```json
{
  "checklist_id": "uuid",
  "checklist_version": 1,
  "total_items": 8,
  "has_confirm_tasks": false,
  "trigger_verdict": "eligible"
}
```

**checklist_item_checked / checklist_item_unchecked:**
```json
{
  "checklist_id": "uuid",
  "item_id": "bid_001",
  "item_name": "入札書の記入",
  "progress": {"total": 8, "done": 4, "rate": 0.5}
}
```

---

## §5 インデックス戦略

### §5-1. cases

```sql
-- 主要な検索パターン: ステータス別一覧、期限順ソート、データソース別
CREATE INDEX idx_cases_status ON cases(status) WHERE status != 'archived';
CREATE INDEX idx_cases_lifecycle ON cases(current_lifecycle_stage);
CREATE INDEX idx_cases_deadline ON cases(submission_deadline) WHERE submission_deadline IS NOT NULL;
CREATE INDEX idx_cases_score ON cases(score DESC NULLS LAST) WHERE status != 'archived';
CREATE INDEX idx_cases_source ON cases(source, source_id);
CREATE INDEX idx_cases_first_seen ON cases(first_seen_at DESC);
```

### §5-2. case_cards

```sql
-- 最新版の検索が圧倒的に多い
CREATE INDEX idx_case_cards_current ON case_cards(case_id) WHERE is_current = true;
CREATE INDEX idx_case_cards_status ON case_cards(status) WHERE is_current = true;
CREATE INDEX idx_case_cards_deadline ON case_cards(deadline_at) WHERE is_current = true;
CREATE INDEX idx_case_cards_file_hash ON case_cards(file_hash) WHERE file_hash IS NOT NULL;
```

### §5-3. eligibility_results

```sql
CREATE INDEX idx_eligibility_current ON eligibility_results(case_id) WHERE is_current = true;
CREATE INDEX idx_eligibility_verdict ON eligibility_results(verdict) WHERE is_current = true;
```

### §5-4. checklists

```sql
CREATE INDEX idx_checklists_current ON checklists(case_id) WHERE is_current = true;
CREATE INDEX idx_checklists_status ON checklists(status) WHERE is_current = true;
```

### §5-5. case_events

```sql
-- 案件ごとのイベント時系列が最頻クエリ
CREATE INDEX idx_case_events_case_time ON case_events(case_id, created_at DESC);
CREATE INDEX idx_case_events_type ON case_events(event_type, created_at DESC);
CREATE INDEX idx_case_events_feature ON case_events(feature_origin, created_at DESC);
```

### §5-6. base_bids

```sql
-- 案件名キーワード検索（フルテキストは Phase2 で tsvector 導入検討）
CREATE INDEX idx_base_bids_opening ON base_bids(opening_date DESC);
CREATE INDEX idx_base_bids_org ON base_bids(issuing_org);
CREATE INDEX idx_base_bids_source_id ON base_bids(source_id);
```

### §5-7. bid_details

```sql
CREATE INDEX idx_bid_details_base ON bid_details(base_bid_id);
```

### §5-8. batch_logs

```sql
CREATE INDEX idx_batch_logs_source ON batch_logs(source, started_at DESC);
CREATE INDEX idx_batch_logs_status ON batch_logs(status) WHERE status != 'success';
```

---

## §6 再実行データモデル

### §6-1. 方式: version + is_current

再読解（F-002）、再判定（F-003）、チェックリスト再生成（F-004）で、
旧版を保持しつつ最新版を示すための方式。

```
再読解の例:
  1. case_cards (case_id=X, version=1, is_current=true)   ← 初回読解
  2. ユーザーが「再読解」をリクエスト
  3. UPDATE case_cards SET is_current=false WHERE case_id=X AND version=1
  4. INSERT case_cards (case_id=X, version=2, is_current=true)  ← 再読解結果
  5. case_events に reading_requeued + reading_completed を記録
```

### §6-2. 対象テーブル

| テーブル | version カラム | is_current カラム | 再実行イベント |
|---------|---------------|------------------|-------------|
| case_cards | ○ | ○ | reading_requeued → reading_completed |
| eligibility_results | ○ | ○ | judging_requeued → judging_completed |
| checklists | ○ | ○ | checklist_requeued → checklist_generated |

### §6-3. クエリパターン

```sql
-- 最新版の取得（最も頻繁）
SELECT * FROM case_cards WHERE case_id = :id AND is_current = true;

-- 全バージョン履歴（比較・監査用）
SELECT * FROM case_cards WHERE case_id = :id ORDER BY version DESC;

-- 特定バージョンの取得
SELECT * FROM case_cards WHERE case_id = :id AND version = :version;
```

### §6-4. 整合性ルール

| # | ルール | 実装方法 |
|---|-------|---------|
| 1 | 1つの case_id に is_current=true は最大1つ | アプリケーション層で保証。DB制約は部分ユニーク（PostgreSQL 15+ NULLS NOT DISTINCT） |
| 2 | version は case_id 内で単調増加 | `MAX(version) + 1` で採番 |
| 3 | 再実行時は旧版を false にしてから新版を INSERT | 同一トランザクション内で実行 |
| 4 | case_events に再実行の前後を記録 | requeued → started → completed/failed |
| 5 | eligibility_results は case_card_id で紐付け | 再読解後の再判定では新しい case_card_id を参照 |

#### §6-4a. テーブルごとの version/is_current 詳細

**case_cards（F-002）:**
- UNIQUE (case_id) WHERE is_current=true（§6-5 で制約定義）
- version は単調増加（欠番 OK — 手動削除等による）
- 生成元: F-002 の AI 読解パイプライン（`reading_completed` イベント発火時に INSERT）
- 旧版 → false にするタイミング: 新版 INSERT の直前（**同一トランザクション内**で UPDATE → INSERT）
- 再読解トリガー: ユーザー操作 (`reading_requeued`) or 公告/仕様書の更新検知

**eligibility_results（F-003）:**
- UNIQUE (case_id) WHERE is_current=true
- version は単調増加（欠番 OK）
- 生成元: F-003 の判定パイプライン（`judging_completed` イベント発火時に INSERT）
- **依存**: 常に is_current=true の case_cards を参照（`case_card_id` FK）。再読解後の再判定では、新しい case_card_id を使う
- 再判定トリガー: 再読解完了 (cascade) or ユーザー操作 (`judging_requeued`) or company_profile 更新

**checklists（F-004）:**
- UNIQUE (case_id) WHERE is_current=true
- version は単調増加（欠番 OK）
- 生成元: F-004 のチェックリスト生成パイプライン（`checklist_generated` イベント発火時に INSERT）
- **依存**: is_current=true の case_cards + eligibility_results を参照。再判定後の再生成では新しい eligibility_result_id を使う
- 再生成トリガー: 再判定完了 (cascade) or ユーザー操作 (`checklist_requeued`)

### §6-5. 部分ユニーク制約（is_current = true の一意性）

```sql
-- PostgreSQL 15+
CREATE UNIQUE INDEX uq_case_cards_current
    ON case_cards(case_id) WHERE is_current = true;

CREATE UNIQUE INDEX uq_eligibility_current
    ON eligibility_results(case_id) WHERE is_current = true;

CREATE UNIQUE INDEX uq_checklists_current
    ON checklists(case_id) WHERE is_current = true;
```

---

## §7 マイグレーション戦略

### §7-1. ツール

| 項目 | 選定 |
|------|------|
| マイグレーションツール | **Alembic**（SQLAlchemy連携） |
| 命名規約 | `YYYYMMDD_HHMMSS_description.py` |
| 実行環境 | ローカル開発は手動。Phase2以降でCI/CD連携 |

### §7-2. 初期マイグレーション順序

```
001_create_company_profiles.py    ← FK依存なし。シードデータ含む
002_create_base_bids.py           ← FK依存なし
003_create_bid_details.py         ← base_bids に依存
004_create_cases.py               ← FK依存なし
005_create_batch_logs.py          ← FK依存なし
006_create_case_cards.py          ← cases に依存
007_create_eligibility_results.py ← cases, case_cards に依存
008_create_checklists.py          ← cases, case_cards, eligibility_results に依存
009_create_case_events.py         ← cases に依存
010_create_indexes.py             ← 全テーブル作成後
011_seed_company_profile.py       ← Phase1 初期データ
```

### §7-3. Phase1 シードデータ: company_profiles

```sql
INSERT INTO company_profiles (
    unified_qualification, grade, business_categories, regions,
    licenses, certifications, experience, subcontractors
) VALUES (
    true,
    'D',
    '["物品の販売", "役務の提供その他"]'::JSONB,
    '["関東・甲信越"]'::JSONB,
    '[]'::JSONB,
    '[]'::JSONB,
    '[]'::JSONB,
    '[
        {"name": "クローバー運輸", "license": "運送業", "capabilities": ["軽運送", "配送"]},
        {"name": "電気工事会社", "license": "電気工事業", "capabilities": ["電気工事"]},
        {"name": "内装関係", "license": "内装業", "capabilities": ["内装工事"]}
    ]'::JSONB
);
```

### §7-4. base_bids の変化耐性方針

> 調達ポータル OD の CSV スキーマは予告なく変わり得る。
> 以下のルールで base_bids のテーブルスキーマを安定させる。

| # | ルール | 詳細 |
|---|-------|------|
| 1 | **原本保存** | 取得した CSV の全カラムを `raw_data` (JSONB) に丸ごと保存。ハッシュ付き |
| 2 | **マッピングレイヤで吸収** | Python の取り込みスクリプト内に「CSV カラム名 → base_bids カラム」のマッピング dict を持つ。CSV スキーマ変更時はこの dict のみ修正 |
| 3 | **base_bids スキーマは原則不変** | 新カラムが必要な場合は、まず `raw_data` から段階的に昇格する（ALTER TABLE ADD COLUMN）。既存カラムの変更・削除は行わない |
| 4 | **バッチ実行時にスキーマバージョンを記録** | `batch_logs.metadata` に `{"csv_schema_version": "2026-01", "csv_hash": "sha256:..."}` を格納。変更検知に使用 |
| 5 | **スキーマ変更検知** | 取り込み時に CSV のヘッダ行を前回と比較。差異がある場合は batch_logs.status = 'partial' + 警告ログ出力。処理は続行（マッピング dict に存在するカラムのみ取り込み） |

---

## [要確認] 一覧

| # | 項目 | 影響範囲 | 解消予定 |
|---|------|---------|---------|
| 1 | base_bids.winning_amount の税抜/税込 | base_bids, 集計クエリ | Phase0（ODファイルDLで確定） |
| 2 | 調達ポータルODの実際のCSVスキーマ | base_bids のカラム構成 | Phase0（M6検証タスク） |
| 3 | base_bids の年間レコード数（パーティショニング要否） | base_bids のテーブル設計 | Phase0（データ量確認後） |

---

## 変更履歴

| 日付 | 変更内容 | 変更者 |
|------|---------|-------|
| 2026-02-17 | 初版作成（P0全5機能の仕様書に基づく。9テーブル + case_events 新設） | Claude / 金子 |
| 2026-02-18 | v2: §3-1a lifecycle_stage許容値一覧、§3-9b case_events整合性ガード、§6-4a version/is_current詳細、§7-4 base_bids変化耐性方針を追加（DDL変更なし） | Claude / 金子 |
