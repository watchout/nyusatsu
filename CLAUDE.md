# CLAUDE.md - プロジェクト指示書（Claude Code用）

> Claude Code はこのファイルを自動で読み込みます。
> プロジェクトの全仕様書は docs/ にあります。

---

## ⚠️ AI中断プロトコル（最優先ルール）

以下の場合、即座に作業を中断しユーザーに質問すること:

1. SSOTに記載がない仕様判断が必要な時
2. SSOTの記載が曖昧で複数解釈が可能な時
3. 技術的な選択肢が複数あり判断できない時
4. SSOTと既存実装が矛盾している時
5. 制約・規約に未定義のケースに遭遇した時
6. 変更の影響範囲が判断できない時
7. ビジネス判断が必要な時

「推測で進める」「とりあえず仮で」は禁止。

---

## プロセスゲート強制ルール

```
■ 1アクション = 1ドキュメント（絶対ルール）

  ドキュメント生成を依頼された場合:
  - 1つのドキュメントを生成する
  - 生成結果を表示する
  - ユーザーの確認を待つ
  - ユーザーが承認するまで次に進まない

  「まとめて生成」「一括作成」「効率化のため全部」は禁止。

■ ヒアリング = 1問ずつ（絶対ルール）

  仕様のヒアリングが必要な場合:
  - 1回の発言で1つだけ質問する
  - 必ず具体例を添える
  - 回答を受けてから次の質問をする

  「以下の5点について教えてください」は禁止。

■ ゲートチェック

  以下のタイミングで、前ステップの成果物を検証する:
  - docs/idea/ の4ドキュメント完成 → 事業設計ゲート通過
  - docs/requirements/ の2ドキュメント完成 → プロダクト概要ゲート通過
  - P0機能の全SSOT完成（各 Freeze 2） → 機能仕様ゲート通過
  - docs/design/core/ の3ドキュメント完成 → 技術設計ゲート通過

  ゲート未通過で次のフェーズに進むことは禁止。

■ [要確認] マーカー

  既存資料にない情報を補完する場合:
  - 推測で埋めず「[要確認]」マーカーを付ける
  - [要確認] 項目をユーザーに1つずつ質問する
  - 全ての [要確認] が解消されるまでドキュメントは未完了
```

---

## プロジェクト概要

| 項目 | 内容 |
|------|------|
| プロダクト名 | 入札ラクダAI |
| 概要 | 官公庁・自治体等の入札業務を「わかる・見つかる・進められる」状態に標準化し、案件探索→選定→入札準備→入札→結果学習→落札後までを半自動〜自動化するSaaS |
| 技術スタック | Python (FastAPI) + React (bun) |
| リポジトリ | （未設定） |

---

## 最重要ルール

```
1. 仕様書がない機能は実装しない
2. 実装前に必ず該当の仕様書を読む
3. 仕様と実装の乖離を見つけたら報告する
4. コア定義（docs/design/core/）は原則変更不可
```

---

## 🔒 Pre-Code Gate（CLI で構造的に強制）

```
コードを1行でも書く前に、3段階のGateを全て通過する必要がある。
Gate は 2層の構造的強制で実行される。

Layer 1: Claude Code hook（リアルタイム）
  - PreToolUse フックが Edit/Write をインターセプト
  - src/ 等のソースコードパスへの編集を Gate 未通過時にブロック
  - .claude/hooks/pre-code-gate.sh → .framework/gates.json を参照
  - docs/, config 等の非ソースファイルは制限なし

Layer 2: Git pre-commit hook（コミット時）
  - ソースファイルが含まれるコミットで `framework gate check` をフル実行
  - 緊急時は `git commit --no-verify` でバイパス可能

Gate A: 開発環境・インフラの準備
  - package.json, requirements.txt, .env, docker-compose, CI/CD の存在確認

Gate B: タスク分解・計画の完了
  - .framework/plan.json（framework plan 実行済み）
  - .framework/project.json の存在確認

Gate C: SSOT 完全性チェック
  - 各SSOT の §3-E/F/G/H セクションが記入されているか

操作コマンド:
  framework gate check       全Gate一括チェック → gates.json に保存
  framework gate check-a     Gate A のみチェック
  framework gate check-b     Gate B のみチェック
  framework gate check-c     Gate C のみチェック
  framework gate status      現在のGate状態を表示
  framework gate reset       Gate 状態をリセット

自動連動:
  framework plan 成功時     → Gate B が自動パス
  framework audit ssot 実行時 → Gate C が自動評価

日常のワークフロー:
  1. framework gate check   ← 全ゲートをチェック
  2. framework gate status  ← 結果を確認
  3. 未通過のGateがあれば修正
  4. framework run          ← 全Gate通過後のみ実行可能
```

