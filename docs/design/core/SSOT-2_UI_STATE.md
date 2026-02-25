# SSOT-2: UI/状態遷移 — 入札ラクダAI

> 案件（case）の統一ライフサイクルを定義する。
> cases.current_lifecycle_stage が全機能を横断する「今どの段階か」の SSOT。
> case_events の最新行が正規化された真実。各テーブルの status は非正規化キャッシュ。

---

## 基本情報

| 項目 | 内容 |
|------|------|
| ドキュメントID | SSOT-2 |
| ドキュメント名 | UI/状態遷移 |
| バージョン | v2.0 |
| 作成日 | 2026-02-18 |
| 最終更新日 | 2026-02-18 |
| 作成者 | Claude / 金子 裕司 |
| ステータス | Draft |

### 参照ドキュメント

| ドキュメント | パス |
|------------|------|
| SSOT-4 データモデル | docs/design/core/SSOT-4_DATA_MODEL.md |
| F-001 案件自動収集 | docs/design/features/project/F-001_案件自動収集.md |
| F-002 AI読解 | docs/design/features/project/F-002_AI読解.md |
| F-003 参加可否判定 | docs/design/features/project/F-003_参加可否判定.md |
| F-004 チェックリスト生成 | docs/design/features/project/F-004_チェックリスト生成.md |
| SSOT-3 API規約 | docs/design/core/SSOT-3_API_CONTRACT.md |

---

## §1 設計原則

| # | 原則 | 詳細 |
|---|------|------|
| 1 | **統一ライフサイクル** | `cases.current_lifecycle_stage` が全機能を横断する案件ステージの SSOT。各テーブルの `status` カラムは機能ローカルの粒度で管理し、ライフサイクルとの対応は §4 で定義 |
| 2 | **case_events が真実** | `current_lifecycle_stage` は非正規化キャッシュ。ステージ遷移は必ず case_events INSERT → current_lifecycle_stage UPDATE のセットで実行（同一トランザクション） |
| 3 | **明示的遷移のみ** | 暗黙の遷移は禁止。全遷移は §3 の状態遷移テーブルに列挙され、未定義の遷移はアプリケーション層で reject |
| 4 | **ユーザー操作はゲート** | 自動処理（パイプライン）は `cascade` で進むが、ユーザーの明示操作がないとパイプラインが起動しないゲートポイントがある（§2-2 で定義） |
| 5 | **再実行は新 version** | 再読解・再判定・再生成は既存レコードの UPDATE ではなく新 version の INSERT。旧版は `is_current=false` で保持（SSOT-4 §6 参照） |
| 6 | **failed はリトライ可能** | 全 `*_failed` ステージからは再キュー（`*_queued`）に遷移可能。ユーザー操作で明示的にリトライ |
| 7 | **Phase1 はシンプル** | SSE・WebSocket は Phase1 では使わない。ポーリング（5秒間隔）でステージ更新を取得。Phase2 で SSE に移行 |
| 8 | **UI表示の優先順位** | ① `current_lifecycle_stage`（画面のメイン状態）→ ② `case_events`（履歴・根拠・進行ログ）→ ③ 各派生テーブルの `is_current=true`（case_cards / eligibility_results / checklists の最新データ）→ ④ UIローカル状態（編集中・確認モーダル等）。競合時は番号の小さい方が勝つ |

---

## §2 統一ケースライフサイクル

### §2-1. ステージ一覧

> SSOT-4 §3-1a と完全一致。17 ステージ。

| # | ステージ | グループ | 説明 | UI ラベル | UI 色 |
|---|---------|---------|------|----------|-------|
| 1 | `discovered` | Discovery | 新規案件として検出 | 新着 | `gray` |
| 2 | `scored` | Discovery | スコアリング完了 | スコア済 | `blue` |
| 3 | `under_review` | Discovery | ユーザーが確認中 | 確認中 | `blue` |
| 4 | `planned` | Discovery | 応札予定に設定 | 応札予定 | `indigo` |
| 5 | `skipped` | Discovery | 見送り | 見送り | `gray` |
| 6 | `reading_queued` | Reading | AI読解キュー待ち | 読解待ち | `yellow` |
| 7 | `reading_in_progress` | Reading | AI読解実行中 | 読解中… | `yellow`（pulse） |
| 8 | `reading_completed` | Reading | AI読解完了 | 読解完了 | `green` |
| 9 | `reading_failed` | Reading | AI読解失敗 | 読解失敗 | `red` |
| 10 | `judging_queued` | Judging | 判定キュー待ち | 判定待ち | `yellow` |
| 11 | `judging_in_progress` | Judging | 判定実行中 | 判定中… | `yellow`（pulse） |
| 12 | `judging_completed` | Judging | 判定完了 | 判定完了 | `green` |
| 13 | `judging_failed` | Judging | 判定失敗 | 判定失敗 | `red` |
| 14 | `checklist_generating` | Preparation | チェックリスト生成中 | 生成中… | `yellow`（pulse） |
| 15 | `checklist_active` | Preparation | チェックリスト運用中 | 準備中 | `orange` |
| 16 | `checklist_completed` | Preparation | 全チェック項目完了 | 準備完了 | `green` |
| 17 | `archived` | Archive | アーカイブ済み | アーカイブ | `gray` |

