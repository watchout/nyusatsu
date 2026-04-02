---
name: discovery
description: |
  Discovery & Business Phase。アイデア検証・事業設計を担当。
  「ディスカバリー」「discovery」「アイデア」「ビジネス設計」「business」で実行。
---

# Discovery & Business Skill

## 概要

プロジェクト初期段階のアイデア発掘から事業設計までを一貫して担当。
Discovery（D1-D4）で課題を検証し、Business（B1-B4）で持続可能なビジネスモデルに落とし込む。

## ワークフロー

```
Discovery                          Business
──────────                         ──────────
D1: Idea Excavator                 B1: Value Architect
    ↓ アイデアの核心を抽出              ↓ 価値提案を設計
D2: Problem Validator              B2: Competitor Analyst
    ↓ 課題の実在性を検証               ↓ 競合と差別化を分析
D3: User Profiler                  B3: Revenue Designer
    ↓ ターゲットユーザーを特定          ↓ マネタイズモデルを設計
D4: Market Scout                   B4: Go-to-Market Planner
    ↓ 市場機会を評価                   ↓ 市場投入戦略を策定

→ IDEA_CANVAS + USER_PERSONA       → VALUE_PROPOSITION + COMPETITOR_ANALYSIS
  + COMPETITOR_ANALYSIS(初版)         + BUSINESS_MODEL + GTM_STRATEGY
```

## 実行ルール

1. **1回の発言で1つだけ質問する**（まとめて聞かない）
2. **必ず具体例を添える**（回答のハードルを下げる）
3. **各Stage完了時に整理・確認する**（認識ズレを防ぐ）
4. **「まとまっていなくてOK」と伝える**（完璧を求めない）
5. **ドキュメント生成は1つずつ、ユーザー承認を挟む**

## Discovery エージェント詳細

### D1: Idea Excavator（アイデア発掘者）

ユーザーの漠然としたアイデアから核心を引き出す。

**質問バンク**:
- 「どんな問題を解決したいですか？」
- 「理想の状態はどんな姿ですか？」
- 「既存の解決策の何が不満ですか？」
- 「その問題に気づいたきっかけは？」
- 「解決したら誰が一番喜びますか？」

**出力**: アイデアの核心、解決すべき課題の仮説

### D2: Problem Validator（課題検証者）

課題が実在し、解決する価値があるか検証する。

**質問バンク**:
- 「この問題で具体的に困った経験は？」
- 「今どうやって対処していますか？」
- 「解決されたらいくら払えますか？」
- 「どのくらいの頻度で困っていますか？」
- 「この問題を放置するとどうなりますか？」

**評価基準**:
- 深刻度: 日常的に困るか、たまにか
- 頻度: 毎日か、月1回か
- 代替手段: 既に何かで対処しているか
- 支払意欲: お金を払ってでも解決したいか

**出力**: 課題の深刻度スコア、解決意欲の評価

### D3: User Profiler（ユーザープロファイラー）

ターゲットユーザーの具体像を特定する。

**質問バンク**:
- 「最も困っているのは誰ですか？」
- 「その人の1日を教えてください」
- 「その人は普段どこで情報を得ますか？」
- 「その人のITリテラシーはどのくらい？」
- 「その人は何に価値を感じますか？」

**出力**: ペルソナ仮説、ユーザージャーニー仮説

### D4: Market Scout（市場偵察者）

市場機会と競合状況を評価する。

**質問バンク**:
- 「競合サービスを知っていますか？」
- 「なぜ競合では不十分なのですか？」
- 「どのくらいの市場規模を想定していますか？」
- 「海外に類似サービスはありますか？」

**出力**: 競合分析仮説、差別化ポイント仮説

## Business エージェント詳細

### B1: Value Architect（価値設計者）

ユーザーに提供する価値を明確に言語化する。

**フレームワーク**:
- バリュープロポジションキャンバス
- Jobs to be Done
- ゲインクリエイター / ペインリリーバー

**チェックリスト**:
- [ ] 顧客のJob（達成したいこと）が明確か
- [ ] Pain（避けたいこと）を具体的に列挙したか
- [ ] Gain（得たいこと）を具体的に列挙したか
- [ ] 競合と差別化できる価値があるか

**出力**: VALUE_PROPOSITION.md

### B2: Competitor Analyst（競合分析者）

競合状況を分析し、差別化ポイントを明確化する。

**分析観点**:
- 直接競合 / 間接競合 / 代替手段
- 機能比較マトリクス
- ポジショニングマップ（2軸）

**出力**: COMPETITOR_ANALYSIS.md

### B3: Revenue Designer（収益設計者）

持続可能な収益モデルを設計する。

**検討事項**:
- 課金モデル（サブスク/従量/フリーミアム/買い切り）
- 価格設定戦略（競合基準/価値基準/コスト基準）
- LTV/CAC 試算

**出力**: BUSINESS_MODEL セクション（PRDに統合）

### B4: Go-to-Market Planner（市場投入計画者）

市場投入戦略を策定する。

**検討事項**:
- ローンチ戦略（PLF/Build in Public）
- チャネル戦略
- 初期ユーザー獲得計画

**マーケティング原則参照** (specs/08_MARKETING.md):
- ジェイ・エイブラハム: 3軸成長、リスクリバーサル
- DRM: PASONA、2ステップ
- ローンチ戦略: PLF、Build in Public

**出力**: GTM_STRATEGY（または LP_SPEC.md への入力）

## 成果物一覧

| 成果物 | 完成度 | 担当 | 次フェーズ入力 |
|--------|--------|------|---------------|
| IDEA_CANVAS.md | 80% | D1-D4 | Business全体 |
| USER_PERSONA.md | 50% | D3 | Product Phase |
| COMPETITOR_ANALYSIS.md | 80% | D4+B2 | Product Phase |
| VALUE_PROPOSITION.md | 80% | B1 | Product Phase |
| BUSINESS_MODEL | 60% | B3 | PRD統合 |
| GTM_STRATEGY | 40% | B4 | LP_SPEC.md |

## Multi-perspective Check

出力を確定する前に、以下の視点を検討:
- **Product**: ユーザーニーズに合致するか？ペルソナは実在するか？
- **Technical**: 技術的に実現可能か？開発コストは妥当か？
- **Business**: ビジネスモデルは持続可能か？市場は十分か？

視点間の緊張があれば、それを明記して解決策を示す。

## 次のフェーズ

Discovery & Business 完了後:
1. 成果物一覧をユーザーに提示して確認
2. 「設計フェーズ（/design）に進みますか？」と提案
3. 承認されたら Skill ツールで /design を起動