---

## Workflow Orchestration

このプロジェクトには4つの専門スキルが .claude/skills/ に配置されている。
各スキルには専門エージェントが定義されており、品質の高い成果物を生成する。

### スキル起動ルール

**明示的なフェーズ指示**（以下のキーワード）→ 即座に Skill ツールで対応スキルを起動:

| キーワード | 起動スキル |
|-----------|-----------|
| 「ディスカバリー」「何を作りたい？」「アイデア」 | /discovery |
| 「設計」「仕様を作って」「スペック」「アーキテクチャ」 | /design |
| 「実装開始」「コードを書いて」「タスク分解」 | /implement |
| 「レビュー」「監査」「audit」 | /review |

**タスク指示**（「DEV-XXXを実装して」「〇〇機能を作って」等）→ 適切なスキルの起動を提案:
- 新機能の場合: 「/design で設計してから /implement で実装しますか？」
- 既存機能の修正: 「/implement で実装しますか？」
- 品質確認: 「/review で監査しますか？」
ユーザーが承認したら Skill ツールで起動。不要と判断されたらスキップ。

**軽微な作業**（typo修正、設定変更、1ファイルの小修正等）→ スキル不要。直接作業。

### フェーズ遷移
各スキル完了後、次のフェーズを提案する:
discovery → design → implement → review
ユーザー承認後に次スキルを Skill ツールで起動。

### Pre-Code Gate 連携
「実装開始」の場合:
1. Skill ツールで /implement を起動
2. /implement スキル内で .framework/gates.json を確認
3. 全Gate passed なら実装開始。未通過なら報告。

---

## 会社ナレッジ参照ルール

> `.framework/project.json` に `knowledgeSource` が設定されている場合、
> `framework sync-knowledge` で会社の知識データベースからダイジェストを生成できる。

```
参照ファイル: docs/knowledge/_company/KNOWLEDGE_DIGEST.md

このファイルが存在する場合、以下のルールを適用する:

1. 設計判断・機能提案の前に KNOWLEDGE_DIGEST.md を読み、記載された原則に従う
2. マーケティング関連の判断はダイジェストの原則を根拠にする
3. ダイジェストの原則と矛盾する実装を検出した場合は警告する
4. ダイジェストに記載のない領域の判断が必要な場合は報告する

ファイルが存在しない場合は、このセクションを無視してよい。

設定: .framework/project.json の knowledgeSource
更新: framework sync-knowledge（または手動で配置）
```

---

## 仕様書の参照方法

### 実装前に必ず確認するドキュメント（優先順）

```
1. 機能仕様書         → docs/design/features/
2. コア定義           → docs/design/core/
   - UI/状態遷移      → docs/design/core/SSOT-2_UI_STATE.md
   - API規約          → docs/design/core/SSOT-3_API_CONTRACT.md
   - データモデル     → docs/design/core/SSOT-4_DATA_MODEL.md
   - 横断的関心事     → docs/design/core/SSOT-5_CROSS_CUTTING.md
3. 開発規約           → docs/standards/
   - コーディング規約 → docs/standards/CODING_STANDARDS.md
   - テスト規約       → docs/standards/TESTING_STANDARDS.md
   - Git運用          → docs/standards/GIT_WORKFLOW.md
4. PRD               → docs/requirements/SSOT-0_PRD.md
```

### 機能を実装する時のフロー

```
1. 対象の機能仕様書を読む
   → docs/design/features/common/  （共通機能）
   → docs/design/features/project/ （固有機能）

2. 関連するコア定義を確認
   → API設計 → SSOT-3
   → DB設計 → SSOT-4
   → 認証/エラー/ログ → SSOT-5

3. 実装
   → コーディング規約に従う
   → テスト規約に従う

4. テスト
   → 仕様書のテストケースに基づく
```

---

## ディレクトリ構造