### §2-2. ゲートポイント（ユーザー操作必須）

| # | ゲート | 遷移 | 操作 | 理由 | UI制約 |
|---|-------|------|------|------|--------|
| G1 | 応札意思決定 | `under_review` → `planned` | 「応札予定にする」ボタン | AI読解パイプラインの起動トリガー。ユーザーの明示的意思が必要 | `under_review` 以外 → ボタン非表示 |
| G2 | 見送り決定 | `under_review` → `skipped` | 「見送り」ボタン + 理由入力 | 見送り理由の記録が必要 | `under_review` 以外 → ボタン非表示 |
| G3 | 読解失敗リトライ | `reading_failed` → `reading_queued` | 「再読解」ボタン | 自動リトライは最大回数まで。それ以降はユーザー判断 | `reading_failed` 以外 → ボタン disabled |
| G4 | 判定オーバーライド | `judging_completed`（uncertain）→ human_override 設定 | オーバーライドパネル | uncertain 案件の最終判断は人間 | `judging_completed` かつ verdict=uncertain → パネル表示。eligible/ineligible → 読み取り専用 |
| G5 | 判定失敗リトライ | `judging_failed` → `judging_queued` | 「再判定」ボタン | 手動リトライ | `judging_failed` 以外 → ボタン disabled |
| G6 | 再読解リクエスト | `reading_completed` → `reading_queued` | 「再読解」ボタン | 仕様書更新時等。新 version 作成 | `reading_completed` 以外 → ボタン disabled |
| G7 | 再判定リクエスト | `judging_completed` → `judging_queued` | 「再判定」ボタン | プロフィール更新時等。新 version 作成 | `judging_completed` 以外 → ボタン disabled |
| G8 | チェックリスト再生成 | `checklist_active` → `checklist_generating` | 「再生成」ボタン | 再判定後等。新 version 作成 | `checklist_active` 以外 → ボタン disabled |
| G9 | skipped 復帰 | `skipped` → `under_review` | 「復帰」ボタン | 見送った案件を再検討 | `skipped` 以外 → ボタン非表示 |

### §2-3. 自動遷移（cascade / system / batch）

| # | 遷移 | triggered_by | 条件 |
|---|------|-------------|------|
| A1 | `discovered` → `scored` | batch | F-001 スコアリングバッチ完了時 |
| A2 | `planned` → `reading_queued` | cascade | G1 操作の直後に自動 |
| A3 | `reading_queued` → `reading_in_progress` | system | ワーカーがキューからピックアップ |
| A4 | `reading_in_progress` → `reading_completed` | system | F-002 パイプライン正常完了 |
| A5 | `reading_in_progress` → `reading_failed` | system | F-002 パイプライン異常終了 |
| A6 | `reading_completed` → `judging_queued` | cascade | 読解完了の直後に自動 |
| A7 | `judging_queued` → `judging_in_progress` | system | ワーカーがキューからピックアップ |
| A8 | `judging_in_progress` → `judging_completed` | system | F-003 判定正常完了 |
| A9 | `judging_in_progress` → `judging_failed` | system | F-003 判定異常終了 |
| A10 | `judging_completed` → `checklist_generating` | cascade | verdict=eligible（または human_override=eligible）の場合のみ |
| A11 | `checklist_generating` → `checklist_active` | system | F-004 生成正常完了 |
| A12 | `checklist_active` → `checklist_completed` | system | 全チェック項目が done になった時点で自動 |
| A13 | 任意 → `archived` | system/batch | 期限超過で自動アーカイブ（日次バッチ） |
| A14 | `checklist_generating` → `reading_failed` に準じた失敗 | system | チェックリスト生成失敗（ただし lifecycle は `judging_completed` に戻らず、別途 `checklist_generation_failed` として扱う — 下記 §3 参照） |

