# SSOT-3: API規約 — 入札ラクダAI

> P0 全5機能（F-001〜F-005）の REST API を統合定義する。
> SSOT-2（状態遷移）の全ゲートポイント・遷移を API エンドポイントとして実装する。
> SSOT-4（データモデル）のテーブル構造と JSONB スキーマに基づくレスポンス型を定義する。

---

## 基本情報

| 項目 | 内容 |
|------|------|
| ドキュメントID | SSOT-3 |
| ドキュメント名 | API規約 |
| バージョン | v1.1 |
| 作成日 | 2026-02-18 |
| 最終更新日 | 2026-02-18 |
| 作成者 | Claude / 金子 裕司 |
| ステータス | Draft |
| フレームワーク | **FastAPI** (Python) |

### 参照ドキュメント

| ドキュメント | パス |
|------------|------|
| SSOT-2 UI/状態遷移 | docs/design/core/SSOT-2_UI_STATE.md |
| SSOT-4 データモデル | docs/design/core/SSOT-4_DATA_MODEL.md |
| F-001 案件自動収集 | docs/design/features/project/F-001_案件自動収集.md |
| F-002 AI読解 | docs/design/features/project/F-002_AI読解.md |
| F-003 参加可否判定 | docs/design/features/project/F-003_参加可否判定.md |
| F-004 チェックリスト生成 | docs/design/features/project/F-004_チェックリスト生成.md |
| F-005 価格分析 | docs/design/features/project/F-005_価格分析.md |

---

## §1 設計原則

| # | 原則 | 詳細 |
|---|------|------|
| 1 | **RESTful + Command パターン** | CRUD はリソースエンドポイント（`GET /cases`）、状態遷移は Command エンドポイント（`POST /cases/:id/actions/mark-planned`）で分離 |
| 2 | **FastAPI + Pydantic** | リクエスト/レスポンスは全て Pydantic モデルで型定義。OpenAPI スキーマを自動生成 |
| 3 | **Phase1 は認証なし** | シングルユーザー（金子）。CORS は `localhost` のみ。Phase2 で Bearer Token (JWT) 導入 |
| 4 | **レスポンス包括構造** | 全エンドポイントが `{ data, meta, error }` の統一構造を返す（§2-3 参照） |
| 5 | **楽観ロック** | Command エンドポイントに `expected_lifecycle_stage` パラメータ。不一致で 409 Conflict（SSOT-2 §2-4 参照） |
| 6 | **case_events 自動記録** | 全 Command エンドポイントは case_events に自動でイベントを INSERT。レスポンスに発火したイベントを含める |
| 7 | **冪等性** | チェック操作（PATCH）は冪等。POST 系は `Idempotency-Key` ヘッダーを推奨（Phase1 は必須にしない） |
| 8 | **URL パスバージョニング** | `/api/v1/` プレフィックス。Phase2 で `/api/v2/` を並行稼働 |

---

## §2 共通仕様

### §2-1. URL プレフィックス

```
/api/v1/
```

### §2-2. 共通リクエストヘッダー

| ヘッダー | 必須 | 説明 |
|---------|------|------|
| `Content-Type` | ○（POST/PATCH） | `application/json` |
| `Accept` | — | `application/json`（省略時もJSON） |
| `Idempotency-Key` | —（推奨） | POST 系リクエストの冪等性キー。UUID v4。Phase1 は非必須 |

### §2-3. レスポンス包括構造

**正常系:**

```json
{
  "data": { ... },
  "meta": {
    "timestamp": "2026-03-01T06:00:00Z",
    "request_id": "uuid-v4"
  }
}
```

**一覧系（ページネーション付き）:**

```json
{
  "data": [ ... ],
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 142,
    "total_pages": 8,
    "timestamp": "2026-03-01T06:00:00Z",
    "request_id": "uuid-v4"
  }
}
```

**エラー系:**

```json
{
  "data": null,
  "error": {
    "code": "INVALID_TRANSITION",
    "message": "Cannot transition from archived to under_review",
    "details": {
      "current_lifecycle_stage": "archived",
      "requested_action": "restore"
    }
  },
  "meta": {
    "timestamp": "2026-03-01T06:00:00Z",
    "request_id": "uuid-v4"
  }
}
```

### §2-4. ページネーション

| パラメータ | デフォルト | 最大 | 説明 |
|-----------|-----------|------|------|
| `page` | 1 | — | ページ番号（1-indexed） |
| `limit` | 20 | 100 | 1ページあたりの件数 |

### §2-5. HTTPステータスコード

| コード | 用途 |
|-------|------|
| `200 OK` | 正常完了（GET / PATCH / 冪等な POST の再送） |
| `201 Created` | リソース新規作成（POST で新規作成された場合） |
| `400 Bad Request` | リクエスト構文エラー |
| `404 Not Found` | リソース不在 |
| `409 Conflict` | 不正な状態遷移 / 楽観ロック不一致 / パイプライン実行中 |
| `422 Unprocessable Entity` | バリデーション失敗（必須パラメータ不足等） |
| `500 Internal Server Error` | サーバー内部エラー |

### §2-6. 日時フォーマット

全日時は **ISO8601 UTC** 形式: `2026-03-15T17:00:00Z`

UI側で JST 変換する。

### §2-7. warnings フィールド（部分的成功）

一部のエンドポイントでは、200 OK レスポンスの `meta` に `warnings` 配列を付与する場合がある。
これはリクエストが正常に処理されたが、品質上の注意事項がある場合を示す。

