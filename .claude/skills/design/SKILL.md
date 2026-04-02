---
name: design
description: |
  Product & Technical Design Phase。プロダクト設計と技術設計を担当。
  「設計」「design」「仕様」「プロダクト設計」「技術設計」「アーキテクチャ」で実行。
---

# Design Skill (Product + Technical)

## 概要

ビジネス要件をプロダクト仕様に変換し（P1-P5）、
それを実装可能な技術設計に落とし込む（T1-T5）専門家チーム。

## ワークフロー

```
Product Design                     Technical Design
──────────────                     ────────────────
P1: PRD Author                     T1: Tech Stack Selector
    ↓ プロダクト要件を定義              ↓ 技術スタック選定
P2: Feature Cataloger              T2: API Architect
    ↓ 機能を分類・優先度付け            ↓ API契約を設計
P3: UI State Designer              T3: Data Modeler
    ↓ 画面と状態遷移を設計              ↓ データモデルを設計
P4: Feature Spec Writer            T4: Cross-Cutting Designer
    ↓ 各機能の詳細仕様を作成            ↓ 認証・エラー・ログを設計
P5: UX Validator                   T5: Security Reviewer
    ↓ ユーザー体験を検証               ↓ セキュリティを検証

→ PRD + Feature Catalog            → API_CONTRACT + DATA_MODEL
  + UI_STATE + 各機能SSOT             + CROSS_CUTTING + SECURITY
```

## 実行ルール

- ドキュメント生成は**1つずつ**、ユーザー承認を挟む
- 仕様ヒアリングは**1回の発言で1つだけ質問**する
- 不明な情報は推測で埋めず「[要確認]」マーカーを付ける
- Freeze 2（Contract）完了で実装開始可能

## Product エージェント詳細

### P1: PRD Author（PRD作成者）

**役割**: プロダクト要件定義書を作成

**含む内容**:
- プロダクトビジョン
- ターゲットユーザー（ペルソナ参照）
- コア機能（MUST/SHOULD/COULD）
- 成功指標（KPI）
- 制約条件

**チェックリスト**:
- [ ] ビジョンが1文で表現できているか
- [ ] MUST機能が5個以内に絞れているか
- [ ] KPIが計測可能か
- [ ] ペルソナとの整合性があるか

**出力**: SSOT-0_PRD.md

### P2: Feature Cataloger（機能カタログ作成者）

**役割**: 機能を体系的に分類し優先度付け

**分類軸**:
- 共通機能（認証、アカウント、エラー処理）→ Layer 2
- 固有機能（プロジェクト特有）→ Layer 3
- MVP / Post-MVP

**出力**: SSOT-1_FEATURE_CATALOG.md

### P3: UI State Designer（UI状態設計者）

**役割**: 画面一覧と状態遷移を設計

**設計内容**:
- 画面一覧
- 認証状態（S0-S4）ごとの表示
- 画面遷移図
- 主要コンポーネント

**出力**: SSOT-2_UI_STATE.md

### P4: Feature Spec Writer（機能仕様作成者）

**役割**: 各機能の詳細SSOTを作成（specs/04_FEATURE_SPEC.md に従う）

**フロー**:
1. 共通質問（5項目）: 主要アクター、前提条件、主要フロー、代替フロー、データ項目
2. 種別質問（機能種別ごと）
3. UI確認
4. 仕様確定
5. SSOT生成（§3-E/F/G/H 含む）

**質問バンク（共通）**:
- 「この機能の主なユーザー（アクター）は誰ですか？」
- 「この機能を使う前に何が完了している必要がありますか？」
- 「メインの操作フロー（ステップ）を教えてください」
- 「エラーや例外が起きたらどう対応しますか？」
- 「扱うデータ項目とその制約は？」

**出力**: docs/design/features/{ID}_{name}.md

### P5: UX Validator（UX検証者）

**役割**: ユーザー体験の観点から仕様を検証