### §2-4. 相反操作の排他ルール

| # | ルール | 詳細 |
|---|-------|------|
| 1 | **同一案件の同時パイプライン禁止** | `reading_in_progress` 中に再読解不可。`judging_in_progress` 中に再判定不可。`*_queued`, `*_in_progress`, `*_generating` ステージでは対応するリトライ/再実行ボタンを disabled |
| 2 | **進行中はアクション制限** | ステージが `*_queued`, `*_in_progress`, `*_generating` のいずれかなら全アクションボタンを disabled（手動アーカイブのみ例外） |
| 3 | **楽観ロック（Phase1 簡易版）** | API リクエストに `expected_lifecycle_stage` を含める。サーバー側で現在値と不一致なら **409 Conflict** を返す。UI は再取得して表示を更新。詳細は SSOT-3 §6 参照 |

---

## §3 状態遷移テーブル

> 全有効遷移を網羅的に列挙する。ここに記載されていない遷移は無効（アプリケーション層で reject）。

### §3-1. 正方向の遷移（ハッピーパス + 分岐）

| # | from | to | event_type | feature | triggered_by | 備考 |
|---|------|----|-----------|---------|-------------|------|
| T01 | `discovered` | `scored` | `case_scored` | F-001 | batch | スコアリングバッチ完了 |
| T02 | `scored` | `under_review` | `case_marked_reviewed` | F-001 | user | ユーザーが案件を確認 |
| T03 | `under_review` | `planned` | `case_marked_planned` | F-001 | user | **G1: 応札意思決定** |
| T04 | `under_review` | `skipped` | `case_marked_skipped` | F-001 | user | **G2: 見送り** |
| T05 | `planned` | `reading_queued` | `reading_queued` | F-002 | cascade | G1 直後に自動 |
| T06 | `reading_queued` | `reading_in_progress` | `reading_started` | F-002 | system | ワーカーピックアップ |
| T07 | `reading_in_progress` | `reading_completed` | `reading_completed` | F-002 | system | 読解正常完了 |
| T08 | `reading_in_progress` | `reading_failed` | `reading_failed` | F-002 | system | 読解異常終了 |
| T09 | `reading_completed` | `judging_queued` | `judging_queued` | F-003 | cascade | 読解完了直後に自動 |
| T10 | `judging_queued` | `judging_in_progress` | `judging_queued`→`started` | F-003 | system | ワーカーピックアップ |
| T11 | `judging_in_progress` | `judging_completed` | `judging_completed` | F-003 | system | 判定正常完了 |
| T12 | `judging_in_progress` | `judging_failed` | `judging_failed` | F-003 | system | 判定異常終了 |
| T13 | `judging_completed` | `checklist_generating` | `checklist_generating` | F-004 | cascade | verdict=eligible のみ |
| T14 | `checklist_generating` | `checklist_active` | `checklist_generated` | F-004 | system | 生成正常完了 |
| T15 | `checklist_generating` | `judging_completed` | `checklist_generation_failed` | F-004 | system | 生成失敗 → judging_completed に戻る |
| T16 | `checklist_active` | `checklist_completed` | `checklist_completed` | F-004 | system | 全項目 done |

### §3-2. ユーザー操作による遷移（ゲート + オーバーライド）

| # | from | to | event_type | feature | triggered_by | 備考 |
|---|------|----|-----------|---------|-------------|------|
| T20 | `reading_failed` | `reading_queued` | `reading_requeued` | F-002 | user | **G3: 読解失敗リトライ** |
| T21 | `judging_failed` | `judging_queued` | `judging_requeued` | F-003 | user | **G5: 判定失敗リトライ** |
| T22 | `reading_completed` | `reading_queued` | `reading_requeued` | F-002 | user | **G6: 再読解リクエスト** |
| T23 | `judging_completed` | `judging_queued` | `judging_requeued` | F-003 | user | **G7: 再判定リクエスト** |
| T24 | `checklist_active` | `checklist_generating` | `checklist_requeued` | F-004 | user | **G8: チェックリスト再生成** |
| T25 | `skipped` | `under_review` | `case_marked_reviewed` | F-001 | user | **G9: skipped 復帰** |
| T26 | `checklist_completed` | `checklist_active` | `checklist_item_unchecked` | F-004 | user | チェック取消で active に戻る |