> **設計判断**: EVIDENCE_MISSING を 422 エラーではなく 200 + warnings とした理由:
> 根拠欠落は不正リクエストではなく LLM 出力の品質問題。データは有用で人間レビュー対象。
> 既存の `status='needs_review'` + `confidence_score` パターンと一貫。

**warnings 付きレスポンス例:**

```json
{
  "data": { ... },
  "meta": {
    "timestamp": "2026-03-01T06:15:00Z",
    "request_id": "uuid-v4",
    "warnings": [
      {
        "code": "EVIDENCE_MISSING",
        "message": "One or more extracted fields lack evidence references. confidence_score may be low.",
        "affected_fields": ["submission_items", "risk_factors"]
      }
    ]
  }
}
```

| warning コード | 発生条件 | 対応 |
|--------------|---------|------|
| `EVIDENCE_MISSING` | case_cards の抽出結果で根拠（evidence）が欠落している項目が存在する | UI側で `needs_review` バッジ表示 + 根拠欠落項目をハイライト |

> `warnings` は `meta` 内に配列で格納。空の場合は `warnings` キー自体を省略する。
> 今後、Phase2 で追加の warning コードを定義する可能性がある。

---

## §3 エンドポイント一覧

### §3-1. 全エンドポイント（28件）

| # | Method | Path | 説明 | 冪等 |
|---|--------|------|------|------|
| **Cases（案件）** | | | | |
| 1 | GET | `/api/v1/cases` | 案件一覧（フィルタ・ソート・ページネーション） | ○ |
| 2 | GET | `/api/v1/cases/:id` | 案件詳細（related リソース embed 可） | ○ |
| **Case Actions（案件アクション）** | | | | |
| 3 | POST | `/api/v1/cases/:id/actions/mark-reviewed` | 確認済みに変更 | — |
| 4 | POST | `/api/v1/cases/:id/actions/mark-planned` | 応札予定に変更（→ reading_queued カスケード） | — |
| 5 | POST | `/api/v1/cases/:id/actions/mark-skipped` | 見送りに変更（reason 必須） | — |
| 6 | POST | `/api/v1/cases/:id/actions/restore` | skipped から復帰 | — |
| 7 | POST | `/api/v1/cases/:id/actions/archive` | 手動アーカイブ | — |
| 8 | POST | `/api/v1/cases/:id/actions/retry-reading` | 再読解（G3/G6） | — |
| 9 | POST | `/api/v1/cases/:id/actions/retry-judging` | 再判定（G5/G7） | — |
| 10 | POST | `/api/v1/cases/:id/actions/retry-checklist` | チェックリスト再生成（G8） | — |
| 11 | POST | `/api/v1/cases/:id/actions/override` | 判定オーバーライド（G4） | — |
| **Case Cards（AI読解結果）** | | | | |
| 12 | GET | `/api/v1/cases/:id/card` | 最新版（is_current=true） | ○ |
| 13 | GET | `/api/v1/cases/:id/cards` | 全バージョン（version DESC） | ○ |
| 14 | POST | `/api/v1/case-cards/:id/actions/mark-reviewed` | 人間確認済みに変更 | — |
| **Eligibility Results（参加可否判定）** | | | | |
| 15 | GET | `/api/v1/cases/:id/eligibility` | 最新版 | ○ |
| 16 | GET | `/api/v1/cases/:id/eligibilities` | 全バージョン | ○ |
| **Checklists（チェックリスト）** | | | | |
| 17 | GET | `/api/v1/cases/:id/checklist` | 最新版 | ○ |
| 18 | GET | `/api/v1/cases/:id/checklists` | 全バージョン | ○ |
| 19 | PATCH | `/api/v1/checklists/:id/items/:item_id` | チェック/アンチェック | ○（冪等） |
| 20 | POST | `/api/v1/checklists/:id/items` | 手動項目追加 | — |
| **Case Events（イベント履歴）** | | | | |
| 21 | GET | `/api/v1/cases/:id/events` | イベント履歴（ページネーション + フィルタ） | ○ |
| **Batch（バッチ管理）** | | | | |
| 22 | GET | `/api/v1/batch/latest` | 最新バッチ状態 | ○ |
| 23 | GET | `/api/v1/batch/logs` | バッチ履歴 | ○ |
| 24 | GET | `/api/v1/batch/logs/:id` | バッチ詳細 | ○ |
| 25 | POST | `/api/v1/batch/trigger` | 手動バッチ起動 | — |
| **Company Profile（会社プロフィール）** | | | | |
| 26 | GET | `/api/v1/company-profile` | 取得（Phase1: 1レコード固定） | ○ |
| 27 | PATCH | `/api/v1/company-profile` | 更新 | ○（冪等） |
| **Price Analytics（価格分析）** | | | | |
| 28 | GET | `/api/v1/analytics/price-summary` | 価格分析サマリ（フィルタ付き） | ○ |

---

## §4 リソース別エンドポイント詳細

### §4-1. Cases（案件）

#### `GET /api/v1/cases` — 案件一覧

**クエリパラメータ:**