```
.claude/
└── agents/                   ← Agent Teams（CLI パターン）

docs/                         ← 全仕様書（SSOT）
├── idea/                     ← アイデア・検証
├── requirements/             ← 要件定義
├── design/                   ← 設計
│   ├── core/                 ← コア定義（変更不可）
│   ├── features/             ← 機能仕様
│   │   ├── common/           ← 共通機能
│   │   └── project/          ← 固有機能
│   └── adr/                  ← 設計判断記録
├── standards/                ← 開発規約
├── operations/               ← 運用
├── marketing/                ← マーケティング
├── growth/                   ← グロース
└── management/               ← プロジェクト管理

src/                          ← ソースコード
├── backend/                  ← FastAPI バックエンド
│   ├── app/                  ← アプリケーション
│   │   ├── api/              ← APIエンドポイント
│   │   ├── models/           ← データモデル
│   │   ├── services/         ← ビジネスロジック
│   │   └── core/             ← 設定・共通
│   └── tests/                ← バックエンドテスト
└── frontend/                 ← React フロントエンド
    ├── src/
    │   ├── components/       ← UIコンポーネント
    │   ├── pages/            ← ページ
    │   ├── hooks/            ← カスタムフック
    │   ├── services/         ← API連携
    │   └── types/            ← 型定義
    └── tests/                ← フロントエンドテスト
```

---

## 技術スタック

| カテゴリ | 技術 |
|---------|------|
| バックエンド | Python / FastAPI |
| フロントエンド | React / TypeScript |
| パッケージマネージャー | bun (frontend) / uv (backend) |
| DB | （未定） |
| 認証 | （未定） |
| ホスティング | （未定） |
| CSS | （未定） |
| テスト | pytest (backend) / vitest (frontend) |
| CI/CD | （未定） |

---

## コーディング規約（要約）

> 詳細: docs/standards/CODING_STANDARDS.md

### 命名規則
- コンポーネント: PascalCase（`LoginForm.tsx`）
- Python モジュール: snake_case（`bid_scorer.py`）
- 関数/変数: camelCase (TS) / snake_case (Python)
- 定数: UPPER_SNAKE_CASE（`MAX_RETRY_COUNT`）
- 型/Interface: PascalCase + 接尾辞（`UserResponse`, `AuthState`）

### 基本原則
- 1ファイル200行以内を目安
- 1関数1責務
- マジックナンバー禁止（定数化する）
- any 禁止（型を明示する）
- コメントは「なぜ」を書く（「何を」はコードで表現）

---

## Git 運用（要約）

> 詳細: docs/standards/GIT_WORKFLOW.md

### ブランチ戦略
```
main ← production
  └── develop ← 開発統合
        └── feature/XXX-description ← 機能開発
        └── fix/XXX-description ← バグ修正
        └── hotfix/XXX-description ← 緊急修正
```

### コミットメッセージ
```
<type>(<scope>): <description>

type: feat | fix | docs | style | refactor | test | chore
scope: 機能ID or モジュール名
```

---

## テスト規約（要約）

> 詳細: docs/standards/TESTING_STANDARDS.md

### テスト種類
- ユニットテスト: 全ビジネスロジック
- 統合テスト: API エンドポイント
- E2Eテスト: クリティカルパス

### カバレッジ目標
- ビジネスロジック: 80%+
- API: 70%+
- 全体: 60%+

---

## 禁止事項

```
❌ 仕様書にない機能を勝手に実装しない
❌ コア定義を勝手に変更しない
❌ テストなしでPRを出さない
❌ any 型を使わない
❌ console.log / print をプロダクションコードに残さない
❌ 環境変数をハードコードしない
❌ エラーを握りつぶさない（必ずハンドリング）
```

---

## よくあるタスクのコマンド例

```bash
# 機能実装
claude "docs/design/features/common/AUTH-001_login.md の仕様に基づいて
       ログイン機能を実装して"

# テスト生成
claude "src/backend/tests/ のテストを
       docs/standards/TESTING_STANDARDS.md に基づいて生成して"

# リファクタリング
claude "src/ 以下のエラーハンドリングを
       docs/design/core/SSOT-5_CROSS_CUTTING.md に準拠させて"

# 仕様書の更新
claude "docs/design/features/project/FEAT-003.md を
       新しい要件に基づいて更新して"
```