### §3-3. オーバーライド遷移（ライフサイクルは変えずメタデータ更新）

| # | ライフサイクルステージ | event_type | feature | 備考 |
|---|----------------------|-----------|---------|------|
| T30 | `judging_completed`（変更なし） | `eligibility_overridden` | F-003 | human_override 設定。verdict=uncertain→eligible の場合は T13 が後続 |

> **注**: T30 は current_lifecycle_stage を変更しない。ただし human_override=eligible の場合、
> cascade で T13（checklist_generating）が後続する。この2つのイベントは同一トランザクション内で発行。

### §3-4. アーカイブ遷移

| # | from | to | event_type | feature | triggered_by | 備考 |
|---|------|----|-----------|---------|-------------|------|
| T40 | 任意（`archived` 以外） | `archived` | `case_archived` | F-001 | system/batch | 期限超過 or ユーザー手動 |

> **アーカイブ制約**: `archived` から他のステージへの遷移は不可。アーカイブは最終状態。

### §3-5. 不正遷移（明示的に禁止）

以下は代表的な不正遷移。§3-1〜§3-4 に記載されていない全遷移が不正。

| from | to | 理由 |
|------|----|------|
| `discovered` | `planned` | `scored` → `under_review` を経由する必要がある |
| `reading_completed` | `planned` | 逆行禁止（再読解は reading_queued 経由） |
| `judging_completed` | `reading_completed` | 逆行禁止（再判定は judging_queued 経由） |
| `archived` | 任意 | アーカイブは最終状態 |
| `checklist_active` | `judging_completed` | 直接の逆行禁止（再判定→再生成のルートを使う） |

---

## §4 テーブル別ステータスマッピング

> `current_lifecycle_stage` と各テーブルの `status` の対応関係。

### §4-1. マッピングテーブル

| current_lifecycle_stage | cases.status | case_cards.status | eligibility.verdict | checklists.status |
|------------------------|-------------|-------------------|--------------------|--------------------|
| `discovered` | `new` | — | — | — |
| `scored` | `new` | — | — | — |
| `under_review` | `reviewed` | — | — | — |
| `planned` | `planned` | — | — | — |
| `skipped` | `skipped` | — | — | — |
| `reading_queued` | `planned` | `pending` | — | — |
| `reading_in_progress` | `planned` | `processing` | — | — |
| `reading_completed` | `planned` | `completed`/`needs_review` | — | — |
| `reading_failed` | `planned` | `failed` | — | — |
| `judging_queued` | `planned` | `completed`/`needs_review` | — | — |
| `judging_in_progress` | `planned` | `completed`/`needs_review` | — | — |
| `judging_completed` | `planned` | `completed`/`needs_review` | `eligible`/`ineligible`/`uncertain` | — |
| `judging_failed` | `planned` | `completed`/`needs_review` | — | — |
| `checklist_generating` | `planned` | `completed`/`needs_review` | `eligible` | `draft` |
| `checklist_active` | `planned` | `completed`/`needs_review` | `eligible` | `active` |
| `checklist_completed` | `planned` | `completed`/`needs_review` | `eligible` | `completed` |
| `archived` | `archived` | （変更なし） | （変更なし） | `archived` |

### §4-2. マッピングルール

| # | ルール | 詳細 |
|---|-------|------|
| 1 | **cases.status は粗粒度** | `new`/`reviewed`/`planned`/`skipped`/`archived` の 5 値のみ。Reading/Judging/Preparation フェーズ中は `planned` のまま |
| 2 | **case_cards.status は独立** | `needs_review` と `completed` はユーザーの確認操作で遷移。ライフサイクルは case_cards.status に依存しない（ただし needs_review の場合はUIで「要確認」バッジ表示） |
| 3 | **verdict は独立** | `eligible`/`ineligible`/`uncertain` はライフサイクルステージに影響しない。ただし `eligible`（or human_override=eligible）のみが checklist_generating へのカスケード条件 |
| 4 | **archived は全テーブルに波及** | `archived` 遷移時に checklists.status も `archived` に更新（他テーブルの status は変更しない） |

---

## §5 再実行の状態ルール

### §5-1. 再読解（F-002）

```
reading_completed ──[user: G6]──→ reading_queued
                                       │
  case_cards: INSERT (version+1, is_current=true)
  旧 case_cards: UPDATE (is_current=false)
  case_events: reading_requeued + reading_started + reading_completed
                                       │
                                       ▼
                              reading_in_progress → reading_completed
                                       │
                              ┌────────┴──────────┐
                              │ cascade: 再判定    │
                              └───────────────────┘
```