| パラメータ | 型 | デフォルト | 説明 |
|-----------|-----|-----------|------|
| `lifecycle_stage` | string | — | ステージフィルタ（カンマ区切りで複数可: `scored,under_review`） |
| `status` | string | — | cases.status フィルタ（`new`, `reviewed`, `planned`, `skipped`, `archived`） |
| `score_min` | int | — | スコア下限（0-100） |
| `score_max` | int | — | スコア上限（0-100） |
| `deadline_before` | string | — | 提出期限上限（ISO8601） |
| `deadline_after` | string | — | 提出期限下限（ISO8601） |
| `needs_review` | bool | — | `true`: case_cards.status='needs_review' の案件のみ |
| `has_failed` | bool | — | `true`: `*_failed` ステージの案件のみ |
| `search` | string | — | 案件名・発注機関の部分一致検索 |
| `sort` | string | `deadline_at:asc` | ソート順（`field:direction` 形式、カンマ区切り複数可）。許可値: `deadline_at:asc/desc`, `score:desc/asc`, `first_seen_at:desc/asc`, `case_name:asc/desc`, `needs_review:desc`。複合例: `needs_review:desc,deadline_at:asc` |
| `page` | int | 1 | ページ番号 |
| `limit` | int | 20 | 1ページあたり件数（最大100） |
| `exclude_archived` | bool | `true` | `false` でアーカイブ済みを含む |

> `sort` に許可値以外のフィールド/方向を指定した場合は 422 `VALIDATION_ERROR` を返す。
> デフォルト `deadline_at:asc` は提出期限が近い順。ダッシュボードの推奨ビュー。

**レスポンス（200 OK）:**

```json
{
  "data": [
    {
      "id": "uuid",
      "source": "chotatku_portal",
      "source_id": "2026-0001234",
      "case_name": "○○省 配送業務委託",
      "issuing_org": "○○省",
      "bid_type": "一般競争入札",
      "category": "役務の提供",
      "region": "関東・甲信越",
      "grade": "D",
      "submission_deadline": "2026-03-15T17:00:00Z",
      "opening_date": "2026-03-20T10:00:00Z",
      "status": "planned",
      "current_lifecycle_stage": "reading_completed",
      "score": 85,
      "score_detail": { "competition": 25, "scale": 20, "deadline_margin": 22, "relevance": 18, "total": 85 },
      "first_seen_at": "2026-02-28T06:00:00Z",
      "last_updated_at": "2026-03-01T06:15:00Z"
    }
  ],
  "meta": { "page": 1, "limit": 20, "total": 42, "total_pages": 3 }
}
```

#### `GET /api/v1/cases/:id` — 案件詳細

**クエリパラメータ:**

| パラメータ | 型 | デフォルト | 説明 |
|-----------|-----|-----------|------|
| `include` | string | — | Enum（カンマ区切り複数可）: `card_current`, `eligibility_current`, `checklist_current`, `latest_events`。未指定時は含まれない（`null`） |

**レスポンス（200 OK）:**

```json
{
  "data": {
    "id": "uuid",
    "source": "chotatku_portal",
    "source_id": "2026-0001234",
    "case_name": "○○省 配送業務委託",
    "issuing_org": "○○省",
    "issuing_org_code": "012",
    "bid_type": "一般競争入札",
    "category": "役務の提供",
    "region": "関東・甲信越",
    "grade": "D",
    "submission_deadline": "2026-03-15T17:00:00Z",
    "opening_date": "2026-03-20T10:00:00Z",
    "spec_url": "https://...",
    "notice_url": "https://...",
    "detail_url": "https://...",
    "status": "planned",
    "current_lifecycle_stage": "checklist_active",
    "score": 85,
    "score_detail": { ... },
    "first_seen_at": "2026-02-28T06:00:00Z",
    "last_updated_at": "2026-03-01T06:15:00Z",
    "card": { ... },
    "eligibility": { ... },
    "checklist": { ... }
  }
}
```

> `include` 未指定時は関連リソースは含まれない（`null`）。
> Phase1 は Enum 固定（embed 肥大化防止）。`include=all` は Phase2 で導入（§8 参照）。
> 複数指定例: `?include=card_current,eligibility_current`
> 個別取得は §4-3〜§4-5 のエンドポイントを使用。

---

### §4-2. Case Actions（案件アクション — Command パターン）

> 全アクションは SSOT-2 §2-2 のゲートポイント + §3 の状態遷移テーブルに対応する。
> 全アクションは case_events に自動でイベントを INSERT し、レスポンスに含める。

#### 共通リクエストボディ

```json
{
  "expected_lifecycle_stage": "under_review"
}
```

> `expected_lifecycle_stage` は全アクションで**推奨**（Phase1 は省略可能）。
> サーバー側で現在の `current_lifecycle_stage` と比較し、不一致なら 409 を返す。

#### 共通レスポンス構造（200 OK）

```json
{
  "data": {
    "case": { ... },
    "event": {
      "id": "uuid",
      "event_type": "case_marked_planned",
      "from_status": "under_review",
      "to_status": "planned",
      "triggered_by": "user",
      "actor_id": "kaneko",
      "feature_origin": "F-001",
      "payload": { "reason": "相場が合いそう" },
      "created_at": "2026-03-01T10:00:00Z"
    },
    "cascade_events": []
  }
}
```

> `cascade_events`: カスケードで発生した後続イベントの配列。
> 例: `mark-planned` → `reading_queued` のカスケードイベントが含まれる。

#### 再実行共通オプション（retry 系全エンドポイント）

> retry-reading / retry-judging / retry-checklist の3エンドポイントに共通するオプションパラメータ。

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `reason` | string | —（推奨） | 再実行理由。case_events.payload.reason に記録される。例: `"仕様書が更新されたため"` |
| `scope` | string | — | `"soft"`（デフォルト）: 既存データを最大限再利用（SHA-256 キャッシュ等）。`"force"`: 全ステップを強制再実行。SSOT-5 §3 で詳細定義 |

> `reason` は case_events.payload に記録され、監査ログとして保持される。
> `scope` の `soft` / `force` の具体的な挙動差は SSOT-5 §3（再実行スコープ）で定義。

#### 個別アクション

**`POST /api/v1/cases/:id/actions/mark-reviewed`**

