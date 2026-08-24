---
name: google-analytics-ga4
description: "Google Analytics 4（GA4）のデータ取得ツールでセッション・ユーザー・流入経路データを取得し、アクセス解析・流入分析・問題検知・原因分析・改善提案を行う。テキスト（会話内レポート）またはChart.js HTMLダッシュボードで出力する。基本サマリー（アクティブユーザー・新規ユーザー・セッション数・PV・平均滞在時間）、リファラー分析、ソース/メディア分析、チャネルグループ分析、ランディングページ分析、デバイス分析、国別分析、カート追加イベント分析に対応。「GA4」「Google Analytics」「アクセス解析」「セッション数」「PV」「流入経路」「チャネル」「ランディングページ」「直帰率」「滞在時間」「サイト流入」「広告効果測定」「流入と売上の関係」「どこから来ているか」「アクセス解析レポート」など、GA4データの分析が少しでも絡むリクエストにはすべてこのスキルを使う。数値の確認だけでなく、なぜ変動したかの原因分析や次に何をすべきかの施策提案まで対応する。Makeshopの売上・注文データ（shop-analyticsスキル）と組み合わせた統合分析を行う場合は references/cross-channel-reference.md を参照する。"
---

# GA4データ取得・分析スキル

Google Analytics 4 Data API を通じてセッション・流入データを取得し、アクセス解析・問題検知・レポート作成・施策提案を行う。MCPサーバーではなく、ローカルのPythonスクリプト（`scripts/ga4_query.py`）をBashツールで実行してデータを取得する。

## ワークフロー

### 1. ヒアリング

以下の項目をすべて明確にしてから次工程に進む。ユーザーの発話から推測できる項目は確認なしで進めてよいが、曖昧な場合は必ず聞き返す。

| 項目 | 確認内容 |
|---|---|
| 対象プロパティ | どのサイト/GA4プロパティを対象とするか（例: `example-shop`、`rakuten-example-shop`。`config/properties.json` を参照） |
| 分析テーマ | 何を知りたいか・何を解決したいか（例: 「流入経路の内訳」「セッション数が落ちた原因」「広告経由の効果測定」） |
| 分析対象指標 | テーマに対して具体的にどのディメンション/メトリクスを出すか |
| 対象期間 | いつからいつまでのデータを対象とするか |
| 出力形式 | テキスト or HTML |

#### 1-1. 対象プロパティの特定

`config/properties.json` を読み、キー名の一覧をユーザーに確認する。ユーザーの発話にサイト名・ドメインが含まれていれば推測してよい。複数プロパティ（例: 自社サイトと楽天店舗）にまたがる比較依頼の場合は、両方のプロパティに対してデータ取得を行う。

#### 1-2. 分析テーマの聞き取り

ユーザーから「何を知りたいか・何を解決したいか」を聞く。曖昧な表現の場合は意図を確認する。

#### 1-3. 分析対象指標の具体化

テーマだけでは何を取得すべきかが定まらないため、**ディメンション/メトリクスのレベルまで具体化してユーザーと合意を取る**。

**スキップ条件**: ユーザー発話の中で具体的な指標が明示されている場合（例: 「チャネル別のセッション数を見せて」「ランディングページ上位10件だけ知りたい」）は、提案による確認を省略して 1-4 に進む。曖昧な指標が1つでも残っていれば実施する。

**該当リファレンスの特定**:

1. 依頼が **日次/週次/月次/ダッシュボード等の複合レポート**、または **Makeshopの売上データと組み合わせた統合分析** → `references/cross-channel-reference.md` を起点に、構成要素を特定
2. 依頼が **単一テーマ**（基本サマリー、リファラー、チャネル、ランディングページなど） → `references/metrics-dimensions-reference.md` の「ユーザーリクエスト→参照ディメンション/メトリクス」索引表で該当行を引く
3. 上記いずれにも当てはまらない曖昧な依頼 → 同ファイルの「キーワード索引」で発話に含まれる単語から候補を絞る

**手順**:

1. 上記で該当する項目を `references/metrics-dimensions-reference.md` から特定する
2. テーマに合ったディメンション/メトリクスを2〜4個に絞ってユーザーに提案し、確認を取る

提案例:
> ユーザー: 「最近の流入経路を分析したい」
> Claude: `references/metrics-dimensions-reference.md` を確認 → 「ソース/メディア別セッション数とチャネルグループ別セッション数を分析対象にしますが、いかがでしょうか?」

ユーザーが指標の追加・削除を求めた場合は調整する。

#### 1-4. 対象期間

| ユーザーの表現 | 対象期間 | 比較対象 |
|---|---|---|
| 「今月のアクセス」「今月はどう」 | 当月1日〜本日 | 前月同期間 |
| 「先月のアクセス」 | 前月1日〜前月末日 | 前々月 |
| 「最近のアクセス」「アクセスはどう」 | 直近1ヶ月 | その前の1ヶ月 |
| 「今年のアクセス」 | 当年1月1日〜本日 | 前年同期間 |
| 明示的な期間指定 | 指定期間 | 同じ長さの直前期間 |