**下流への影響**:
- 再読解完了 → 自動で再判定キュー（`judging_queued`）
- 再判定完了 → verdict=eligible なら自動でチェックリスト再生成（`checklist_generating`）
- **全カスケードが完了するまで、中間ステージで停止可能**（failed で止まる）

### §5-2. 再判定（F-003）

```
judging_completed ──[user: G7]──→ judging_queued
                                       │
  eligibility_results: INSERT (version+1, is_current=true)
  旧 eligibility_results: UPDATE (is_current=false)
  case_events: judging_requeued + judging_completed
                                       │
                                       ▼
                              judging_in_progress → judging_completed
                                       │
                              ┌────────┴──────────────────┐
                              │ cascade: チェックリスト再生成 │
                              │ （verdict=eligible の場合）  │
                              └───────────────────────────┘
```

**トリガー条件**:
- ユーザーが明示的に「再判定」を操作（G7）
- company_profile が更新された場合（Phase1: ユーザー操作後に手動で再判定）

### §5-3. チェックリスト再生成（F-004）

```
checklist_active ──[user: G8]──→ checklist_generating
                                       │
  checklists: INSERT (version+1, is_current=true)
  旧 checklists: UPDATE (is_current=false)
  case_events: checklist_requeued + checklist_generated
                                       │
                                       ▼
                              checklist_generating → checklist_active
```

**下流への影響**: なし（チェックリストはパイプラインの末端）

### §5-4. skipped 復帰

```
skipped ──[user: G9]──→ under_review
                              │
  cases.status: skipped → reviewed
  case_events: case_marked_reviewed (from_status=skipped)
  skip_reason はそのまま保持（履歴として）
```

**下流への影響**: なし（under_review でユーザーが再度 planned を選択すれば通常フローに入る）

### §5-5. カスケード中断ルール

| 中断点 | 中断ステージ | ユーザーアクション | 再開方法 |
|-------|-----------|---------------|---------|
| 再読解後 reading_failed | `reading_failed` | G3: 読解失敗リトライ | `reading_queued` → 通常フロー |
| 再判定後 judging_failed | `judging_failed` | G5: 判定失敗リトライ | `judging_queued` → 通常フロー |
| 再生成後 generation_failed | `judging_completed` | G8: チェックリスト再生成 | `checklist_generating` → 通常フロー |
| 再判定後 verdict=ineligible | `judging_completed` | — | チェックリストは生成されない。ユーザーが override で eligible にすれば生成 |

---

## §6 UI 状態定義（React）

### §6-1. グローバル状態構造

> Phase1 は React Context で十分。Phase2 でユーザー数が増えたら Zustand 等に移行検討。

```typescript
// Phase1: Context ベース
interface AppState {
  // 案件一覧
  cases: {
    items: Case[];
    filter: CaseFilter;
    sort: CaseSort;
    loading: boolean;
    error: string | null;
    lastFetchedAt: string | null;   // ISO8601
  };
  // 案件詳細（選択中の案件）
  activeCase: {
    caseId: string | null;
    caseData: Case | null;
    card: CaseCard | null;          // is_current=true
    eligibility: EligibilityResult | null;  // is_current=true
    checklist: Checklist | null;    // is_current=true
    events: CaseEvent[];
    loading: boolean;
    error: string | null;
  };
  // 会社プロフィール
  companyProfile: {
    data: CompanyProfile | null;
    loading: boolean;
  };
  // バッチ状態
  batchStatus: {
    lastRun: BatchLog | null;
    running: boolean;
  };
}
```

### §6-2. 主要データ型