| 項目 | 値 |
|------|-----|
| SSOT-2 遷移 | T02: `scored` → `under_review` |
| event_type | `case_marked_reviewed` |
| Body | `{ expected_lifecycle_stage?: "scored" }` |
| 許可される from | `scored`, `skipped`（G9 復帰兼用） |

**`POST /api/v1/cases/:id/actions/mark-planned`**

| 項目 | 値 |
|------|-----|
| SSOT-2 遷移 | T03: `under_review` → `planned` |
| event_type | `case_marked_planned` |
| Body | `{ expected_lifecycle_stage?: "under_review", reason?: "string" }` |
| 許可される from | `under_review` |
| カスケード | T05: `planned` → `reading_queued`（自動。cascade_events に含まれる） |

**`POST /api/v1/cases/:id/actions/mark-skipped`**

| 項目 | 値 |
|------|-----|
| SSOT-2 遷移 | T04: `under_review` → `skipped` |
| event_type | `case_marked_skipped` |
| Body | `{ expected_lifecycle_stage?: "under_review", reason: "string" }` |
| 許可される from | `under_review` |
| バリデーション | `reason` は必須（空文字不可） |

**`POST /api/v1/cases/:id/actions/restore`**

| 項目 | 値 |
|------|-----|
| SSOT-2 遷移 | T25: `skipped` → `under_review` |
| event_type | `case_marked_reviewed` |
| Body | `{ expected_lifecycle_stage?: "skipped" }` |
| 許可される from | `skipped` |

**`POST /api/v1/cases/:id/actions/archive`**

| 項目 | 値 |
|------|-----|
| SSOT-2 遷移 | T40: 任意 → `archived` |
| event_type | `case_archived` |
| Body | `{ expected_lifecycle_stage?: "string" }` |
| 許可される from | `archived` 以外の全ステージ |
| 副作用 | `cases.archived_at` にタイムスタンプ設定。`checklists.status` → `archived` |

**`POST /api/v1/cases/:id/actions/retry-reading`**

| 項目 | 値 |
|------|-----|
| SSOT-2 遷移 | T20: `reading_failed` → `reading_queued`（G3）/ T22: `reading_completed` → `reading_queued`（G6） |
| event_type | `reading_requeued` |
| Body | `{ expected_lifecycle_stage?: "reading_failed" \| "reading_completed", reason?: "string", scope?: "soft" \| "force" }` |
| 許可される from | `reading_failed`, `reading_completed` |
| 副作用 | 新 case_cards version を作成（SSOT-4 §6 参照）。カスケード: 下流（judging, checklist）も再実行 |
| payload 必須キー | `previous_version`（SSOT-4 §3-9b） |

**`POST /api/v1/cases/:id/actions/retry-judging`**

| 項目 | 値 |
|------|-----|
| SSOT-2 遷移 | T21: `judging_failed` → `judging_queued`（G5）/ T23: `judging_completed` → `judging_queued`（G7） |
| event_type | `judging_requeued` |
| Body | `{ expected_lifecycle_stage?: "judging_failed" \| "judging_completed", reason?: "string", scope?: "soft" \| "force" }` |
| 許可される from | `judging_failed`, `judging_completed` |
| 副作用 | 新 eligibility_results version を作成。カスケード: checklist も再生成（verdict=eligible の場合） |
| payload 必須キー | `previous_version` |

**`POST /api/v1/cases/:id/actions/retry-checklist`**

| 項目 | 値 |
|------|-----|
| SSOT-2 遷移 | T24: `checklist_active` → `checklist_generating`（G8） |
| event_type | `checklist_requeued` |
| Body | `{ expected_lifecycle_stage?: "checklist_active", reason?: "string", scope?: "soft" \| "force" }` |
| 許可される from | `checklist_active` |
| 副作用 | 新 checklists version を作成 |
| payload 必須キー | `previous_version` |

**`POST /api/v1/cases/:id/actions/override`**

| 項目 | 値 |
|------|-----|
| SSOT-2 遷移 | T30: `judging_completed`（ステージ変更なし。メタデータ更新） |
| event_type | `eligibility_overridden` |
| Body | `{ expected_lifecycle_stage?: "judging_completed", verdict: "eligible" \| "ineligible", reason: "string" }` |
| 許可される from | `judging_completed` |
| バリデーション | `verdict` と `reason` は必須。`reason` は空文字不可 |
| 副作用 | `eligibility_results.human_override` 更新。verdict=eligible → カスケード T13（`checklist_generating`） |
| payload 必須キー | `previous_verdict`, `new_verdict`, `override_reason`（SSOT-4 §3-9b） |

---

### §4-3. Case Cards（AI読解結果）

#### `GET /api/v1/cases/:id/card` — 最新版

> `is_current=true` のレコードを返す。存在しない場合は 404。

**レスポンス（200 OK）:**

```json
{
  "data": {
    "id": "uuid",
    "case_id": "uuid",
    "version": 2,
    "is_current": true,
    "eligibility": { ... },
    "schedule": { ... },
    "business_content": { ... },
    "submission_items": { ... },
    "risk_factors": [ ... ],
    "deadline_at": "2026-03-15T17:00:00Z",
    "business_type": "役務の提供",
    "risk_level": "medium",
    "extraction_method": "text",
    "is_scanned": false,
    "assertion_counts": { "fact": 12, "inferred": 3, "caution": 1 },
    "evidence": { ... },
    "confidence_score": 0.85,
    "file_hash": "sha256:abc123...",
    "status": "needs_review",
    "llm_model": "claude-3-5-sonnet-20241022",
    "token_usage": { "input": 5000, "output": 2000 },
    "extracted_at": "2026-03-01T06:15:00Z",
    "reviewed_at": null,
    "reviewed_by": null,
    "created_at": "2026-03-01T06:15:00Z"
  }
}
```