Makeshopのshop-analyticsスキルと統合分析する場合は、**必ず両スキルで同じ対象期間・比較期間を指定する**（`references/cross-channel-reference.md` 参照）。

#### 1-5. 出力形式

「グラフで見たい」「ダッシュボード」→ HTML、「簡潔に教えて」「会話で報告」→ テキスト。

### 2. 取得項目の確認

必要なディメンション/メトリクスだけを取得して実行時間を短縮する。プロパティを複数回・期間を複数回叩く場合は、ユーザーに許可をとってから実行する。

手順:

1. 1-3 で特定したディメンション/メトリクスを `references/metrics-dimensions-reference.md` で確認し、GA4 Data API上の正式なパラメータ名（dimension名・metric名）を確定する
2. **出力形式が HTML の場合は、この時点で `references/report-reference-html.md` も読み込み、ダッシュボード描画に必要な構成を洗い出しに加える**
3. カート追加イベント等、イベント単位の分析が必要な場合は `--dimension-filter eventName=add_to_cart` のようなフィルタ条件を洗い出す

### 3. データ取得

`scripts/ga4_query.py` をBashツールで実行してデータを取得する。

```
python3 scripts/ga4_query.py --property <config/properties.jsonのキー> --start-date YYYY-MM-DD --end-date YYYY-MM-DD --dimensions <カンマ区切り> --metrics <カンマ区切り> [--dimension-filter name=value] [--order-by metricName:desc] [--limit N]
```

比較期間が必要な場合は `--compare-start-date` / `--compare-end-date` も指定すると、同じレスポンスに比較期間のデータも含めて返す。

**初回セットアップ（プロジェクトごとに必要）**: このスキルは複数プロジェクト（複数の会社・店舗）で共有する前提のため、SKILL.md/scripts/referencesはシンボリックリンクで共有し、認証情報・対象プロパティだけは各プロジェクトの `.claude/skills/google-analytics-ga4/` 直下に実体として配置する。`os.path.abspath(__file__)` はシンボリックリンクを解決しないため、`scripts/ga4_query.py` が「プロジェクト側の実行パス」を基準に `.env` を探しに行く（原本フォルダ側の `.env` は読みに行かない）。

1. プロジェクトの `.claude/skills/google-analytics-ga4/.env` に以下を記載（`.env.example` 参照）:
   ```
   GOOGLE_SERVICE_ACCOUNT_JSON=/absolute/path/to/service-account.json
   ```
2. プロジェクトの `.claude/skills/google-analytics-ga4/config/properties.json` に対象プロパティを登録（`config/properties.example.json` 参照）
3. `pip3 install -r scripts/requirements.txt` を実行（初回のみ）

`--credentials` 引数や環境変数 `GOOGLE_SERVICE_ACCOUNT_JSON` でも上書き可能。未設定の場合はスクリプトがエラーで案内を出す。

手順:

1. 対象期間のデータを、2で確定したディメンション/メトリクス・フィルタ条件で取得する
2. 比較対象期間がある場合（1-4 の表で定義された前月・前年同期間など）は `--compare-start-date` / `--compare-end-date` を付けて同時に取得する。前期比・前年比の算出に必須
3. 複数プロパティ（自社サイト・楽天店舗など）を比較する場合は、プロパティごとに実行する

### 4. 分析・出力

1. `references/metrics-dimensions-reference.md` の用途説明に従い分析を実施する
2. 分析カテゴリに応じた構成で結果をまとめる
   - **アクセス状況の把握**: 指標の算出 → 前期間との比較 → 変動要因の分解（流入元・デバイス・ランディングページ別） → 次のアクションへの示唆
   - **問題検知・原因分析**: 概況把握 → 問題の特定（どの流入元/ページで落ちたか） → 原因の深掘り → 対応策の提示
   - **レポート・資料作成**: サマリー（結論先出し） → 基本指標の算出 → 前期間比較 → 注目トピックの深掘り → 推奨アクション
   - **売上との統合分析**: `references/cross-channel-reference.md` に従い、Makeshopのshop-analyticsスキルで取得した売上・注文データと突き合わせる
3. レポートリファレンスを参照し、指定された形式で出力する

## リファレンス一覧

| ファイル | 内容 |
|---|---|
| `references/metrics-dimensions-reference.md` | GA4主要ディメンション・メトリクスの定義・用途・取得パラメータ、ユーザーリクエスト→参照ディメンション/メトリクスの索引、キーワード索引 |
| `references/report-reference-html.md` | Chart.jsによるHTMLダッシュボードの生成方法（Makeshop shop-analyticsと共通のカラーパレット） |
| `references/report-reference-text.md` | 会話内テキストレポートの構成 |
| `references/cross-channel-reference.md` | Makeshopの売上・注文データ（shop-analyticsスキル）と組み合わせた統合分析の考え方 |

Makeshopのshop-analyticsスキル（注文・会員データ分析）やoptimize-productsスキル（商品診断）と組み合わせて統合分析する場合は `references/cross-channel-reference.md` を参照する。