```typescript
interface Case {
  id: string;
  source: string;
  sourceId: string;
  caseName: string;
  issuingOrg: string;
  bidType: string | null;
  category: string | null;
  region: string | null;
  grade: string | null;
  submissionDeadline: string | null;  // ISO8601
  openingDate: string | null;
  status: 'new' | 'reviewed' | 'planned' | 'skipped' | 'archived';
  currentLifecycleStage: LifecycleStage;
  score: number | null;
  scoreDetail: ScoreDetail | null;
  firstSeenAt: string;
  lastUpdatedAt: string;
}

type LifecycleStage =
  | 'discovered' | 'scored' | 'under_review'
  | 'planned' | 'skipped'
  | 'reading_queued' | 'reading_in_progress'
  | 'reading_completed' | 'reading_failed'
  | 'judging_queued' | 'judging_in_progress'
  | 'judging_completed' | 'judging_failed'
  | 'checklist_generating' | 'checklist_active'
  | 'checklist_completed' | 'archived';

type Verdict = 'eligible' | 'ineligible' | 'uncertain';

interface CaseCard {
  id: string;
  caseId: string;
  version: number;
  isCurrent: boolean;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'needs_review';
  eligibility: object;        // JSONB
  schedule: object;
  businessContent: object;
  submissionItems: object;
  riskFactors: object[];
  deadlineAt: string | null;
  businessType: string | null;
  riskLevel: 'low' | 'medium' | 'high' | null;
  extractionMethod: 'text' | 'ocr' | 'text_failed';
  isScanned: boolean;
  assertionCounts: { fact: number; inferred: number; caution: number } | null;
  evidence: object;
  confidenceScore: number | null;
  llmModel: string | null;
  extractedAt: string | null;
  reviewedAt: string | null;
}

interface EligibilityResult {
  id: string;
  caseId: string;
  caseCardId: string;
  version: number;
  isCurrent: boolean;
  verdict: Verdict;
  confidence: number;
  hardFailReasons: HardFailReason[];
  softGaps: SoftGap[];
  checkDetails: object;
  humanOverride: Verdict | null;
  overrideReason: string | null;
  overriddenAt: string | null;
  judgedAt: string;
}

interface Checklist {
  id: string;
  caseId: string;
  version: number;
  isCurrent: boolean;
  status: 'draft' | 'active' | 'completed' | 'archived';
  checklistItems: ChecklistItem[];
  scheduleItems: ScheduleItem[];
  warnings: string[];
  progress: { total: number; done: number; rate: number };
  generatedAt: string;
  completedAt: string | null;
}
```

### §6-3. ページ構成

| # | ページ | パス | 主要コンテンツ |
|---|-------|------|-------------|
| P1 | ダッシュボード | `/` | 案件一覧（ステージフィルタ・スコアソート）、バッチ状態、新着通知 |
| P2 | 案件詳細 | `/cases/:id` | 案件カード + 判定結果 + チェックリスト + イベント履歴 |
| P3 | 価格分析 | `/analytics` | F-005 の落札実績データ・相場分析 |
| P4 | 設定 | `/settings` | 会社プロフィール編集、検索条件設定 |

### §6-4. ダッシュボード（P1）の構成

```
┌──────────────────────────────────────────────────────────┐
│ 入札ラクダAI                              [設定] [更新]  │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  バッチ状態: ✅ 最終実行 2026-03-01 06:00 (成功)        │
│                                                          │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ フィルタ: [全て▼] [Discovery▼] [Reading▼] ...      │ │
│  │ ソート: [スコア順▼] [期限順▼] [新着順▼]            │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌─ 案件カード ───────────────────────────────────────┐  │
│  │ 📦 ○○省 配送業務委託                   スコア: 85  │  │
│  │ [応札予定] 期限: 3/15  ステージ: 読解完了 🟢       │  │
│  │ 判定: eligible ✅  チェック: 3/8 (37%)             │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌─ 案件カード ───────────────────────────────────────┐  │
│  │ 📄 ○○局 事務用品調達                   スコア: 72  │  │
│  │ [応札予定] 期限: 3/20  ステージ: 判定中… 🟡        │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌─ 案件カード ───────────────────────────────────────┐  │
│  │ 🆕 ○○省 軽運送業務                     スコア: 68  │  │
│  │ [新着] 期限: 3/25  ステージ: スコア済 🔵           │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**デフォルトビュー**: 全ステージ一覧。`archived` は非表示（フィルタで表示可能）。スコア降順ソート。

### §6-5. 案件詳細（P2）の構成

```
┌──────────────────────────────────────────────────────────┐
│ ← 戻る   ○○省 配送業務委託                              │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ステージ: [読解完了 🟢] → [判定完了 🟢] → [準備中 🟠] │
│                                                          │
│  ┌─ タブ ────────────────────────────────────────────┐   │
│  │ [概要] [AI読解] [参加可否] [チェックリスト] [履歴] │   │
│  └───────────────────────────────────────────────────┘   │
│                                                          │
│  ── 概要タブ ──                                          │
│  案件名: ○○省 配送業務委託                              │
│  発注機関: ○○省                                         │
│  入札方式: 一般競争入札                                  │
│  カテゴリ: 役務の提供                                    │
│  提出期限: 2026-03-15 17:00                              │
│  スコア: 85 (競争:25 規模:20 余裕:22 適合:18)           │
│                                                          │
│  [応札予定にする] [見送り] [アーカイブ]                  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### §6-6. ポーリング設計（Phase1）