#### `GET /api/v1/cases/:id/cards` — 全バージョン

> `version DESC` でソートして返す。ページネーション付き。

#### `POST /api/v1/case-cards/:id/actions/mark-reviewed` — 人間確認

| 項目 | 値 |
|------|-----|
| event_type | `reading_reviewed` |
| Body | `{}` |
| 副作用 | `case_cards.reviewed_at` = NOW(), `case_cards.reviewed_by` = 'kaneko' |

> ステージ遷移は発生しない（SSOT-2 §7-5 参照）。case_events には記録される。

---

### §4-4. Eligibility Results（参加可否判定）

#### `GET /api/v1/cases/:id/eligibility` — 最新版

**レスポンス（200 OK）:**

```json
{
  "data": {
    "id": "uuid",
    "case_id": "uuid",
    "case_card_id": "uuid",
    "version": 1,
    "is_current": true,
    "verdict": "uncertain",
    "confidence": 0.72,
    "hard_fail_reasons": [],
    "soft_gaps": [ { "rule_id": "soft_1_experience", "label": "実績要件", "severity": "high", ... } ],
    "check_details": { "hard_checks": [ ... ], "soft_checks": [ ... ] },
    "company_profile_snapshot": { ... },
    "human_override": null,
    "override_reason": null,
    "overridden_at": null,
    "judged_at": "2026-03-01T06:20:00Z",
    "created_at": "2026-03-01T06:20:00Z"
  }
}
```

#### `GET /api/v1/cases/:id/eligibilities` — 全バージョン

> `version DESC` でソートして返す。ページネーション付き。

> **注**: オーバーライドは `POST /cases/:id/actions/override`（§4-2）で実行する。

---

### §4-5. Checklists（チェックリスト）

#### `GET /api/v1/cases/:id/checklist` — 最新版

**レスポンス（200 OK）:**

```json
{
  "data": {
    "id": "uuid",
    "case_id": "uuid",
    "case_card_id": "uuid",
    "eligibility_result_id": "uuid",
    "version": 1,
    "is_current": true,
    "checklist_items": [
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
        "evidence_ref": { ... }
      }
    ],
    "schedule_items": [ ... ],
    "warnings": [],
    "progress": { "total": 8, "done": 3, "rate": 0.375 },
    "status": "active",
    "generated_at": "2026-03-01T06:25:00Z",
    "completed_at": null,
    "created_at": "2026-03-01T06:25:00Z"
  }
}
```

#### `GET /api/v1/cases/:id/checklists` — 全バージョン

> `version DESC` でソートして返す。ページネーション付き。

#### `PATCH /api/v1/checklists/:id/items/:item_id` — チェック / アンチェック

**リクエストボディ:**

```json
{
  "status": "done"
}
```

| フィールド | 型 | 必須 | 値 |
|-----------|-----|------|-----|
| `status` | string | ○ | `"pending"` or `"done"` |
| `expected_checklist_version` | int | — | 指定時: サーバー側で `checklists.version` と比較。不一致なら 409 `CHECKLIST_VERSION_MISMATCH`。マルチタブ/マルチユーザー競合検出用 |

**冪等性**: 同じ `status` を再送しても 200 OK を返す（変更なし）。

> `expected_checklist_version` は Phase1 は任意。マルチタブでの同時操作が発生した際の競合検出に使用。
> 409 が返った場合、クライアントは最新の checklist を再取得してからリトライする。

**副作用**:
- `checklist_items[item_id].status` を更新
- `checklist_items[item_id].checked_at` を設定（done 時）or null（pending 時）
- `progress` を再計算
- case_events に `checklist_item_checked` or `checklist_item_unchecked` を記録
- 全項目 done → `checklists.status` = `completed`, `current_lifecycle_stage` = `checklist_completed`
- done から pending に戻した場合 → `checklists.status` = `active`, `current_lifecycle_stage` = `checklist_active`（T26）

**レスポンス（200 OK）:**

```json
{
  "data": {
    "checklist": { ... },
    "event": {
      "event_type": "checklist_item_checked",
      "payload": {
        "checklist_id": "uuid",
        "item_id": "bid_001",
        "item_name": "入札書の記入",
        "progress": { "total": 8, "done": 4, "rate": 0.5 }
      }
    }
  }
}
```

#### `POST /api/v1/checklists/:id/items` — 手動項目追加

**リクエストボディ:**

```json
{
  "name": "社印の手配",
  "phase": "bid_time",
  "deadline": "2026-03-14",
  "notes": "総務に依頼済み"
}
```

**副作用**: `source = "manual"` で checklist_items に追加。`progress.total` を +1。

---

### §4-6. Case Events（イベント履歴）

#### `GET /api/v1/cases/:id/events` — イベント履歴

**クエリパラメータ:**

| パラメータ | 型 | デフォルト | 説明 |
|-----------|-----|-----------|------|
| `event_type` | string | — | イベントタイプフィルタ（カンマ区切り） |
| `feature_origin` | string | — | 機能フィルタ: `F-001`, `F-002`, etc. |
| `triggered_by` | string | — | 発火元: `user`, `system`, `batch`, `cascade` |
| `created_after` | string | — | 日時下限（ISO8601） |
| `created_before` | string | — | 日時上限（ISO8601） |
| `fold` | string | — | `check_operations`: チェック操作をグルーピング（SSOT-2 §7-5 参照） |
| `since_event_id` | string (UUID) | — | 指定イベント ID 以降のイベントのみ返す（その ID 自体は含まない）。`since_ts` と排他。効率的ポーリング用 |
| `since_ts` | string (ISO8601) | — | 指定日時以降のイベントのみ返す。`since_event_id` と排他。`since_event_id` が指定された場合は無視 |
| `page` | int | 1 | ページ番号 |
| `limit` | int | 50 | 1ページあたり件数（最大200） |