**検証観点**:
- ユーザーフローの自然さ
- エラー時の体験
- アクセシビリティ
- モバイル対応
- 3クリック以内で主要操作が完了するか

**出力**: UX改善提案、仕様へのフィードバック

## Technical エージェント詳細

### T1: Tech Stack Selector（技術選定者）

**役割**: プロジェクトに最適な技術スタックを選定

**選定基準**:
- プロジェクトタイプ（app/api/lp/hp/cli）
- チーム経験・学習コスト
- 長期保守性
- エコシステムの成熟度

**出力**: TECH_STACK（PRDまたは独立ドキュメント）

### T2: API Architect（API設計者）

**役割**: API契約を設計（RESTful / GraphQL）

**設計内容**:
- エンドポイント一覧
- リクエスト/レスポンス形式
- 認証・認可
- エラーレスポンス
- OpenAPI仕様

**チェックリスト**:
- [ ] 全MUST機能のエンドポイントが定義されているか
- [ ] エラーレスポンスが統一形式か
- [ ] 認証が適切に設計されているか
- [ ] ページネーションが定義されているか

**出力**: SSOT-3_API_CONTRACT.md

### T3: Data Modeler（データモデラー）

**役割**: データベース設計とマイグレーション計画

**設計内容**:
- ER図（Mermaid形式）
- テーブル定義（カラム、型、制約）
- インデックス戦略
- マイグレーション順序

**出力**: SSOT-4_DATA_MODEL.md

### T4: Cross-Cutting Designer（横断設計者）

**役割**: 横断的関心事を設計

**設計内容**:
- 認証フロー（S0-S4状態管理）
- エラーコード体系（AUTH_xxx, VAL_xxx, RES_xxx, RATE_xxx, SYS_xxx）
- ログ設計（構造化ログ）
- 監視・アラート

**出力**: SSOT-5_CROSS_CUTTING.md

### T5: Security Reviewer（セキュリティレビュアー）

**役割**: セキュリティ観点から設計をレビュー

**レビュー観点**:
- OWASP Top 10
- 認証・認可の堅牢性
- データ保護（暗号化、マスキング）
- 入力検証
- 依存関係の脆弱性

**出力**: SECURITY_REVIEW、設計へのフィードバック

## Freeze 単位

```
Freeze 1: Domain  → P1, P2 完了後（用語・スコープ確定）
Freeze 2: Contract → P3, P4, T2, T3 完了後（実装開始可能）
Freeze 3: Exception → T4 完了後（テスト・監査可能）
Freeze 4: Non-functional → T5 完了後（リリース準備完了）
```

## 成果物一覧

| 成果物 | 完成度 | 担当 |
|--------|--------|------|
| SSOT-0_PRD.md | 90% | P1 |
| SSOT-1_FEATURE_CATALOG.md | 90% | P2 |
| SSOT-2_UI_STATE.md | 80% | P3 |
| 各機能SSOT | 100% | P4 |
| SSOT-3_API_CONTRACT.md | 90% | T2 |
| SSOT-4_DATA_MODEL.md | 90% | T3 |
| SSOT-5_CROSS_CUTTING.md | 90% | T4 |

## Multi-perspective Check

出力を確定する前に、以下の視点を検討:
- **Product**: ユーザーニーズを満たす設計か？使いやすいか？
- **Technical**: 実装可能で保守しやすいか？技術的負債を生まないか？
- **Business**: ビジネスモデルを支えるか？スケーラブルか？

視点間の緊張があれば、それを明記して解決策を示す。

## TDD条件

Technical Phaseの成果物はCORE/CONTRACT層に該当するため、
プロジェクトタイプが api/cli の場合は **TDD強制** の対象。

```
SSOT → テスト作成 → 実装 → コード監査
```

## 次のフェーズ

Design 完了後:
1. 設計成果物をユーザーに提示して確認
2. 「実装フェーズ（/implement）に進みますか？」と提案
3. 承認されたら Skill ツールで /implement を起動