| 対象 | エンドポイント | 間隔 | 条件 |
|------|-------------|------|------|
| 案件一覧 | `GET /api/v1/cases` | 30秒 | ダッシュボード表示中 |
| 案件詳細 | `GET /api/v1/cases/:id` | 5秒 | 進行中ステージ（`*_in_progress`, `*_queued`, `*_generating`）の場合のみ |
| バッチ状態 | `GET /api/v1/batch/latest` | 60秒 | ダッシュボード表示中 |

**ポーリング停止条件**: 安定ステージ（`reading_completed`, `judging_completed`, `checklist_active`, `checklist_completed`, `archived`）では5秒ポーリングを停止し、30秒の一覧ポーリングのみ。

---

## §7 エラー状態の UI 表現

### §7-1. ステージ別エラーハンドリング

| ステージ | UI 表現 | ユーザーアクション |
|---------|---------|---------------|
| `reading_failed` | 🔴 赤バッジ「読解失敗」+ エラー詳細パネル | 「再読解」ボタン（G3） |
| `judging_failed` | 🔴 赤バッジ「判定失敗」+ エラー詳細パネル | 「再判定」ボタン（G5） |
| checklist_generation_failed | 🔴 赤バッジ「生成失敗」（ステージは `judging_completed` に戻る） | 「再生成」ボタン（G8 相当） |

**エラー詳細パネルの内容**:
- エラータイプ（`llm_api_error`, `pdf_parse_error`, `timeout` 等）
- エラーメッセージ
- 発生日時
- リトライ回数
- 「再試行」ボタン

### §7-2. 品質に関する注意表示

| 条件 | UI 表現 | 場所 |
|------|---------|------|
| `case_cards.status = 'needs_review'` | ⚠️ 黄バッジ「要確認」 | 案件カード + AI読解タブ |
| `confidence_score < 0.6` | ⚠️ 信頼度バッジ（赤: <0.4, 黄: 0.4-0.6, 緑: >0.6） | AI読解タブ |
| `assertion_counts.inferred > 0` | 推定 `N` 件（黄テキスト） | AI読解タブの各セクション |
| `assertion_counts.caution > 0` | ⚠️ 注意 `N` 件（赤テキスト） | AI読解タブの各セクション |
| `verdict = 'uncertain'` | ⚠️ 橙バッジ「確認必要」+ オーバーライドパネル | 参加可否タブ |
| `risk_level = 'high'` | 🔴 リスク高バッジ | 案件カード + 概要タブ |
| `is_scanned = true` | ⚠️ 「画像PDF — テキスト抽出に制限あり」 | AI読解タブ |

### §7-3. オーバーライドパネル（verdict=uncertain 時）

```
┌─ 参加可否判定 ─────────────────────────────────────────┐
│                                                        │
│  判定: ⚠️ uncertain（確認必要）                        │
│  信頼度: 0.72                                          │
│                                                        │
│  ── 不確実な理由 ──                                    │
│  • Hard-5: 「その他の参加資格」に記載あり → 確認が必要 │
│  • Soft-1: 同種業務の実績要件 → severity: high         │
│                                                        │
│  ── 判定を上書き ──                                    │
│  [ eligible に変更 ] [ ineligible に変更 ]             │
│  理由: [____________________________]                  │
│                                                        │
│  ⚠️ 上書き後、チェックリストが自動生成されます          │
│                                                        │
└────────────────────────────────────────────────────────┘
```

### §7-4. 空状態の表示

| 画面 | 条件 | 表示 |
|------|------|------|
| ダッシュボード | 案件0件 | 「まだ案件がありません。バッチを実行して案件を収集しましょう。」+ バッチ実行ボタン |
| AI読解タブ | case_card なし | 「この案件はまだ AI 読解されていません。」 |
| 参加可否タブ | eligibility_result なし | 「AI 読解が完了すると、自動で判定が実行されます。」 |
| チェックリストタブ | checklist なし | 「参加可能と判定されると、チェックリストが自動生成されます。」 |
| 履歴タブ | events 0件 | 「イベント履歴はまだありません。」 |