> `since_event_id` と `since_ts` を同時指定した場合は `since_event_id` が優先される。
> ポーリング用途では `since_event_id` を推奨（日時スキューなし）。
> 初回取得（全件）: パラメータ省略。以降のポーリング: レスポンスの最後のイベント `id` を `since_event_id` に指定。

**`fold=check_operations` の動作:**

チェック操作（`checklist_item_checked`, `checklist_item_unchecked`）を1つのサマリーエントリにまとめる。

```json
{
  "event_type": "_folded_check_operations",
  "count": 5,
  "first_at": "2026-03-02T10:00:00Z",
  "last_at": "2026-03-02T14:30:00Z",
  "summary": { "checked": 4, "unchecked": 1 }
}
```

**レスポンス（200 OK）:**

```json
{
  "data": [
    {
      "id": "uuid",
      "case_id": "uuid",
      "event_type": "case_marked_planned",
      "from_status": "under_review",
      "to_status": "planned",
      "triggered_by": "user",
      "actor_id": "kaneko",
      "feature_origin": "F-001",
      "payload": { "reason": "相場が合いそう" },
      "created_at": "2026-03-01T10:00:00Z"
    }
  ],
  "meta": { "page": 1, "limit": 50, "total": 23, "total_pages": 1 }
}
```

---

### §4-7. Batch（バッチ管理）

#### `GET /api/v1/batch/latest` — 最新バッチ状態

> ダッシュボードの60秒ポーリング対象（SSOT-2 §6-6）。

**レスポンス（200 OK）:**

```json
{
  "data": {
    "id": "uuid",
    "source": "chotatku_portal",
    "feature_origin": "F-001",
    "batch_type": "case_fetch",
    "started_at": "2026-03-01T06:00:00Z",
    "finished_at": "2026-03-01T06:05:00Z",
    "status": "success",
    "total_fetched": 150,
    "new_count": 12,
    "updated_count": 5,
    "unchanged_count": 133,
    "error_count": 0,
    "error_details": null,
    "metadata": null
  }
}
```

#### `GET /api/v1/batch/logs` — バッチ履歴

> ページネーション付き。`started_at DESC` でソート。

#### `GET /api/v1/batch/logs/:id` — バッチ詳細

#### `POST /api/v1/batch/trigger` — 手動バッチ起動

**リクエストボディ:**

```json
{
  "source": "chotatku_portal",
  "batch_type": "case_fetch"
}
```

| フィールド | 型 | 必須 | 値 |
|-----------|-----|------|-----|
| `source` | string | ○ | `"chotatku_portal"`, `"od_csv"` |
| `batch_type` | string | ○ | `"case_fetch"`, `"od_import"`, `"detail_scrape"` |

**バリデーション**: 同じ source + batch_type のバッチが `running` 状態なら 409 `BATCH_ALREADY_RUNNING`。

**レスポンス（201 Created）:**

```json
{
  "data": {
    "batch_log_id": "uuid",
    "status": "running"
  }
}
```

---

### §4-8. Company Profile（会社プロフィール）

#### `GET /api/v1/company-profile` — 取得

> Phase1 は1レコード固定。

**レスポンス（200 OK）:**

```json
{
  "data": {
    "id": "uuid",
    "unified_qualification": true,
    "grade": "D",
    "business_categories": ["物品の販売", "役務の提供その他"],
    "regions": ["関東・甲信越"],
    "licenses": [],
    "certifications": [],
    "experience": [],
    "subcontractors": [
      { "name": "クローバー運輸", "license": "運送業", "capabilities": ["軽運送", "配送"] },
      { "name": "電気工事会社", "license": "電気工事業", "capabilities": ["電気工事"] },
      { "name": "内装関係", "license": "内装業", "capabilities": ["内装工事"] }
    ],
    "updated_at": "2026-02-20T10:00:00Z",
    "created_at": "2026-02-20T10:00:00Z"
  }
}
```

#### `PATCH /api/v1/company-profile` — 更新

**リクエストボディ（部分更新）:**

```json
{
  "licenses": ["一般貨物自動車運送事業許可"],
  "experience": [{ "description": "○○省 配送業務", "year": 2025 }]
}
```

> 指定されたフィールドのみ更新。未指定フィールドは変更なし。

---

### §4-9. Price Analytics（価格分析）

#### `GET /api/v1/analytics/price-summary` — 価格分析サマリ

**クエリパラメータ:**

| パラメータ | 型 | デフォルト | 説明 |
|-----------|-----|-----------|------|
| `keyword` | string | — | 案件名キーワード |
| `issuing_org` | string | — | 発注機関フィルタ |
| `category` | string | — | カテゴリフィルタ |
| `period_months` | int | 36 | 分析対象期間（月数） |

**レスポンス（200 OK）:**

