# PROJECT_PLAN.md - プロジェクト計画書

> プロジェクトの進捗・マイルストーン・残タスクを一元管理する

---

## 基本情報

| 項目 | 内容 |
|------|------|
| プロジェクト名 | 入札ラクダAI |
| 開始日 | 2026-02-13 |
| Phase1 目標完了 | 2026-08（6ヶ月後） |
| 開発者 | 金子 裕司（1人開発） |
| 最終更新日 | 2026-02-18 |

---

## 1. マイルストーン

| MS | 名称 | ゲート | 成果物 | ステータス |
|----|------|-------|--------|-----------|
| M0 | フレームワーク導入 | — | CLAUDE.md + ディレクトリ構造 | ✅ 完了 |
| M1 | 事業設計 | 事業設計ゲート | docs/idea/ 4ドキュメント | ✅ 完了 |
| M2 | プロダクト概要 | プロダクト概要ゲート | SSOT-0 PRD + SSOT-1 機能カタログ | ✅ 完了 |
| M3 | 機能仕様 | 機能仕様ゲート | P0個別仕様書（F-001〜F-005） | ✅ 完了 |
| M4 | 技術設計 | 技術設計ゲート | SSOT-2〜5（UI/API/Data/CrossCutting） | ✅ 完了 |
| M5 | 開発環境 | Pre-Code Gate A | package.json, requirements.txt, .env, docker-compose | 🔜 進行中 |
| M6 | Phase0 検証 | — | AI読解PoC, 案件件数調査, OD取込テスト | ⬜ 未着手 |
| M7 | Phase1 MVP | — | P0機能（F-001〜F-005）実装・運用 | ⬜ 未着手 |

```
    M0     M1     M2     M3     M4     M5     M6     M7
    │      │      │      │      │      │      │      │
    ▼      ▼      ▼      ▼      ▼      ▼      ▼      ▼
────●──────●──────●──────●──────●──────●──────●──────●────▶
    ✅     ✅     ✅     ✅     ✅     🔜
  FW導入  事業設計 PRD   機能仕様 技術設計 開発環境 検証   MVP
```

---

## 2. 現在のマイルストーン: M5 開発環境

### 完了条件
- pyproject.toml / package.json / docker-compose.yml / .env が揃うこと
- `framework gate check-a` が PASS すること
- Pre-Code Gate A 通過 → ソースコード編集を解禁

### 実装計画
- **IMPLEMENTATION_PLAN_P0.md** に 55 タスク（Phase 0〜7 + SIM）を定義済み
- 詳細: `docs/management/IMPLEMENTATION_PLAN_P0.md`
- Phase 0（TASK-01〜03）が M5 に該当する

---

## 3. 完了済みドキュメント一覧

### M0: フレームワーク導入 ✅

| 成果物 | パス | 承認日 |
|--------|-----|--------|
| CLAUDE.md | CLAUDE.md | 2026-02-16 |
| ディレクトリ構造 | docs/, src/, .claude/, .framework/ | 2026-02-16 |

### M1: 事業設計 ✅

| 成果物 | パス | 承認日 |
|--------|-----|--------|
| アイデアキャンバス | docs/idea/IDEA_CANVAS.md | 2026-02-17 |
| ユーザーペルソナ | docs/idea/USER_PERSONA.md | 2026-02-17 |
| 競合分析 | docs/idea/COMPETITOR_ANALYSIS.md | 2026-02-17 |
| 価値提案 | docs/idea/VALUE_PROPOSITION.md | 2026-02-17 |

### M2: プロダクト概要 ✅

| 成果物 | パス | 承認日 |
|--------|-----|--------|
| PRD | docs/requirements/SSOT-0_PRD.md | 2026-02-17 |
| 機能カタログ | docs/requirements/SSOT-1_FEATURE_CATALOG.md | 2026-02-17 |

### M3: 機能仕様 ✅

| 成果物 | パス | 承認日 |
|--------|-----|--------|
| F-005 価格分析 | docs/design/features/project/F-005_価格分析.md | 2026-02-17 |
| F-001 案件自動収集 | docs/design/features/project/F-001_案件自動収集.md | 2026-02-17 |
| F-002 AI読解 | docs/design/features/project/F-002_AI読解.md | 2026-02-17 |
| F-003 参加可否判定 | docs/design/features/project/F-003_参加可否判定.md | 2026-02-17 |
| F-004 チェックリスト生成 | docs/design/features/project/F-004_チェックリスト生成.md | 2026-02-17 |

### M4: 技術設計 ✅

| 成果物 | パス | 承認日 |
|--------|-----|--------|
| SSOT-4 データモデル v2 | docs/design/core/SSOT-4_DATA_MODEL.md | 2026-02-18 |
| SSOT-2 UI/状態遷移 v2 | docs/design/core/SSOT-2_UI_STATE.md | 2026-02-18 |
| SSOT-3 API規約 v1.1 | docs/design/core/SSOT-3_API_CONTRACT.md | 2026-02-18 |
| SSOT-5 横断的関心事 v1.1 | docs/design/core/SSOT-5_CROSS_CUTTING.md | 2026-02-18 |
| P0 実装タスク分解 | docs/management/IMPLEMENTATION_PLAN_P0.md | 2026-02-18 |

---

## 4. 今後のマイルストーン概要

### M5: 開発環境

| タスク | 内容 |
|-------|------|
| バックエンド | requirements.txt / pyproject.toml / FastAPI 初期設定 |
| フロントエンド | package.json / bun / React 初期設定 |
| 環境変数 | .env / .env.example |
| framework CLI | `framework init` → project.json / `framework plan` → plan.json |
| Pre-Code Gate | Gate A パス → ソースコード編集を解禁 |

### M6: Phase0 検証

| 検証項目 | 成功基準 |
|---------|---------|
| 対象3領域の案件件数 | 月20件以上 |
| AI読解精度（仕様書PoC） | 要点抽出の精度80%以上 |
| 調達ポータルOD取り込み | 差分取得が7日間安定動作 |

### M7: Phase1 MVP

| KPI | 目標（6ヶ月後） |
|-----|---------------|
| 入札参加件数 | 月10件以上 |
| 落札件数 | 月2件以上 |
| 案件探索時間 | 1日10分以内 |
| 提出不備率 | 0% |

---

## 5. リスク・課題

| # | リスク/課題 | 影響 | 対策 | ステータス |
|---|-----------|------|------|-----------|
| 1 | AI読解の精度が実用レベルに達しない | Phase0 No-Go | Phase0 PoCで早期検証 | 未検証 |
| 2 | 対象領域の案件数が不足 | Phase1 KPI未達 | Phase0で件数調査 | 未検証 |
| 3 | 1人開発で全M7まで到達できるか | 全体遅延 | MVPを5機能に絞る | 監視中 |

---

## 変更履歴

| 日付 | 変更内容 | 変更者 |
|------|---------|-------|
| 2026-02-17 | 初版作成（M0〜M2完了時点のスナップショット） | Claude / 金子 |
| 2026-02-18 | M3 機能仕様・M4 技術設計 完了、M5 開始、IMPLEMENTATION_PLAN_P0.md 追加 | Claude / 金子 |