### §7-5. ステージ遷移しないイベントの表示ルール

> case_events にはステージを変えないイベント（checklist_item_checked 等）も記録される。
> これらはユーザーの体感上重要だが、履歴タブが冗長にならないよう表示を制御する。

| イベントカテゴリ | 例 | 履歴タブでの表示 |
|---------------|-----|--------------|
| チェック操作 | `checklist_item_checked`, `checklist_item_unchecked` | デフォルト折りたたみ。「チェック操作 N件」としてグルーピング。展開で個別表示 |
| 読解確認 | `reading_reviewed` | 通常表示（ステージは変わらないが重要イベント） |
| 判定オーバーライド | `eligibility_overridden`（T30: ステージは `judging_completed` のまま） | 通常表示 + 強調（verdict 変更の監査証跡） |

**フィルタオプション**（履歴タブ上部）:

| フィルタ | 表示対象 |
|---------|---------|
| 全て | 全イベント（チェック操作は折りたたみ） |
| ステージ変更のみ | `from_status != to_status` のイベントのみ |
| ユーザー操作のみ | `triggered_by = 'user'` のイベントのみ |

---

## §8 状態遷移図（ASCII）

### §8-1. 全体フロー

```
                        ┌─────────────────────────────────────────────────────────┐
                        │              Discovery                                   │
                        │                                                         │
  バッチ取得 ─────────▶ │ discovered ──▶ scored ──▶ under_review ──┬──▶ planned   │
                        │                              │           │              │
                        │                              │           └──▶ skipped   │
                        │                              │                  │        │
                        │                              │         G9: 復帰 │        │
                        │                              ◀──────────────────┘        │
                        └──────────────────────────────┬──────────────────────────┘
                                                       │ G1: 応札意思決定
                                                       │ (cascade)
                        ┌──────────────────────────────▼──────────────────────────┐
                        │              Reading                                     │
                        │                                                         │
                        │ reading_queued ──▶ reading_in_progress ──┬──▶ reading_  │
                        │      ▲                                   │    completed │
                        │      │ G3/G6: リトライ/再読解            │              │
                        │      └───────────────── reading_failed ◀─┘              │
                        └──────────────────────────────┬──────────────────────────┘
                                                       │ cascade
                        ┌──────────────────────────────▼──────────────────────────┐
                        │              Judging                                     │
                        │                                                         │
                        │ judging_queued ──▶ judging_in_progress ──┬──▶ judging_  │
                        │      ▲                                   │    completed │
                        │      │ G5/G7: リトライ/再判定            │      │       │
                        │      └───────────────── judging_failed ◀─┘      │       │
                        │                                            T30: override│
                        └──────────────────────────────┬──────────────────────────┘
                                                       │ cascade (eligible のみ)
                        ┌──────────────────────────────▼──────────────────────────┐
                        │              Preparation                                 │
                        │                                                         │
                        │ checklist_generating ──▶ checklist_active ──▶ checklist_│
                        │      ▲                        │              completed  │
                        │      │ G8: 再生成             │                  │       │
                        │      └────────────────────────┘   T26: uncheck ──┘       │
                        └─────────────────────────────────────────────────────────┘

                        ┌─────────────────────────────────────────────────────────┐
                        │  archived  ◀── T40: 任意ステージから（期限超過 / 手動）  │
                        └─────────────────────────────────────────────────────────┘
```

---

## [要確認] 一覧

| # | 項目 | 影響範囲 | 解消予定 |
|---|------|---------|---------|
| — | （なし — 全項目はプランファイルで事前解消済み） | — | — |

> **参考（プランで解消済み）**:
> - skipped 復帰可否 → 可能（SSOT-4 v2 で明記、本ドキュメント G9 で定義）
> - reading_in_progress タイムアウト → SSOT-5 §8 で定義予定
> - ダッシュボードデフォルトビュー → 全ステージ一覧（§6-4 で定義）

---

## 変更履歴

| 日付 | 変更内容 | 変更者 |
|------|---------|-------|
| 2026-02-18 | 初版作成（17ステージ、状態遷移テーブル40件、テーブル別マッピング、再実行ルール、UI定義） | Claude / 金子 |
| 2026-02-18 | v2: §1原則8(UI表示優先順位)、§2-2(UI制約列)、§2-4(相反操作排他ルール+楽観ロック)、§7-5(ステージ遷移しないイベント表示ルール)を追加 | Claude / 金子 |