```json
{
  "data": {
    "total_records": 1250,
    "period": { "from": "2023-03-01", "to": "2026-03-01" },
    "amount_stats": {
      "median": 1200000,
      "q1": 800000,
      "q3": 1800000,
      "mean": 1350000,
      "min": 200000,
      "max": 5000000
    },
    "participants_stats": {
      "median": 3,
      "mean": 3.5,
      "single_bid_rate": 0.25
    },
    "winning_rate_by_amount": [
      { "range": "0-500k", "win_rate": 0.85 },
      { "range": "500k-1M", "win_rate": 0.65 },
      { "range": "1M-2M", "win_rate": 0.55 }
    ],
    "trend_by_quarter": [
      { "quarter": "2025-Q4", "median_amount": 1150000, "avg_participants": 3.2 }
    ]
  }
}
```

---

## §5 リクエスト/レスポンス型定義（Pydantic）

> 実装時に FastAPI の Pydantic モデルとして定義する。ここでは主要な型の概要のみ示す。
> SSOT-2 §6-2 の TypeScript 型と 1:1 対応する。

### §5-1. 型対応表

| Pydantic モデル | TypeScript 型 | SSOT-4 テーブル |
|----------------|--------------|---------------|
| `CaseResponse` | `Case` | cases |
| `CaseCardResponse` | `CaseCard` | case_cards |
| `EligibilityResultResponse` | `EligibilityResult` | eligibility_results |
| `ChecklistResponse` | `Checklist` | checklists |
| `CaseEventResponse` | `CaseEvent` | case_events |
| `BatchLogResponse` | `BatchLog` | batch_logs |
| `CompanyProfileResponse` | `CompanyProfile` | company_profiles |

### §5-2. カラム名変換規則

| DB (snake_case) | API レスポンス (snake_case) | TypeScript (camelCase) |
|----------------|---------------------------|----------------------|
| `case_name` | `case_name` | `caseName` |
| `issuing_org` | `issuing_org` | `issuingOrg` |
| `current_lifecycle_stage` | `current_lifecycle_stage` | `currentLifecycleStage` |
| `is_current` | `is_current` | `isCurrent` |

> API レスポンスは **snake_case** で統一。フロントエンドで camelCase に変換する。

### §5-3. Enum 型

```python
from enum import Enum

class LifecycleStage(str, Enum):
    DISCOVERED = "discovered"
    SCORED = "scored"
    UNDER_REVIEW = "under_review"
    PLANNED = "planned"
    SKIPPED = "skipped"
    READING_QUEUED = "reading_queued"
    READING_IN_PROGRESS = "reading_in_progress"
    READING_COMPLETED = "reading_completed"
    READING_FAILED = "reading_failed"
    JUDGING_QUEUED = "judging_queued"
    JUDGING_IN_PROGRESS = "judging_in_progress"
    JUDGING_COMPLETED = "judging_completed"
    JUDGING_FAILED = "judging_failed"
    CHECKLIST_GENERATING = "checklist_generating"
    CHECKLIST_ACTIVE = "checklist_active"
    CHECKLIST_COMPLETED = "checklist_completed"
    ARCHIVED = "archived"

class CaseStatus(str, Enum):
    NEW = "new"
    REVIEWED = "reviewed"
    PLANNED = "planned"
    SKIPPED = "skipped"
    ARCHIVED = "archived"

class Verdict(str, Enum):
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"
    UNCERTAIN = "uncertain"

class ChecklistItemStatus(str, Enum):
    PENDING = "pending"
    DONE = "done"

class TriggeredBy(str, Enum):
    SYSTEM = "system"
    USER = "user"
    BATCH = "batch"
    CASCADE = "cascade"

class IncludeParam(str, Enum):
    CARD_CURRENT = "card_current"
    ELIGIBILITY_CURRENT = "eligibility_current"
    CHECKLIST_CURRENT = "checklist_current"
    LATEST_EVENTS = "latest_events"

class SortField(str, Enum):
    DEADLINE_AT = "deadline_at"
    SCORE = "score"
    FIRST_SEEN_AT = "first_seen_at"
    CASE_NAME = "case_name"
    NEEDS_REVIEW = "needs_review"

class SortDirection(str, Enum):
    ASC = "asc"
    DESC = "desc"

class RetryScope(str, Enum):
    SOFT = "soft"
    FORCE = "force"
```

---

## §6 冪等性と楽観ロック

### §6-1. 楽観ロック

| 項目 | 詳細 |
|------|------|
| パラメータ | `expected_lifecycle_stage`（リクエストボディ内） |
| 対象 | §4-2 の全 Case Actions |
| 動作 | サーバー側で `cases.current_lifecycle_stage` と比較。不一致 → 409 `STAGE_MISMATCH` |
| Phase1 | 省略可能（省略時はチェックをスキップ） |
| Phase2 | 必須化 |

**409 STAGE_MISMATCH レスポンス例:**

```json
{
  "data": null,
  "error": {
    "code": "STAGE_MISMATCH",
    "message": "Current lifecycle stage has changed. Expected 'under_review' but found 'reading_queued'.",
    "details": {
      "expected": "under_review",
      "actual": "reading_queued"
    }
  }
}
```

### §6-2. チェック操作の冪等性

| 操作 | 同じ値の再送 | レスポンス |
|------|------------|----------|
| `PATCH /checklists/:id/items/:item_id` `{status: "done"}` → 既に done | 200 OK | 変更なし。event は記録しない |
| `PATCH /checklists/:id/items/:item_id` `{status: "pending"}` → 既に pending | 200 OK | 変更なし。event は記録しない |

### §6-3. リトライ/再実行の冪等性

| 操作 | 既に *_queued ステージ | レスポンス |
|------|---------------------|----------|
| `POST /actions/retry-reading` → 既に `reading_queued` | 200 OK | 重複リクエスト許容。新イベントは記録しない |
| `POST /actions/retry-judging` → 既に `judging_queued` | 200 OK | 同上 |
| `POST /actions/retry-checklist` → 既に `checklist_generating` | 200 OK | 同上 |

