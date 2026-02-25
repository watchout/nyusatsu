# SSOT-5: 横断的関心事（Cross-Cutting Concerns）

> **バージョン**: v1.1
> **最終更新**: 2026-02-18
> **ステータス**: Draft
> **依存先**: SSOT-2（UI/状態遷移）, SSOT-3（API規約）, SSOT-4（データモデル）
> **参照元**: F-001〜F-005 全機能仕様書

---

## 変更履歴

| バージョン | 日付 | 変更内容 |
|-----------|------|---------|
| v1.0 | 2026-02-18 | 初版（12セクション） |
| v1.1 | 2026-02-18 | [要確認] 8件の暫定決定 + SLO分類明示 + raw参照キー追加 + LLMサーキットブレーカ/コスト制御/致命アラート新設 |

---

## 目次

- [§1 設計原則](#1-設計原則)
- [§2 バッチ実行ワークフロー](#2-バッチ実行ワークフロー)
- [§3 再実行リトライワークフロー](#3-再実行リトライワークフロー)
- [§4 エラーハンドリングパターン](#4-エラーハンドリングパターン)
- [§5 冪等性設計（Phase1→Phase2）](#5-冪等性設計phase1phase2)
- [§6 監査トレイル（Audit Spine）](#6-監査トレイルaudit-spine)
- [§7 復旧手順（Recovery Runbook）](#7-復旧手順recovery-runbook)
- [§8 KPIメトリクス観測性](#8-kpiメトリクス観測性)
- [§9 セキュリティ権限](#9-セキュリティ権限)
- [§10 データ保持原文保存ポリシー](#10-データ保持原文保存ポリシー)
- [§11 ログ設計](#11-ログ設計)
- [§12 インフラライブラリ定数](#12-インフラライブラリ定数)

---

## §1 設計原則

横断的関心事の全体を貫く10原則。各セクションの判断基準として参照する。

| # | 原則 | 説明 | 根拠 |
|---|------|------|------|
| 1 | **部分失敗を許容する** | バッチ処理・パイプラインは個別案件の失敗で全体を止めない。失敗件数を記録し、成功分は確定する | F-001/F-005 のバッチ設計、batch_logs.status = `partial` |
| 2 | **再実行は新 version を作る** | case_cards / eligibility_results / checklists の再実行は旧版を保持し、新版（version+1, is_current=true）を生成する。上書き禁止 | SSOT-4 §6 再実行データモデル |
| 3 | **case_events が監査スパイン** | 全ての状態遷移・ユーザー操作・システムイベントを case_events に記録する。各テーブルの status は非正規化キャッシュ | SSOT-4 §1-6, §3-9 |
| 4 | **原文再現性を保証する** | 取得した公告HTML・仕様書PDF・OD CSVの原本を保存し、いつでも再読解・再分析可能にする | F-001 原本保存、F-002 SHA-256 キャッシュ、F-005 raw_data |
| 5 | **uncertain は一級市民** | 判定不能・データ不足は `uncertain` として正式に扱う。推測で eligible/ineligible に振らない | F-003 設計思想、SSOT-3 §2-7 warnings |
| 6 | **Phase1 は最小限の認証** | シングルユーザー前提で認証を省略し、危険操作のみ制限する。Phase2 で JWT + RBAC を導入する接合点を文書化 | SSOT-3 §1 原則3、§8 Phase2 拡張 |
| 7 | **冪等性は段階的に導入** | Phase1 は楽観ロック（expected_*）+ 同値再送OK。Phase2 で Idempotency-Key を必須化 | SSOT-3 §6 |
| 8 | **ログは構造化 JSON** | 全ログを構造化 JSON で出力し、case_id + feature_origin をキーに横断検索可能にする | MONITORING.md 準拠 |
| 9 | **営業日は jpholiday で計算** | 日本の祝日・振替休日・年末年始を考慮した営業日計算を共通関数化する | F-004 逆算スケジュール |
| 10 | **タイムアウトで自動復旧** | *_in_progress 状態が一定時間経過したら自動で failed に遷移させ、リトライ可能にする | SSOT-2 §8 参照先（本ドキュメント §3, §7 で定義） |
| 11 | **LLM Provider 抽象化レイヤ必須** | LLM API 呼び出しは抽象レイヤ経由で行い、Provider を差し替え可能にする。Phase1 は Claude API、価格・障害時に他 Provider へ切り替え可能 | コスト最適化・障害耐性 |

---

## §2 バッチ実行ワークフロー

### §2-1 バッチ種別

| # | batch_type | feature_origin | 実行タイミング | 処理内容 | 対象テーブル |
|---|-----------|---------------|-------------|---------|------------|
| 1 | `case_fetch` | F-001 | 日次（早朝） | データソース巡回 → 案件取得 → 正規化 → 格納 → スコアリング | cases |
| 2 | `od_import` | F-005 | 日次 | 調達ポータルOD(CSV) → ダウンロード → パース → 格納 | base_bids |
| 3 | `detail_scrape` | F-005 | 日次（od_import 後） | 対象領域の落札公告詳細ページ → スクレイピング → 補完データ格納 | bid_details |
| 4 | `cascade_pipeline` | F-002→F-003→F-004 | case_fetch 後 / 手動 | 新着・更新案件に対して AI読解→判定→チェックリスト生成を連鎖実行 | case_cards, eligibility_results, checklists |

### §2-2 バッチ実行フロー

```
[cron / 手動トリガー]
  │
  ├─ batch_logs INSERT (status='running')
  │
  ├─ 個別処理ループ
  │   ├─ 成功 → カウント加算
  │   ├─ 失敗 → error_details に追記、次の件へ継続（原則1）
  │   └─ スキップ → unchanged_count 加算
  │
  ├─ 全件完了
  │   ├─ error_count == 0 → status='success'
  │   ├─ error_count > 0 && success_count > 0 → status='partial'
  │   └─ error_count == total → status='failed'
  │
  └─ batch_logs UPDATE (status, counts, finished_at)
```

### §2-3 バッチ間の依存と実行順序

```
06:00  od_import (F-005)          ← 独立実行
06:30  case_fetch (F-001)         ← od_import 完了後（スコアリングに base_bids を参照）
07:00  detail_scrape (F-005)      ← od_import の新規レコードを対象
07:30  cascade_pipeline (F-002→)  ← case_fetch で planned になった案件を対象
```

> **制約**: 同一 `batch_type` のバッチは同時に1つだけ実行可能（SSOT-3 §7 `BATCH_ALREADY_RUNNING`）。
> 異なる batch_type は並行実行可能（例: od_import と detail_scrape は独立）。

### §2-4 cascade_pipeline の詳細

cascade_pipeline は case_fetch で `planned` ステージになった案件（または手動で planned にした案件）を対象に、以下を順次実行する:

```
対象案件ごとに:
  1. reading_queued → reading_started → reading_completed / reading_failed
     ├─ failed → 次の案件へ（この案件の後続はスキップ）
     └─ completed → 2へ
  2. judging_queued → judging_completed / judging_failed
     ├─ failed → 次の案件へ
     ├─ ineligible → 次の案件へ（チェックリスト不要）
     ├─ uncertain → 次の案件へ（人間確認待ち）
     └─ eligible → 3へ
  3. checklist_generating → checklist_active / checklist_generation_failed
     └─ 完了（成功/失敗問わず）→ 次の案件へ
```

> Phase1 は案件を**逐次処理**（1件ずつ）。Phase2 で並行処理を検討。

### §2-5 部分失敗（partial）の定義

| 条件 | batch_logs.status | アクション |
|------|------------------|----------|
| 全件成功 | `success` | 正常完了ログ |
| 1件以上成功 + 1件以上失敗 | `partial` | 警告ログ + error_details に失敗詳細 |
| 全件失敗 | `failed` | エラーログ + アラート（§4 参照） |
| 0件対象（処理なし） | `success` | 正常完了ログ（total_fetched=0） |

---

## §3 再実行/リトライワークフロー

### §3-1 用語定義

| 用語 | 意味 | トリガー |
|------|------|---------|
| **リトライ（retry）** | 失敗した処理の再試行 | `*_failed` ステージからの復帰（G3, G5） |
| **再実行（re-run）** | 完了済み処理の再実行（新 version 生成） | `*_completed` / `*_active` ステージからの差し戻し（G6, G7, G8） |
| **自動リトライ** | パイプライン内のHTTP/LLM呼び出しの自動再試行 | tenacity による関数レベルの再試行 |

### §3-2 scope の横断定義

SSOT-3 §4-2 の retry エンドポイントで指定する `scope` パラメータの詳細挙動:

| scope | 動作 | 対象データ | 使用シーン |
|-------|------|----------|----------|
| `soft`（デフォルト） | キャッシュ再利用。変更がなければ既存データを流用 | F-002: SHA-256 が同一の PDF/HTML → LLM 呼び出しスキップ、前回の case_card をコピー。F-003: 同一 case_card + 同一 company_profile → 前回の verdict をコピー。F-004: 同一 eligibility_result → 前回のチェックリストをコピー | LLM障害後のリトライ、一時的エラーの復帰 |
| `force` | 全ステップを強制再実行。キャッシュを無視 | F-002: PDF/HTML を再取得し、LLM に再投入。F-003: 全条件を再評価。F-004: チェックリストを一から再生成 | 仕様書更新時、プロンプト改善後、company_profile 変更後 |

**soft の判定ロジック（F-002 の例）**:

```python
# SHA-256 でキャッシュヒット判定
current_hash = sha256(downloaded_pdf_bytes)
previous_card = get_current_card(case_id)

if scope == "soft" and previous_card and previous_card.file_hash == current_hash:
    # キャッシュヒット: 前回結果をコピーして新 version を作成
    new_card = copy_with_new_version(previous_card)
    emit_event("reading_completed", payload={"cache_hit": True})
else:
    # キャッシュミス or force: 全ステップ実行
    new_card = run_full_pipeline(case_id)
    emit_event("reading_completed", payload={"cache_hit": False})
```

### §3-3 カスケード再実行

再実行は上流から下流へカスケードする:

```
再読解（F-002）
  └─ 自動で再判定（F-003）をトリガー
       └─ verdict=eligible なら自動でチェックリスト再生成（F-004）をトリガー

再判定（F-003）
  └─ verdict=eligible なら自動でチェックリスト再生成（F-004）をトリガー

チェックリスト再生成（F-004）
  └─ カスケードなし（終端）
```

**カスケード中断条件**:
- パイプラインのいずれかのステップが `*_failed` → 中断（ユーザーがリトライで復帰）
- F-003 の verdict が `ineligible` → チェックリスト生成をスキップ
- F-003 の verdict が `uncertain` → チェックリスト生成をスキップ（人間確認待ち）

### §3-4 自動リトライ（関数レベル）の上限とバックオフ

| 対象 | ライブラリ | 最大回数 | バックオフ | タイムアウト/回 |
|------|----------|---------|----------|-------------|
| HTTP リクエスト（F-001, F-005 スクレイピング） | tenacity | 3回 | 指数: 30s → 60s → 120s | 30s |
| LLM API 呼び出し（F-002） | tenacity | 2回 | 指数: 10s → 30s | 60s |
| LLM レスポンス JSON パース（F-002） | 独自 | 1回 | 即時（プロンプト微調整して再送） | — |
| DB 接続（全機能共通） | tenacity | 3回 | 指数: 1s → 2s → 4s | 10s |
| PDF ダウンロード（F-002） | tenacity | 3回 | 指数: 30s → 60s → 120s | 60s |

### §3-4a LLM サーキットブレーカ

同一 batch/cascade 内で LLM API 呼び出しが連続して失敗した場合、以降の案件をスキップして無駄なリトライを防止する。

| 項目 | 値 |
|------|-----|
| 発動条件 | 同一 batch/cascade 内で連続 3件の `llm_api_error`（`LLM_CIRCUIT_BREAKER_THRESHOLD`） |
| degraded mode の挙動 | 以降の案件は `reading_failed`（error_type: `llm_circuit_open`）で即失敗。LLM API を呼び出さない |
| 復旧 | 次回バッチで自動リセット。手動リトライは常に可能（サーキットブレーカの対象外） |
| case_event 記録 | reading_failed: `{"error_type": "llm_circuit_open", "consecutive_failures": 3}` |

> **設計判断**: cascade_pipeline 内の F-002 は LLM 依存。LLM がダウンしている状態で全案件を順番に試行するのは無駄（タイムアウト × 案件数 の時間を消費）。3件連続失敗で打ち切り、LLM 復旧後に一括リトライする方が効率的。

### §3-5 *_in_progress スタック検出

パイプラインが `*_in_progress` のまま停止した場合の自動復旧:

| ステージ | タイムアウト | 復旧アクション |
|---------|-----------|-------------|
| `reading_in_progress` | 5分（is_scanned=true の場合は 10分） | → `reading_failed` + case_event 記録（error_type: `timeout`） |
| `judging_in_progress` | 2分 | → `judging_failed` + case_event 記録（error_type: `timeout`） |
| `checklist_generating` | 1分 | → `checklist_generation_failed` + case_event 記録（error_type: `timeout`） |

**検出方法（Phase1）**:
- バッチ開始時に `*_in_progress` ステージの案件を走査
- `case_events` の最新イベントの `created_at` がタイムアウト閾値を超過 → 自動 failed 遷移
- case_event の `triggered_by` = `"system"`, `actor_id` = `"system"`, payload に `{"recovery": "timeout", "stuck_since": "ISO8601"}`

**Phase2 検討**: ハートビート方式（処理中に定期的に case_events に progress イベントを書く。ハートビートが途絶えたらスタックと判定）

### §3-6 リトライ/再実行の上限

| 対象 | 上限 | 超過時の挙動 |
|------|------|------------|
| ユーザーによるリトライ（G3, G5） | **制限なし** | ユーザー判断で何度でもリトライ可能 |
| ユーザーによる再実行（G6, G7, G8） | **制限なし** | ユーザー判断で何度でも再実行可能（version が増加） |
| バッチ内の案件レベルリトライ | **0回**（バッチ内ではリトライしない） | 失敗は記録して次の案件へ。ユーザーが後で個別リトライ |
| 自動リトライ（関数レベル、§3-4） | 上記テーブル参照 | 最終失敗 → `*_failed` ステージへ遷移 |

---

## §4 エラーハンドリングパターン

### §4-1 機能別エラーマトリクス

| 機能 | エラーシナリオ | HTTP/ステータス | UI表示 | case_event |
|------|-------------|---------------|--------|-----------|
| **F-001** | データソース取得失敗 | — (バッチ内) | バッチログに表示 | — (batch_logs.error_details) |
| F-001 | HTML パースエラー | — (バッチ内) | 案件スキップ通知 | — (batch_logs.error_details) |
| F-001 | DB 格納エラー | — (バッチ内) | バッチ失敗アラート | — (batch_logs) |
| F-001 | スコアリングエラー（F-005 データ不在） | — (バッチ内) | デフォルトスコア適用 | case_scored (payload に `{"default_score": true}`) |
| **F-002** | 公告HTML取得失敗 | — (パイプライン内) | `reading_failed` 表示 | reading_failed (error_type: `fetch_error`) |
| F-002 | 仕様書PDF取得失敗 | — (パイプライン内) | `reading_failed` 表示 | reading_failed (error_type: `pdf_fetch_error`) |
| F-002 | スキャンPDF検出 | — (パイプライン内) | `reading_failed` + 理由表示 | reading_failed (error_type: `scanned_pdf`) |
| F-002 | LLM API エラー | — (パイプライン内) | `reading_failed` + リトライボタン | reading_failed (error_type: `llm_api_error`) |
| F-002 | LLM レスポンス パースエラー | — (パイプライン内) | `reading_failed` 表示 | reading_failed (error_type: `llm_parse_error`) |
| F-002 | 低信頼度（confidence < 0.6） | 200 + warnings | `needs_review` バッジ | reading_completed (payload に confidence_score) |
| F-002 | 根拠欠落（EVIDENCE_MISSING） | 200 + warnings | `needs_review` バッジ + 対象フィールド強調 | reading_completed (payload に warnings) |
| **F-003** | case_card 未存在 | — (パイプライン内) | スキップ（ログ表示） | — |
| F-003 | eligibility データ NULL | — (パイプライン内) | `uncertain` 表示 | judging_completed (verdict: uncertain, reason: no_eligibility_data) |
| F-003 | 低信頼度 case_card | — (パイプライン内) | `uncertain` 表示 | judging_completed (verdict: uncertain, reason: low_extraction_confidence) |
| F-003 | company_profile 未設定 | — (パイプライン内) | `uncertain` 表示 | judging_completed (verdict: uncertain, reason: company_profile_incomplete) |
| **F-004** | submission_items NULL | — (パイプライン内) | スケジュールのみ表示 | checklist_generated (payload に `{"skeleton": true}`) |
| F-004 | deadline_at NULL | — (パイプライン内) | 日程なしリスト表示 | checklist_generated (payload に `{"no_schedule": true}`) |
| F-004 | deadline_at 過去日 | — (パイプライン内) | 警告「提出期限超過」 | checklist_generated (payload に `{"past_deadline": true}`) + status=archived |
| **F-005** | OD 取得失敗 | — (バッチ内) | バッチログに表示 | — (batch_logs.error_details) |
| F-005 | CSV パースエラー（行レベル） | — (バッチ内) | スキップ行数表示 | — (batch_logs.error_details) |
| **共通** | DB 接続エラー | 500 INTERNAL_ERROR | エラー画面 | — (アプリケーションログ) |
| 共通 | 不正な状態遷移 | 409 INVALID_TRANSITION | 再読み込み促進 | — (リクエスト拒否) |
| 共通 | 楽観ロック不一致 | 409 STAGE_MISMATCH | 画面更新 + 操作やり直し | — (リクエスト拒否) |
| 共通 | パイプライン実行中 | 409 PIPELINE_IN_PROGRESS | ボタン disabled | — (リクエスト拒否) |
| 共通 | バリデーションエラー | 422 VALIDATION_ERROR | フォームエラー表示 | — (リクエスト拒否) |

### §4-2 HTTP ステータスコードと UI 表示ルール

| HTTP | エラーコード | UI 表示 | ユーザーアクション |
|------|-----------|--------|----------------|
| 200 + warnings | EVIDENCE_MISSING 等 | `needs_review` バッジ + 対象フィールド強調 | 原文確認 → 手動修正 or 承認 |
| 400 | — | 「リクエストが不正です」 | 画面再読み込み |
| 404 | NOT_FOUND / *_NOT_FOUND | 「データが見つかりません」 | 一覧へ戻る |
| 409 | STAGE_MISMATCH | 「他の操作により状態が変わりました」+ 自動再取得 | 画面更新後に操作やり直し |
| 409 | INVALID_TRANSITION | 「この操作は現在の状態では実行できません」 | 画面再読み込み |
| 409 | PIPELINE_IN_PROGRESS | 「処理中です。完了までお待ちください」 | 待機（ボタン disabled） |
| 409 | BATCH_ALREADY_RUNNING | 「バッチが実行中です」 | 待機 |
| 409 | CHECKLIST_VERSION_MISMATCH | 「チェックリストが更新されました」+ 自動再取得 | 再読み込み後に操作やり直し |
| 422 | VALIDATION_ERROR | フィールドごとのエラーメッセージ | 入力修正 |
| 422 | OVERRIDE_REASON_REQUIRED | 「理由を入力してください」 | 理由入力 |
| 422 | SKIP_REASON_REQUIRED | 「見送り理由を入力してください」 | 理由入力 |
| 500 | INTERNAL_ERROR | 「サーバーエラーが発生しました。しばらくしてから再試行してください」 | 時間を置いて再試行 |

### §4-3 warning 系イベントの方針

200 OK で返却される warnings（SSOT-3 §2-7）は、以下のルールで case_events に記録する:

| warning コード | case_event への記録 | 方法 |
|---------------|-------------------|------|
| `EVIDENCE_MISSING` | `reading_completed` イベントの payload 内 | `payload.warnings: [{"code": "EVIDENCE_MISSING", "affected_fields": [...]}]` |
| （Phase2 追加分） | 同様に該当 completed イベントの payload 内 | 同上パターン |

> **方針**: warning は独立イベントとしては記録しない。対応する completed イベントの payload に含めることで、
> 1イベント = 1状態遷移の原則を維持する。

### §4-4 アラート方針（Phase1）

| 対象 | 条件 | Phase1 アクション | Phase2 拡張 |
|------|------|-----------------|------------|
| バッチ全件失敗 | batch_logs.status = `failed` | ログ出力（ERROR） | Slack + PagerDuty |
| LLM API 連続失敗 | 同一バッチ内で3件連続 reading_failed | ログ出力（ERROR） | Slack 通知 + バッチ中断 |
| 高 uncertain 率 | 直近バッチの uncertain 率 > 50% | ログ出力（WARN） | Slack 通知 |
| *_in_progress スタック | §3-5 のタイムアウト超過 | 自動 failed 遷移 + ログ出力 | Slack 通知 |
| LLM サーキットブレーカ発動 | §3-4a の連続失敗閾値超過 | ログ出力（ERROR） | Slack 通知 |

### §4-4a Phase1 致命アラート（気づけない問題への対策）

Phase1 はログ出力のみだが、「気づけない」ことが最大リスク。以下の致命度の高い失敗は、定期チェックスクリプトで検出する。

| 致命度 | 対象 | 検出方法 |
|-------|------|---------|
| **高** | cascade_pipeline 全件失敗 | batch_logs.status = `failed` AND feature_origin IN ('F-002','F-003','F-004') |
| **高** | raw ドキュメント保存失敗（ファイルシステムエラー） | ログ ERROR + ファイル存在チェック |
| **高** | LLM サーキットブレーカ発動 | case_events に `llm_circuit_open` が存在 |
| **中** | 24時間以上バッチ未実行 | batch_logs の最終 started_at が24時間以上前 |
| **中** | スタック案件が3件以上同時に存在 | cases の *_in_progress 状態の案件数 |

**Phase1 対策**: 定期チェックスクリプト `python -m app.scripts.health_check` を日次で実行（cron）。致命度「高」の検出時は標準エラー出力に赤字で警告。

**Phase2 拡張**: Slack webhook（致命度「高」→ 即時通知）、PagerDuty（営業時間外の緊急対応）。

---

## §5 冪等性設計（Phase1→Phase2）

### §5-1 Phase1: 擬似ロック + 同値再送OK

| 操作カテゴリ | 冪等性保証方式 | 詳細 |
|------------|-------------|------|
| **状態遷移（アクション系 POST）** | `expected_lifecycle_stage` 楽観ロック | リクエストに現在のステージを含める。サーバー側で不一致なら 409。同一遷移の再送は *_queued 状態チェックで 200 OK を返す |
| **チェック操作（PATCH）** | 同値再送 OK | 同じ status を再送 → 200 OK（変更なし、イベント記録なし）。異なる status → 更新 + イベント記録 |
| **チェックリスト更新（PATCH）** | `expected_checklist_version` | 任意指定。指定時は version 不一致で 409 |
| **オーバーライド（POST）** | `expected_lifecycle_stage` + ステージチェック | judging_completed かつ verdict=uncertain のみ許可。それ以外は 409 |
| **バッチトリガー（POST）** | 同一 batch_type 排他 | 同じ batch_type が running なら 409 `BATCH_ALREADY_RUNNING` |

**重複リクエスト検出（リトライ/再実行）**:
- retry-reading を送信 → `reading_queued` に遷移
- 同じ retry-reading を再送 → 既に `reading_queued` なら 200 OK（重複イベント記録なし）
- `reading_in_progress` 以降なら 409 `PIPELINE_IN_PROGRESS`

### §5-2 Phase2: Idempotency-Key 必須化

| 項目 | Phase1 | Phase2 |
|------|--------|--------|
| Idempotency-Key ヘッダー | 受理するが検証しない（ログ記録のみ） | POST 系で必須（未指定 → 422） |
| キー保存先 | — | Redis（TTL: 24時間） |
| キー形式 | — | UUID v4 推奨 |
| キー衝突時の挙動 | — | 前回のレスポンスを返却（再計算しない） |
| 保存期間 | — | 24時間（TTL 経過後は新規リクエスト扱い） |
| 対象エンドポイント | — | 全 POST /actions/* + POST /batch/trigger + POST /checklists/*/items |

### §5-3 楽観ロック詳細

```
[クライアント]                          [サーバー]
  │                                      │
  │  POST /cases/:id/actions/mark-planned │
  │  { expected_lifecycle_stage:          │
  │    "under_review" }                   │
  │ ────────────────────────────────────> │
  │                                      │ cases.current_lifecycle_stage を確認
  │                                      │ ├─ 一致 → 遷移実行 → 200 OK
  │                                      │ └─ 不一致 → 409 STAGE_MISMATCH
  │ <──────────────────────────────────── │
  │                                      │
  │  409 の場合:                          │
  │  GET /cases/:id で再取得              │
  │  → UI更新 → ユーザーが操作やり直し     │
```

---

## §6 監査トレイル（Audit Spine）

### §6-1 case_events 必須 payload キー（event_type 別）

SSOT-4 §3-9b の整合性ガードを参照し、全 event_type の payload 構造を定義する。

#### 全イベント共通

case_events のカラム（event_type, from_status, to_status, triggered_by, actor_id, feature_origin, created_at）が必須。payload は event_type 固有のデータのみ。

#### F-001 イベント

| event_type | 必須 payload キー | 説明 |
|-----------|-----------------|------|
| `case_discovered` | `source`, `source_id` | データソース名、ソース側ID |
| `case_updated` | `updated_fields[]` | 更新されたフィールド名の配列 |
| `case_scored` | `score`, `score_breakdown`, `default_score?` | スコア値、内訳、デフォルト使用フラグ |
| `case_marked_planned` | `reason?` | ユーザー入力の理由（任意） |
| `case_marked_skipped` | `reason` | 見送り理由（必須） |
| `case_marked_reviewed` | — | 追加データなし |
| `case_archived` | `archive_reason` | アーカイブ理由（`expired` / `manual` / `ineligible`） |

#### F-002 イベント

| event_type | 必須 payload キー | 説明 |
|-----------|-----------------|------|
| `reading_queued` | `batch_log_id?`, `trigger_source` | バッチID（バッチ経由時）、トリガー元（`cascade` / `manual` / `batch`） |
| `reading_started` | `version`, `case_card_id` | 処理対象の version と ID |
| `reading_completed` | `version`, `case_card_id`, `confidence_score`, `cache_hit`, `file_hash`, `warnings?[]` | 完了データ。file_hash は原文再現性の参照キー（§10-3）。warnings は §4-3 参照 |
| `reading_failed` | `version`, `error_type`, `error_message` | 失敗データ。error_type は §4-1 参照 |
| `reading_reviewed` | `case_card_id`, `reviewed_by` | 人間確認記録 |
| `reading_requeued` | `previous_version`, `reason?`, `scope` | 再読解トリガー。scope は soft/force |

#### F-003 イベント

| event_type | 必須 payload キー | 説明 |
|-----------|-----------------|------|
| `judging_queued` | `trigger_source` | トリガー元（`cascade` / `manual`） |
| `judging_completed` | `version`, `eligibility_result_id`, `verdict`, `hard_result`, `soft_result` | 判定結果の全体像 |
| `judging_failed` | `version`, `error_type`, `error_message` | 失敗データ |
| `eligibility_overridden` | `previous_verdict`, `new_verdict`, `override_reason`, `eligibility_result_id` | オーバーライド記録（reason 必須） |
| `judging_requeued` | `previous_version`, `reason?`, `scope` | 再判定トリガー |

#### F-004 イベント

| event_type | 必須 payload キー | 説明 |
|-----------|-----------------|------|
| `checklist_generating` | `trigger_source`, `version` | トリガー元 |
| `checklist_generated` | `version`, `checklist_id`, `item_count`, `skeleton?`, `no_schedule?`, `past_deadline?` | 生成結果 |
| `checklist_generation_failed` | `version`, `error_type`, `error_message` | 失敗データ |
| `checklist_item_checked` | `checklist_id`, `item_id`, `progress` | チェック操作。progress は `"3/12"` 形式 |
| `checklist_item_unchecked` | `checklist_id`, `item_id`, `progress` | アンチェック操作 |
| `checklist_completed` | `checklist_id`, `version` | 全項目完了 |
| `checklist_requeued` | `previous_version`, `reason?`, `scope` | 再生成トリガー |

#### F-005 イベント

| event_type | 必須 payload キー | 説明 |
|-----------|-----------------|------|
| `bid_data_imported` | `batch_log_id`, `new_count`, `updated_count`, `csv_hash` | OD取り込み結果。csv_hash は原文再現性の参照キー（§10-3） |
| `bid_detail_scraped` | `batch_log_id`, `target_count`, `success_count` | 詳細スクレイピング結果 |

### §6-2 actor_id 方針

| Phase | actor_id の値 | 意味 |
|-------|-------------|------|
| Phase1 | `"kaneko"` | ユーザー操作（UI経由のアクション） |
| Phase1 | `"system"` | システム自動処理（タイムアウト復旧、自動アーカイブ等） |
| Phase1 | `"batch:{batch_log_id}"` | バッチ処理（cascade_pipeline 含む） |
| Phase2 | `user_id`（UUID） | マルチテナント化後のユーザー識別。VARCHAR(100) のため移行は容易 |

### §6-3 correlation_id 方針

| Phase | 方針 | 理由 |
|-------|------|------|
| Phase1 | **導入しない** | シングルユーザー・逐次処理のため、`case_id + created_at の近傍` で十分追跡可能 |
| Phase2 | `correlation_id UUID` カラムを case_events に追加 | 高トラフィック・並行処理時にカスケード全体を1つの ID で紐付け |

### §6-4 改ざん防止方針

| Phase | 方針 | 詳細 |
|-------|------|------|
| Phase1 | **アプリケーション層で INSERT ONLY** | case_events への UPDATE / DELETE を禁止。アプリケーションコードに DELETE 文を書かない |
| Phase2 | DB レベルのトリガーで DELETE/UPDATE を拒否 | `CREATE RULE ... ON DELETE TO case_events DO INSTEAD NOTHING;` |

> case_events はイミュータブルログとして設計。誤記録の訂正は「訂正イベント」を追加する（上書きしない）。

---

## §7 復旧手順（Recovery Runbook）

### §7-1 *_in_progress スタック復旧

**症状**: 案件が `reading_in_progress` / `judging_in_progress` / `checklist_generating` のまま動かない。

**自動復旧**（§3-5 で定義）:
1. バッチ開始時にスタック案件を走査
2. タイムアウト超過 → 自動で `*_failed` に遷移
3. case_event 記録（error_type: `timeout`）

**手動復旧**（自動復旧が動かない場合）:

```sql
-- 1. スタック案件の特定
SELECT id, case_name, current_lifecycle_stage, updated_at
FROM cases
WHERE current_lifecycle_stage IN ('reading_in_progress', 'judging_in_progress', 'checklist_generating')
  AND updated_at < NOW() - INTERVAL '10 minutes';

-- 2. 手動で failed に遷移（case_events + cases を更新）
-- ※ アプリケーション経由で実行することを推奨（直接SQL変更は最終手段）
```

**アプリケーション経由の復旧**:
- 管理用スクリプト: `python -m app.scripts.recover_stuck_cases --dry-run`
- `--dry-run` で対象案件を確認 → `--execute` で実行

### §7-2 バッチ全体失敗対応

**症状**: batch_logs.status = `failed`（全件失敗）。

**復旧手順**:
1. batch_logs.error_details を確認 → エラーパターンの特定
2. 原因別対応:

| 原因 | 対応 |
|------|------|
| データソースのHTMLレイアウト変更 | アダプターのパーサーを修正 → 手動バッチトリガー |
| ネットワーク障害 | 時間を置いて手動バッチトリガー |
| DB 接続障害 | DB復旧を確認 → 手動バッチトリガー |
| CSVスキーマ変更（F-005） | マッピングレイヤを修正（SSOT-4 §7-4 参照）→ 手動バッチトリガー |

3. 手動バッチトリガー: `POST /api/v1/batch/trigger` または `python -m app.scripts.run_batch --type=case_fetch`

### §7-3 LLM 障害時の運用

**症状**: Claude API が長時間ダウンまたはレート制限。

**影響範囲**: F-002（AI読解）のみ。F-001, F-003, F-004, F-005 はLLM非依存。

**対応**:
1. cascade_pipeline のF-002ステップが全て `reading_failed` になる
2. F-001（案件収集）と F-005（価格分析）は正常動作を継続
3. LLM 復旧後、失敗案件に対して一括リトライ:
   - `python -m app.scripts.retry_failed_readings --scope=soft`
   - または UI から個別にリトライボタン

**予防策**:
- F-002 の自動リトライ（§3-4）で一時的な障害は吸収
- 連続失敗を検出したらバッチ内の F-002 処理を一時停止（3件連続失敗で中断）

### §7-4 データ不整合の復旧

**症状**: cases.current_lifecycle_stage と case_events の最新イベントが不一致。

**原因**: アプリケーションバグ（cases の UPDATE と case_events の INSERT が不整合）。

**復旧手順**:
```sql
-- 1. 不整合案件の特定
SELECT c.id, c.current_lifecycle_stage,
       (SELECT to_status FROM case_events
        WHERE case_id = c.id ORDER BY created_at DESC LIMIT 1) AS events_latest
FROM cases c
WHERE c.current_lifecycle_stage != (
    SELECT to_status FROM case_events
    WHERE case_id = c.id ORDER BY created_at DESC LIMIT 1
);

-- 2. case_events を正とし、cases を修正
-- ※ 管理スクリプト経由で実行
```

- 管理用スクリプト: `python -m app.scripts.fix_lifecycle_mismatch --dry-run`

---

## §8 KPI/メトリクス/観測性

### §8-1 機能別 KPI

| 機能 | KPI | 目標 | 計測方法 |
|------|-----|------|---------|
| F-001 | 案件収集数/日 | Phase1: 対象3領域で10件以上/日 | batch_logs.new_count の日次集計 |
| F-001 | バッチ成功率 | 95%以上 | batch_logs.status の集計 |
| F-002 | 重要項目 Recall | 90%以上 | Phase0 で手動検証 → Phase1 で reading_reviewed 時のフィードバック |
| F-002 | 根拠付与率（重要項目） | 95%以上 | case_cards.evidence の JSONB 走査 |
| F-002 | needs_review 率 | 20%以下 | case_cards.status = 'needs_review' の割合 |
| F-003 | uncertain 率 | 30%以下（初期）→ 10%以下（安定期） | eligibility_results.verdict の集計 |
| F-003 | 判定精度（Hard条件） | 99%以上 | 人間確認との一致率 |
| F-004 | チェックリスト生成成功率 | 95%以上 | checklists.status != 'failed' の割合 |
| F-005 | データ鮮度 | 週1回以上更新 | batch_logs の最終成功日時 |

### §8-2 SLO（Service Level Objectives）

| カテゴリ | SLI | p95 | p99 | 計測対象 |
|---------|-----|-----|-----|---------|
| **API** | GET 系レスポンス | 500ms | 1,000ms | FastAPI middleware で計測 |
| API | POST アクション系レスポンス | 1,000ms | 2,000ms | FastAPI middleware で計測 |
| API | GET /events レスポンス | 300ms | 500ms | FastAPI middleware で計測 |
| **パイプライン** | AI 読解（F-002、1案件） | 30s | 60s | reading_started → reading_completed の差分 |
| パイプライン | 判定（F-003、1案件） | 1s | 2s | judging_queued → judging_completed の差分 |
| パイプライン | チェックリスト生成（F-004、1案件） | 2s | 5s | checklist_generating → checklist_generated の差分 |
| **バッチ** | case_fetch 全体 | 30min | 45min | batch_logs の duration |
| バッチ | od_import 全体 | 30min | 45min | batch_logs の duration |
| **フロントエンド** | 案件一覧表示 | 2s | 3s | フロントエンド計測 |
| フロントエンド | ダッシュボード表示 | 3s | 5s | フロントエンド計測 |

### §8-3 観測メトリクス

Phase1 で計測・記録する観測メトリクス:

| カテゴリ | メトリクス | 集計頻度 | 保存先 |
|---------|----------|---------|-------|
| **AI品質** | evidence 付与率（全項目 / 重要項目） | 日次 | ログ + 定期集計SQL |
| AI品質 | uncertain 率（日次 / 週次） | 日次 | ログ + 定期集計SQL |
| AI品質 | assertion_type 分布（fact / inferred / caution） | 日次 | case_cards.assertion_counts の集計 |
| AI品質 | confidence_score 分布（平均 / 中央値 / p10） | 日次 | case_cards.confidence_score の集計 |
| **リトライ** | リトライ率（機能別） | 日次 | case_events の requeued イベント数 / 全イベント数 |
| リトライ | scope 別リトライ数（soft / force） | 日次 | case_events.payload.scope の集計 |
| **バッチ** | バッチ成功率（batch_type 別） | 日次 | batch_logs.status の集計 |
| バッチ | バッチ所要時間（batch_type 別） | 毎回 | batch_logs の started_at 〜 finished_at |
| バッチ | 部分失敗率 | 日次 | batch_logs.status = 'partial' の割合 |
| **コスト** | LLM トークン使用量（入力 / 出力） | 毎回 | case_cards.llm_response.token_usage |
| コスト | LLM API コスト（日次 / 月次） | 日次 | トークン使用量 × 単価 |
| **学習** | 失注理由タグ率（将来のF-005拡張用） | — | Phase2 で計測開始 |

> LLM コスト上限: Phase0 計測後に具体値を決定。暫定ハードストップとして日次トークン上限を設定する仕組みを用意（§8-3a 参照）。

### §8-3a LLM コスト制御（暫定）

Phase0 で実際のトークン消費量を計測し、本番の上限値を決定する。暫定として仕組みのみ用意する。

| 項目 | 値 |
|------|-----|
| `LLM_DAILY_TOKEN_LIMIT` | Phase0 計測後に決定（暫定: 未設定 = 無制限） |
| 超過時の挙動 | 以降の reading を `reading_failed`（error_type: `cost_cap_exceeded`）に落とす。判定(F-003)・チェックリスト(F-004) はLLM非依存のため影響なし |
| トークン計測 | case_cards.llm_response.token_usage（入力/出力を分離記録） |
| コストレビュー | 月次で LLM API コスト（トークン × 単価）を集計し、上限値の妥当性を検証 |
| 環境変数 | `LLM_DAILY_TOKEN_LIMIT`（0 = 無制限） |

### §8-4 Phase1 の観測性実装

| 層 | ツール | 設定 |
|----|-------|------|
| アプリケーションログ | Python logging + 構造化JSON（§11 参照） | INFO/WARN/ERROR をファイル出力 |
| APIメトリクス | FastAPI middleware（自作） | リクエスト時間、ステータスコード分布を構造化ログに出力 |
| バッチメトリクス | batch_logs テーブル | 全バッチの実行結果を永続化 |
| AI品質メトリクス | case_cards + case_events のクエリ | 定期集計スクリプト（日次 cron） |
| ダッシュボード | Phase1: なし（ログ + SQL クエリ） | Phase2: Grafana or カスタムダッシュボード |

---

## §9 セキュリティ・権限

### §9-1 Phase1: 最小限のセキュリティ

| 項目 | Phase1 方針 | 理由 |
|------|-----------|------|
| 認証 | **なし**（シングルユーザー前提） | Phase1 はローカル/プライベート環境で運用。SSOT-3 §1 原則3 |
| CORS | `localhost` のみ許可 | フロントエンドはローカル開発サーバー |
| API アクセス制限 | なし | プライベートネットワーク内 |
| HTTPS | Phase1: HTTP（ローカル開発）。VPS検証環境では HTTPS（Let's Encrypt） | ローカルは HTTP で十分。外部公開時は HTTPS 必須 |

### §9-2 Phase1: 危険操作の制限

認証がない Phase1 でも、以下の操作を制限する:

| 操作 | 制限方式 | 理由 |
|------|---------|------|
| 案件の一括削除 | API未提供（エンドポイントなし） | 誤操作防止。アーカイブのみ可能 |
| company_profile の初期化 | API未提供 | DB直接操作のみ |
| case_events の削除 | API未提供 + アプリケーション層で禁止（§6-4） | 監査ログの保全 |
| バッチの強制停止 | API未提供 | プロセスキルのみ（Phase2 で API 化） |
| DB マイグレーション | CLI のみ（Alembic） | UI からは実行不可 |

### §9-3 Phase2: JWT + RBAC

| 項目 | Phase2 方針 |
|------|-----------|
| 認証方式 | Bearer Token（JWT）。`Authorization: Bearer <token>` ヘッダー |
| トークン有効期限 | アクセストークン: 1時間 / リフレッシュトークン: 30日 |
| 発行者 | 自前認証 or Auth0 / Clerk 等の外部サービス（[要確認]） |

### §9-4 Phase2: RBAC ロール定義

| ロール | 説明 | 許可操作 |
|-------|------|---------|
| `viewer` | 閲覧のみ | GET 系全エンドポイント。案件一覧・詳細の閲覧、バッチログの閲覧 |
| `operator` | 操作可能 | viewer の全権限 + POST /actions/*（状態遷移、リトライ、オーバーライド）、PATCH（チェック操作）、POST /batch/trigger |
| `admin` | 管理者 | operator の全権限 + PATCH /company-profile、ユーザー管理（Phase2 新設）、設定変更 |

**API への反映**:
- 全エンドポイントに `required_role` を設定（SSOT-3 §3 エンドポイント一覧に列追加）
- JWT の claims に `role` を含める
- FastAPI の Dependency Injection でロールチェック

### §9-5 Phase1→Phase2 の接合点

Phase2 への移行を容易にするため、Phase1 で以下を準備する:

| 準備項目 | Phase1 での実装 | Phase2 での利用 |
|---------|---------------|---------------|
| actor_id カラム | `"kaneko"` / `"system"` を記録 | `user_id` に差し替え |
| API エンドポイント設計 | 認証不要だが、ヘッダーは受理可能 | `Authorization` ヘッダーの処理を追加 |
| ミドルウェア構造 | 認証ミドルウェアのスロットを空けておく | JWT 検証ミドルウェアを差し込む |
| エラーコード | 401 / 403 は未使用 | 認証エラー(401) / 認可エラー(403) を追加 |

---

## §10 データ保持・原文保存ポリシー

### §10-1 原文保存の対象と方式

| # | データ種別 | 保存形式 | ハッシュ | 保存先 | 保持期間 |
|---|----------|---------|--------|-------|---------|
| 1 | 公告HTML（F-001 → F-002） | HTML ファイル | SHA-256 | ファイルシステム | 無期限 |
| 2 | 仕様書PDF（F-002） | PDF ファイル | SHA-256（case_cards.file_hash） | ファイルシステム | 無期限 |
| 3 | OD CSV 原本（F-005） | CSV/ZIP ファイル | SHA-256（batch_logs.metadata.csv_hash） | ファイルシステム | 無期限 |
| 4 | 落札公告詳細HTML（F-005 Layer2） | HTML ファイル | — | ファイルシステム | 1年 |

### §10-2 ファイル保存ディレクトリ構造

```
data/
├── raw/
│   ├── notices/          ← 公告HTML（F-001）
│   │   └── {case_id}/
│   │       └── notice_{YYYYMMDD}.html
│   ├── specs/            ← 仕様書PDF（F-002）
│   │   └── {case_id}/
│   │       └── spec_{sha256_prefix}.pdf
│   ├── od/               ← OD CSV 原本（F-005）
│   │   └── {YYYY}/
│   │       └── od_{YYYYMMDD}_{sha256_prefix}.csv
│   └── bid_details/      ← 落札公告詳細HTML（F-005）
│       └── {YYYY}/
│           └── {source_id}.html
```

### §10-3 ハッシュと再現性

| 項目 | 方針 |
|------|------|
| ハッシュアルゴリズム | SHA-256（全ファイル共通） |
| ハッシュの記録先 | case_cards.file_hash（PDF）、batch_logs.metadata.csv_hash（OD CSV） |
| 再読解時のキャッシュ | scope=soft の場合、file_hash が一致すれば LLM 呼び出しをスキップ（§3-2 参照） |
| 差分取得の判定 | F-005: ファイルハッシュ or HTTP Last-Modified で差分検知 |
| ファイル破損検知 | ダウンロード後にハッシュを算出し、保存時にファイル名に prefix として含める |

### §10-4 DB データの保持期間

| テーブル | 保持期間 | アーカイブ方式 |
|---------|---------|-------------|
| cases | 無期限（archived 含む） | ソフトデリート（deleted_at） |
| case_events | 無期限 | イミュータブル（§6-4） |
| case_cards | 無期限（旧 version 含む） | is_current=false で保持 |
| eligibility_results | 無期限（旧 version 含む） | is_current=false で保持 |
| checklists | 無期限（旧 version 含む） | is_current=false で保持 |
| base_bids | 無期限 | raw_data JSONB で原本保持 |
| bid_details | 無期限 | — |
| batch_logs | 1年 | 1年超過分は定期アーカイブ（別テーブル or ファイルエクスポート） |
| company_profiles | 無期限 | — |

### §10-5 ストレージ見積もり（Phase1 1年間）

| データ種別 | 件数/容量の見積もり | 年間ストレージ |
|----------|------------------|-------------|
| 公告HTML | ～3,000件 × 50KB | ～150MB |
| 仕様書PDF | ～500件 × 2MB | ～1GB |
| OD CSV | 日次 × 10MB | ～3.6GB |
| 落札詳細HTML | ～5,000件 × 30KB | ～150MB |
| DB（全テーブル） | — | ～2GB（インデックス含む） |
| **合計** | — | **～7GB** |

---

## §11 ログ設計

### §11-1 構造化 JSON フォーマット

全ログを以下の構造化 JSON で出力する:

```json
{
  "timestamp": "2026-02-18T09:30:00.123Z",
  "level": "INFO",
  "logger": "app.services.f002_reading",
  "message": "AI reading completed",
  "case_id": "550e8400-e29b-41d4-a716-446655440000",
  "feature_origin": "F-002",
  "batch_log_id": null,
  "trace_id": null,
  "duration_ms": 12345,
  "context": {
    "version": 2,
    "confidence_score": 0.85,
    "cache_hit": false
  }
}
```

### §11-2 必須フィールド

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `timestamp` | ISO8601 (UTC) | ○ | ログ出力日時 |
| `level` | string | ○ | DEBUG / INFO / WARN / ERROR |
| `logger` | string | ○ | Python logger 名（モジュールパス） |
| `message` | string | ○ | 人間可読なメッセージ |
| `case_id` | UUID or null | △ | 案件に紐づく場合は必須 |
| `feature_origin` | string or null | △ | 機能に紐づく場合は必須（F-001〜F-005） |
| `batch_log_id` | UUID or null | △ | バッチ内処理の場合は必須 |
| `trace_id` | string or null | — | Phase2 で導入（分散トレーシング用） |
| `duration_ms` | int or null | — | 処理時間（計測対象の場合） |
| `context` | object | — | 追加情報（自由形式） |

### §11-3 ログレベル基準

| レベル | 基準 | 例 |
|-------|------|-----|
| **DEBUG** | 開発時のみ使用。本番では無効 | LLM プロンプト全文、SQL クエリ、HTTP レスポンスボディ |
| **INFO** | 正常な処理の記録 | バッチ開始/完了、案件処理成功、ステージ遷移 |
| **WARN** | 問題の予兆。処理は継続 | 部分失敗（partial）、高 uncertain 率、低信頼度、スキャンPDF検出 |
| **ERROR** | 処理失敗。人間の確認が必要 | LLM API エラー、DB接続エラー、全件失敗バッチ、スタック検出 |

### §11-4 必須出力ポイント

以下のタイミングで必ずログを出力する:

| タイミング | レベル | 出力内容 |
|-----------|-------|---------|
| バッチ開始 | INFO | batch_type, source, started_at |
| バッチ完了 | INFO / WARN | status, counts (success/error/total), duration_ms |
| 案件処理開始 | INFO | case_id, feature_origin, version |
| 案件処理完了 | INFO | case_id, feature_origin, version, duration_ms |
| 案件処理失敗 | ERROR | case_id, feature_origin, error_type, error_message |
| 自動リトライ | WARN | case_id, retry_count, max_retries, error_type |
| スタック検出 | ERROR | case_id, stuck_stage, stuck_since |
| LLM API 呼び出し | INFO | case_id, model, token_usage (input/output), duration_ms |
| ステージ遷移 | INFO | case_id, from_stage, to_stage, triggered_by |
| ユーザーアクション | INFO | case_id, action, actor_id |

### §11-5 PII・機密マスキング方針

| データ種別 | Phase1 での扱い | マスキングルール |
|----------|---------------|---------------|
| 案件名（公開情報） | マスキング不要 | そのまま出力 |
| 発注機関名（公開情報） | マスキング不要 | そのまま出力 |
| 会社名（company_profile） | マスキング不要（Phase1 は自社のみ） | Phase2: テナント分離で対応 |
| LLM プロンプト | DEBUG レベルのみ出力（本番無効） | INFO 以上ではプロンプトを出力しない |
| LLM レスポンス全文 | DEBUG レベルのみ出力 | INFO 以上では summary（confidence_score 等）のみ |
| PDF/HTML テキスト全文 | ログに出力しない | case_cards.raw_text に保存（DB のみ） |
| API リクエストボディ | INFO で reason 等のユーザー入力のみ | パスワード等の機密フィールドは存在しない（Phase1） |
| ファイルパス | ログに出力可 | 絶対パスではなく相対パス（data/raw/... 形式） |

### §11-6 ログ出力先と保持

| 環境 | 出力先 | ローテーション | 保持期間 |
|------|-------|-------------|---------|
| 開発（dev） | stdout + ファイル（logs/dev.log） | 日次 | 7日 |
| 本番（prod） | ファイル（logs/app.log） | 日次、100MB上限 | 90日 |
| Phase2 | stdout → CloudWatch / Datadog | マネージドサービス側 | 90日 |

---

## §12 インフラ・ライブラリ定数

### §12-1 確定済み技術スタック

| カテゴリ | 技術 | バージョン | 用途 |
|---------|------|----------|------|
| 言語（バックエンド） | Python | 3.12+ | FastAPI アプリケーション |
| 言語（フロントエンド） | TypeScript | 5.x | React アプリケーション |
| Web フレームワーク | FastAPI | 0.110+ | REST API |
| フロントエンド | React | 18+ | SPA |
| パッケージマネージャー | uv (backend) / bun (frontend) | — | 依存管理 |
| DB | PostgreSQL | 16+ | メインデータストア |
| ORM / クエリ | SQLAlchemy 2.0 + asyncpg | — | 非同期DB操作 |
| マイグレーション | Alembic | — | スキーマ管理 |
| HTTP クライアント | httpx | — | 非同期HTTPリクエスト |
| リトライ | tenacity | — | 自動リトライ（§3-4 参照） |
| HTML パーサー | beautifulsoup4 | — | 公告HTML / 落札詳細HTML |
| PDF テキスト抽出 | pdfplumber | — | 仕様書PDF。抽出失敗時は case_cards.extraction_method に記録（SSOT-4 定義済み） |
| LLM API | Claude API（暫定） | — | AI読解（F-002）。LLM Provider 抽象レイヤ経由で呼び出し、差し替え可能とする（§1 原則11） |
| スキーマバリデーション | Pydantic v2 | — | リクエスト/レスポンス/LLMレスポンス |
| CSV パーサー | pandas or polars | — | OD CSV（F-005） |
| 営業日計算 | jpholiday | — | 祝日判定（F-004） |
| バッチ実行 | cron + Python スクリプト | — | Phase1。Phase2: Celery |
| テスト | pytest (backend) / vitest (frontend) | — | — |
| レートリミット | httpx 独自実装 | — | 1 req/sec（§12-2 参照） |

### §12-2 タイムアウト・定数テーブル

| 定数名 | 値 | 用途 | 定義元 |
|--------|-----|------|-------|
| `HTTP_TIMEOUT_SEC` | 30 | HTTP リクエストタイムアウト（1回分） | F-001, F-005 |
| `PDF_DOWNLOAD_TIMEOUT_SEC` | 60 | PDF ダウンロードタイムアウト | F-002 |
| `LLM_API_TIMEOUT_SEC` | 60 | LLM API 呼び出しタイムアウト | F-002 |
| `DB_CONNECT_TIMEOUT_SEC` | 10 | DB 接続タイムアウト | 全機能共通 |
| `READING_STUCK_TIMEOUT_MIN` | 5 | reading_in_progress スタック判定 | §3-5 |
| `JUDGING_STUCK_TIMEOUT_MIN` | 2 | judging_in_progress スタック判定 | §3-5 |
| `CHECKLIST_STUCK_TIMEOUT_MIN` | 1 | checklist_generating スタック判定 | §3-5 |
| `HTTP_RETRY_MAX` | 3 | HTTP リクエストリトライ上限 | §3-4 |
| `HTTP_RETRY_BACKOFF_SEC` | [30, 60, 120] | HTTP リトライバックオフ | §3-4 |
| `LLM_RETRY_MAX` | 2 | LLM API リトライ上限 | §3-4 |
| `LLM_RETRY_BACKOFF_SEC` | [10, 30] | LLM リトライバックオフ | §3-4 |
| `LLM_PARSE_RETRY_MAX` | 1 | LLM レスポンスパースリトライ | §3-4 |
| `DB_RETRY_MAX` | 3 | DB 接続リトライ上限 | §3-4 |
| `DB_RETRY_BACKOFF_SEC` | [1, 2, 4] | DB リトライバックオフ | §3-4 |
| `SCRAPE_RATE_LIMIT_SEC` | 1.0 | スクレイピングのレートリミット（秒/リクエスト） | F-001, F-005 |
| `BATCH_CASE_FETCH_TIMEOUT_MIN` | 30 | case_fetch バッチ全体タイムアウト | F-001 §4 |
| `BATCH_OD_IMPORT_TIMEOUT_MIN` | 30 | od_import バッチ全体タイムアウト | F-005 §4 |
| `BATCH_DETAIL_SCRAPE_TIMEOUT_MIN` | 30 | detail_scrape バッチ全体タイムアウト | F-005 §4 |
| `CONFIDENCE_THRESHOLD` | 0.6 | needs_review 判定閾値 | F-002 §3-D |
| `SCANNED_PDF_CHAR_THRESHOLD` | 50 | スキャンPDF判定（文字数/ページ） | F-002 §3-B |
| `CHUNK_SPLIT_TOKEN_THRESHOLD` | 5000 | セクション分割の閾値（トークン数） | F-002 §4 |
| `EVIDENCE_MATCH_STRONG` | 0.8 | 根拠マッチング：強一致（Jaccard） | F-002 §6 |
| `EVIDENCE_MATCH_CANDIDATE` | 0.65 | 根拠マッチング：候補（Jaccard） | F-002 §6 |
| `SCHEDULE_REVERSE_START_BD` | -5 | 逆算：準備開始（営業日） | F-004 §3-B |
| `SCHEDULE_REVERSE_REVIEW_BD` | -2 | 逆算：社内レビュー（営業日） | F-004 §3-B |
| `SCHEDULE_REVERSE_FINALIZE_BD` | -1 | 逆算：最終確定（営業日） | F-004 §3-B |
| `POLLING_INTERVAL_SEC` | 5 | フロントエンドポーリング間隔 | SSOT-2 §6-6 |
| `CASCADE_FAILURE_THRESHOLD` | 3 | 連続失敗でバッチ内F-002中断 | §7-3 |
| `READING_STUCK_TIMEOUT_SCANNED_MIN` | 10 | is_scanned=true 時の reading_in_progress スタック判定 | §3-5 |
| `LLM_CIRCUIT_BREAKER_THRESHOLD` | 3 | LLM 連続失敗でサーキットブレーカ発動 | §3-4a |
| `LLM_DAILY_TOKEN_LIMIT` | 0 | LLM 日次トークン上限（0=無制限。Phase0 計測後に設定） | §8-3a |

### §12-3 環境変数

```bash
# === データベース ===
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/nyusatsu
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10

# === LLM API ===
LLM_API_KEY=sk-ant-...          # Claude API キー
LLM_MODEL=claude-sonnet-4-20250514       # 使用モデル（LLM Provider 抽象レイヤで切り替え可能）
LLM_MAX_TOKENS=4096

# === アプリケーション ===
APP_ENV=development              # development / production
APP_LOG_LEVEL=INFO
APP_LOG_DIR=logs/

# === バッチ ===
BATCH_SCHEDULE_CASE_FETCH=0 6 * * *     # 毎日06:00
BATCH_SCHEDULE_OD_IMPORT=0 6 * * *      # 毎日06:00
BATCH_SCHEDULE_DETAIL_SCRAPE=0 7 * * *  # 毎日07:00

# === データ保存 ===
DATA_RAW_DIR=data/raw/

# === コスト制御 ===
LLM_DAILY_TOKEN_LIMIT=0          # 0=無制限（Phase0計測後に設定）
```

---

## [要確認] 一覧

| # | 項目 | 影響範囲 | 暫定決定 |
|---|------|---------|---------|
| 1 | LLM コスト上限（日次トークン数） | §8-3a, §12-2 | Phase0 計測後に `LLM_DAILY_TOKEN_LIMIT` の具体値を決定 |

> v1.1 で旧 [要確認] 8件中7件を暫定決定として解消。残1件はPhase0で計測データが得られた段階で確定する。

---

## クロスリファレンス

| 参照元 | 参照先（本ドキュメント） | 内容 |
|-------|---------------------|------|
| SSOT-2 §8 [解決済み] | §3-5, §7-1 | reading_in_progress タイムアウトの定義 |
| SSOT-3 §4-2 retry共通オプション | §3-2 | scope=soft/force の詳細挙動 |
| SSOT-3 §6 冪等性 | §5 | Phase1→Phase2 の段階設計 |
| SSOT-4 §3-9b 整合性ガード | §6-1 | payload 必須キーの展開 |
| SSOT-4 §6 再実行モデル | §3 | version + is_current のワークフロー |
| F-001 §3-H | §4-1 | データソース取得失敗のハンドリング |
| F-002 §3-H | §4-1 | LLM API/PDF/スキャンPDF のハンドリング |
| F-003 §3-H | §4-1 | uncertain フォールバックのハンドリング |
| F-004 §3-H | §4-1 | NULL データ時のスケルトン生成 |
| F-005 §3-H | §4-1 | OD取得/CSVパースのハンドリング |
| SSOT-5 §3-4a サーキットブレーカ | §4-4, §7-3 | LLM 連続失敗時の degraded mode |
| SSOT-5 §8-3a コスト制御 | §12-2 | LLM_DAILY_TOKEN_LIMIT の仕組み |
