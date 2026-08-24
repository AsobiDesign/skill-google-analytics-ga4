# GA4 主要ディメンション・メトリクス

GA4 Data API の主要なディメンション・メトリクスの定義・用途・取得パラメータを整理する。すべてのレポートタイプで最初に「基本サマリー」を確認し、そこからテーマに応じて深掘りする。

ディメンション名・メトリクス名は [GA4 Data API スキーマ](https://developers.google.com/analytics/devguides/reporting/data/v1/api-schema) の正式名称をそのまま使う（`scripts/ga4_query.py` の `--dimensions` / `--metrics` にはこの名称を渡す）。

## 分析方法

### 基本サマリー

#### 定義
アクティブユーザー数・新規ユーザー数・セッション数・ページビュー数・平均セッション滞在時間。サイト全体のアクセス規模と質を示す。

#### 用途
過去の同一期間と比較し、増減の全体像を把握する。ここを起点に、どの流入元・デバイス・ページで変動が起きたかを深掘りする。

#### 取得パラメータ
```
--dimensions ""
--metrics activeUsers,newUsers,sessions,screenPageViews,averageSessionDuration
```
ディメンション指定なしで期間合計を取得する。

### リファラー別セッション数

#### 定義
`pageReferrer`（参照元ページURL）別のセッション数。どの外部ページから流入しているかを示す。

#### 用途
特定の外部サイト・記事・SNS投稿からの流入効果を確認する。ソース/メディアより粒度が細かく、個別の参照元URLを特定したいときに使う。

#### 取得パラメータ
```
--dimensions pageReferrer
--metrics sessions
--order-by sessions:desc
```

### ソース/メディア別セッション数

#### 定義
`sessionSourceMedium`（例: `google / organic`、`line / social`）別のセッション数。集客チャネルの内訳を示す。

#### 用途
検索・広告・SNS・メルマガなど、どの経路が流入を作っているかを把握する。広告効果測定や施策別の流入比較に使う。

#### 取得パラメータ
```
--dimensions sessionSourceMedium
--metrics sessions
--order-by sessions:desc
```

### チャネルグループ別セッション数

#### 定義
`sessionDefaultChannelGroup`（Organic Search、Paid Search、Direct、Referral、Social、Email等）別のセッション数。ソース/メディアを標準分類でまとめた粗い粒度の内訳。

#### 用途
チャネル単位の大きな傾向を掴みたいとき、または売上データとの突き合わせでチャネル別貢献度を見たいときに使う（`references/cross-channel-reference.md` 参照）。

#### 取得パラメータ
```
--dimensions sessionDefaultChannelGroup
--metrics sessions
--order-by sessions:desc
```

### ランディングページ別セッション数

#### 定義
`landingPage`（セッションの最初の閲覧ページ）別のセッション数。どのページが集客の入口になっているかを示す。

#### 用途
入口ページごとの集客力を評価する。特定ページへの流入が急減/急増した場合、そのページの検索順位・広告出稿・SNS露出の変化を疑う。

#### 取得パラメータ
```
--dimensions landingPage
--metrics sessions
--order-by sessions:desc
```

### デバイス別セッション数

#### 定義
`deviceCategory`（desktop / mobile / tablet）別のセッション数。閲覧環境の内訳を示す。

#### 用途
モバイル比率の推移を確認し、レスポンシブ対応やモバイル導線改善の優先度を判断する。

#### 取得パラメータ
```
--dimensions deviceCategory
--metrics sessions
--order-by sessions:desc
```

### 国別セッション数

#### 定義
`country` 別のセッション数。地理的な流入分布を示す。

#### 用途
海外からの不自然なアクセス（ボット等）の検知や、越境ECの需要地域を把握する。

#### 取得パラメータ
```
--dimensions country
--metrics sessions
--order-by sessions:desc
```

### カート追加イベント分析

#### 定義
`add_to_cart` イベントの発生数（`eventCount`）を、参照元・ソース/メディア・発生ページ別に見たもの。どの流入経路・ページがカート投入という購買意欲行動につながっているかを示す。

#### 用途
セッション数は多いがカート追加が少ない流入元は「量はあるが質が低い」と判断できる。広告経由の質の評価、LP改善対象の特定に使う。Makeshopの受注データと突き合わせれば、カート追加→購入までの歩留まりも評価できる（`references/cross-channel-reference.md` 参照）。

#### 取得パラメータ
```
--dimensions pageReferrer,sessionSourceMedium,pageLocation
--metrics eventCount
--dimension-filter eventName=add_to_cart
--order-by eventCount:desc
```

## ユーザーリクエスト → 参照ディメンション/メトリクス

「主」が必須、「補」は深掘りやレポート向け。複合的なレポート作成は `references/cross-channel-reference.md` も参照。

| リクエスト | 主 | 補 |
|---|---|---|
| アクセス状況全体、PV数、セッション数、ユーザー数 | 基本サマリー | チャネルグループ, デバイス |
| 流入経路、どこから来ているか | ソース/メディア | リファラー, チャネルグループ |
| 広告効果測定、キャンペーン効果 | ソース/メディア | チャネルグループ, カート追加イベント |
| 検索/SNS/直接流入などの内訳 | チャネルグループ | ソース/メディア |
| 人気ページ、集客力のあるページ | ランディングページ | チャネルグループ |
| スマホ/PC比率、モバイル対応の要否 | デバイス | 基本サマリー |
| 海外アクセス、地域別分布 | 国別 | 基本サマリー |
| 購買意欲の高い流入元、カート投入の起点 | カート追加イベント | ソース/メディア, ランディングページ |
| 流入と売上の関係、CVR | チャネルグループ + 基本サマリー | `references/cross-channel-reference.md` |

## キーワード索引

ユーザー発話に含まれるキーワードから引く。複数候補がある場合は上表で文脈に合うものを選ぶ。

| キーワード | 主要項目 |
|---|---|
| アクセス、PV、ページビュー、セッション数、ユーザー数、滞在時間、直帰 | 基本サマリー |
| リファラー、参照元、どこから来た、外部サイト、被リンク元 | リファラー |
| 流入経路、ソース、メディア、広告効果、キャンペーン効果、SEO効果 | ソース/メディア |
| チャネル、チャネル別、検索/SNS/直接の内訳、流入チャネル構成 | チャネルグループ |
| ランディングページ、入口ページ、LP、人気ページ | ランディングページ |
| デバイス、スマホ、モバイル、PC比率、タブレット | デバイス |
| 国、地域、海外アクセス、越境 | 国別 |
| カート追加、カゴ落ち、購買意欲、CTA効果 | カート追加イベント |
| 流入と売上、CVR、コンバージョン率、広告のROI、チャネル貢献度 | 基本サマリー + チャネルグループ（`cross-channel-reference.md`） |
