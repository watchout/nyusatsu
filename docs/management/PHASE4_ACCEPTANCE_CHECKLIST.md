# Phase 4 受け入れチェックリスト

> Phase 4: F-002 AI読解 / F-003 参加可否判定 / F-004 チェックリスト生成 / Cascade統合
> 完了日: 2026-02-24
> テスト: 437 passed, 0 failures (Phase 3: 233 → +204)
> タグ: `v0.1-phase4-complete`

---

## F-002 AI読解パイプライン (95テスト: Wave 0-3)

### 文書取得 + テキスト抽出 (Stage 1)
- [x] HTML公告テキスト抽出（simple / complex / missing fields）
- [x] PDFテキスト抽出（テーブル / 役務系 / 見積もり要求）
- [x] スキャンPDF検出（低文字数 / 高記号率 → is_scanned=true）
- [x] SHA-256ファイルハッシュ（重複検出用）

### LLM構造化抽出 (Stage 2)
- [x] 5カテゴリ抽出: eligibility, schedule, business_content, submission_items, risk_factors
- [x] assertion_type 付与: fact / inferred / caution
- [x] 長文チャンク分割（>5000トークン → セクション単位分割 → マージ）
- [x] MockProvider / ClaudeProvider 切替（LLM_PROVIDER env var）
- [x] 不正JSON → リトライ、不明assertion_type → "inferred"フォールバック

### 根拠マッピング + 品質チェック (Stage 3)
- [x] 非対称バイグラム類似度による根拠照合（≥0.8 → high, ≥0.65 → candidate）
- [x] evidence_dict 構造: PDF(page/section/quote) / HTML(selector/heading_path/quote)
- [x] confidence_score 算出 + assertion_counts 集計
- [x] risk_level 判定 (high / medium / low)

### ReadingBatch
- [x] reading_queued → reading_in_progress → reading_completed 遷移
- [x] 失敗時 → reading_failed + event記録
- [x] VersionManager によるバージョン管理（initial / rotate）

### 評価指標基盤
- [x] ReadingMetrics: recall_fields, evidence_rate, uncertain_rate, processing_time_ms

---

## F-003 参加可否判定エンジン (52テスト: Wave 4)

### 4フェーズ判定
- [x] Phase 1: 前提条件（profile不完全 / confidence<0.6 → uncertain）
- [x] Phase 2: Hard 5条件
  - H1: 入札資格 (qualification)
  - H2: 等級 (grade) — 16組合せ全通過
  - H3: 品目 (category) — "その他"ワイルドカード対応
  - H4: 地域 (region)
  - H5: 許認可 (license) — inferred → uncertain
- [x] Phase 3: Soft 4条件
  - S1: 実績 (experience) — severity = assertion_type連動
  - S2: 認証 (certifications)
  - S3: 所在地 (location)
  - S4: 人員 (personnel)
- [x] Phase 4: 最終verdict + confidence計算

### 3値判定
- [x] eligible: hard全pass + soft gapなし or 軽微
- [x] ineligible: hard fail 1件以上 → confidence 0.90
- [x] uncertain: hard uncertain or soft high gap → confidence 0.50-0.55

### JudgmentService + Batch
- [x] CompanyProfile読込 → JudgmentEngine → EligibilityResult保存
- [x] seed data干渉回避（テスト時 delete(CompanyProfile)パターン）
- [x] VersionManager keyword-only引数 (case_id=...)
- [x] judging_queued → judging_completed / judging_failed 遷移

---

## F-004 チェックリスト生成 (31テスト: Wave 5)

### ChecklistBuilder
- [x] submission_items → bid_time / performance_time 分類
- [x] 固定項目自動追加（封筒 / 配送方法）
- [x] 見積もり要求 → 最優先配置
- [x] inferred項目 → "（推定）"ラベル付与
- [x] uncertain/gap → 確認タスク自動挿入
- [x] 警告生成: risk_factors / soft_gaps / assertion_counts

### ScheduleCalculator
- [x] 4段階逆算: 準備開始(-5BD) / 書類レビュー(-2BD) / 最終確認(-1BD) / 提出期限(0BD)
- [x] 見積もり期限がある場合の追加ステージ
- [x] jpholiday による祝日スキップ
- [x] 週末スキップ（土日）

### ChecklistService + Batch
- [x] トリガーチェック: verdict=eligible or human_override=eligible
- [x] ineligible / uncertain → チェックリスト生成スキップ
- [x] progress計算: {total, done, rate}
- [x] 失敗時フォールバック: checklist_generating → judging_completed (T15)

---

## Cascade統合 (15テスト: Wave 6)

### CascadePipeline
- [x] 3段階自動遷移: reading → judgment → checklist
- [x] eligible → 全3段階完走
- [x] ineligible / uncertain → checklist スキップ
- [x] 各段階失敗 → abort + safe_transition

### CascadeBatch
- [x] Circuit breaker: 3連続失敗 → 残り案件SKIPPED
- [x] 成功時リセット
- [x] 排他ロック (BatchAlreadyRunningError)

---

## API エンドポイント (17テスト: Wave 7)

### F-002 CaseCard API
- [x] `GET /api/v1/cases/{id}/card` — current取得, 404
- [x] `GET /api/v1/cases/{id}/cards` — 全versions, 空リスト

### F-003 Eligibility API
- [x] `GET /api/v1/cases/{id}/eligibility` — current取得, 404
- [x] `GET /api/v1/cases/{id}/eligibilities` — 全versions

### F-004 Checklist API
- [x] `GET /api/v1/cases/{id}/checklist` — current取得, 404
- [x] `GET /api/v1/cases/{id}/checklists` — 全versions
- [x] `PATCH /api/v1/checklists/{id}/items/{index}` — check/uncheck toggle + progress再計算
- [x] `POST /api/v1/checklists/{id}/items` — 手動追加 (source=manual)

### Batch Trigger API
- [x] `POST /api/v1/batch/trigger` — cascade手動実行 (200 success)
- [x] already running → 409 BATCH_ALREADY_RUNNING

### ライブサーバー検証
- [x] 全エンドポイント正常応答確認
- [x] エラーレスポンス envelope形式 ({data, error, meta})
- [x] サーバーログ: 0 errors

---

## テスト統計

| 区分 | テスト数 |
|------|---------|
| Phase 1-3 (既存) | 233 |
| Wave 0: Pre-flight | +12 |
| Wave 1: F-002 Stage1 | +20 |
| Wave 2: F-002 Stage2 | +24 |
| Wave 3: F-002 Stage3 | +29 |
| Wave 4: F-003 判定 | +52 |
| Wave 5: F-004 チェックリスト | +31 |
| Wave 6: Cascade統合 | +15 |
| Wave 7: API endpoints | +17 |
| **合計** | **437** |

---

## Git履歴について

本リポジトリは Phase 4 完了時点で `git init` を行ったため、Phase 1-3 と Phase 4 の境界がコミット履歴上は分離されていない。
Phase間のトレーサビリティは以下の文書で担保する:

- `docs/management/IMPLEMENTATION_PLAN_P0.md` — Phase/Wave 実装計画
- 本ファイル — Phase 4 受け入れ基準と検証結果
- `v0.1-phase4-complete` タグ — この時点のスナップショット