### §6-4. Idempotency-Key（Phase2 向け）

| Phase | 動作 |
|-------|------|
| Phase1 | `Idempotency-Key` ヘッダーは受け付けるが検証しない（ログ記録のみ） |
| Phase2 | POST 系に必須。同一キーの再送は前回と同じレスポンスを返す（Redis に 24h キャッシュ） |

---

## §7 エラーコード一覧

| コード | HTTP | 説明 | 発生条件 |
|-------|------|------|---------|
| `INVALID_TRANSITION` | 409 | 不正な状態遷移 | SSOT-2 §3-5 の不正遷移を試行した場合 |
| `STAGE_MISMATCH` | 409 | 楽観ロック不一致 | `expected_lifecycle_stage` と現在値が不一致 |
| `PIPELINE_IN_PROGRESS` | 409 | パイプライン実行中 | `*_queued`, `*_in_progress`, `*_generating` ステージでアクション実行を試行（SSOT-2 §2-4） |
| `BATCH_ALREADY_RUNNING` | 409 | バッチ実行中 | 同一 source + batch_type のバッチが running 中に trigger |
| `CHECKLIST_VERSION_MISMATCH` | 409 | チェックリストバージョン不一致 | `expected_checklist_version` が現在の `checklists.version` と不一致 |
| `NOT_FOUND` | 404 | リソース不在 | 指定 ID のリソースが存在しない |
| `CASE_CARD_NOT_FOUND` | 404 | 案件カード不在 | is_current=true の case_card が存在しない（未読解） |
| `ELIGIBILITY_NOT_FOUND` | 404 | 判定結果不在 | is_current=true の eligibility_result が存在しない（未判定） |
| `CHECKLIST_NOT_FOUND` | 404 | チェックリスト不在 | is_current=true の checklist が存在しない（未生成） |
| `CHECKLIST_ITEM_NOT_FOUND` | 404 | チェック項目不在 | 指定 item_id のチェック項目が存在しない |
| `VALIDATION_ERROR` | 422 | バリデーション失敗 | 必須パラメータ不足、型不正、範囲外の値 |
| `OVERRIDE_REASON_REQUIRED` | 422 | オーバーライド理由未指定 | override アクションで reason が空 |
| `SKIP_REASON_REQUIRED` | 422 | 見送り理由未指定 | mark-skipped アクションで reason が空 |
| `INTERNAL_ERROR` | 500 | サーバー内部エラー | DB 接続エラー、LLM API エラー等 |

---

## §8 Phase2 拡張予定

| # | 拡張 | 詳細 |
|---|------|------|
| 1 | **認証** | Bearer Token (JWT)。`Authorization: Bearer <token>` ヘッダー。ユーザー管理テーブル追加 |
| 2 | **SSE** | `GET /api/v1/cases/:id/stream` で案件のリアルタイム更新。ポーリングを代替 |
| 3 | **Webhook** | 外部連携用。ステージ遷移時に指定 URL に POST |
| 4 | **Bulk API** | `POST /api/v1/cases/bulk-actions` で複数案件を一括操作 |
| 5 | **Rate Limiting** | 429 Too Many Requests。Phase2 で SaaS 化時に必須 |
| 6 | **Idempotency-Key 必須化** | POST 系で必須に。Redis キャッシュ（24h） |
| 7 | **API キー管理** | マルチテナント用。テナントごとの API キー発行・失効 |
| 8 | **全文検索** | `GET /api/v1/cases` の `search` パラメータを PostgreSQL tsvector に移行 |
| 9 | **include=all** | `GET /api/v1/cases/:id` で全関連リソースを一括 embed。Phase1 は Enum 固定で個別指定のみ |

---

## [要確認] 一覧

| # | 項目 | 影響範囲 | 解消予定 |
|---|------|---------|---------|
| — | （なし — 全項目はプランファイルおよび v1.1 で解消済み） | — | — |

> **参考（解消済み）**:
> - Phase1 の認証方式 → 認証なし（§1 原則3）
> - GET /cases/:id の embed vs 個別取得 → Enum 固定 embed 方式（§4-1、v1.1 で 4値 Enum 化）
> - retry の種類指定方式 → 3エンドポイント分割 + scope=soft/force（§4-2、v1.1 追加）
> - 楽観ロックの方式 → expected_lifecycle_stage + expected_checklist_version（§6-1、v1.1 追加）
> - sort のデフォルト → deadline_at:asc（v1.1 で確定）
> - 根拠欠落の扱い → 200 + meta.warnings（EVIDENCE_MISSING）（§2-7、v1.1 新設）

---

## 変更履歴

| 日付 | 変更内容 | 変更者 |
|------|---------|-------|
| 2026-02-18 | 初版作成（28エンドポイント、Command パターン、楽観ロック、冪等性ルール、エラーコード13種） | Claude / 金子 |
| 2026-02-18 | v1.1: ①include Enum固定（4値、all はPhase2）②sort デフォルト deadline_at:asc + field:direction 形式 + 許可リスト ③retry 系に reason（推奨）+ scope（soft/force）追加 ④PATCH checklists に expected_checklist_version 追加 + CHECKLIST_VERSION_MISMATCH エラー ⑤events 取得に since_event_id / since_ts 増分パラメータ追加 ⑥EVIDENCE_MISSING 警告コード（200 + meta.warnings 方式）+ §2-7 新設 ⑦Enum 4種追加（IncludeParam, SortField, SortDirection, RetryScope） | Claude / 金子 |
