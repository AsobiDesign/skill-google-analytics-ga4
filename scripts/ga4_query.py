#!/usr/bin/env python3
"""GA4 Data API 汎用クエリツール。

指定したプロパティ・期間・ディメンション/メトリクスでGoogle Analytics 4のレポートを取得し、
結果をJSONとして標準出力に書き出す。google-analytics-ga4スキルのデータ取得ステップから
Bashツール経由で呼び出されることを想定している。
"""

import argparse
import json
import os
import sys


def parse_args() -> argparse.Namespace:
    """コマンドライン引数を定義・解析する。引数なし。戻り値: 解析済みNamespace。"""
    parser = argparse.ArgumentParser(
        description="GA4 Data API から指定条件でレポートを取得し、JSONを標準出力に書き出す。"
    )
    parser.add_argument("--property", dest="property_key", help="config/properties.json のキー名（例: example-shop）")
    parser.add_argument("--property-id", dest="property_id", help="GA4プロパティIDを直接指定（--propertyより優先）")
    parser.add_argument("--start-date", required=True, help="対象期間の開始日（YYYY-MM-DD）")
    parser.add_argument("--end-date", required=True, help="対象期間の終了日（YYYY-MM-DD）")
    parser.add_argument("--dimensions", default="", help="取得するディメンション名（カンマ区切り、例: sessionSourceMedium,deviceCategory）")
    parser.add_argument("--metrics", required=True, help="取得するメトリクス名（カンマ区切り、例: sessions,activeUsers）")
    parser.add_argument(
        "--dimension-filter",
        dest="dimension_filters",
        action="append",
        default=[],
        help="name=value 形式のディメンション完全一致フィルタ。複数指定でAND条件（例: --dimension-filter eventName=add_to_cart）",
    )
    parser.add_argument("--order-by", dest="order_by", help="ソート条件。metricName:desc または metricName:asc（ディメンション名も指定可）")
    parser.add_argument("--limit", type=int, default=20, help="取得件数の上限（デフォルト20）")
    parser.add_argument("--compare-start-date", dest="compare_start_date", help="比較期間の開始日（YYYY-MM-DD）")
    parser.add_argument("--compare-end-date", dest="compare_end_date", help="比較期間の終了日（YYYY-MM-DD）")
    parser.add_argument("--credentials", help="サービスアカウントJSON鍵の絶対パス（省略時は環境変数 GOOGLE_SERVICE_ACCOUNT_JSON）")
    parser.add_argument("--properties-file", dest="properties_file", help="properties.jsonのパス（省略時はスクリプトと同階層の ../config/properties.json）")

    return parser.parse_args()


def fail(message: str) -> None:
    """エラーメッセージを標準エラー出力に日本語で書き出し、exit code 1で終了する。引数: message(str)。戻り値なし。"""
    print(f"エラー: {message}", file=sys.stderr)
    sys.exit(1)


def load_env_file(env_path: str) -> dict:
    """KEY=VALUE形式の.envファイルを簡易パースする。引数: env_path(.envファイルパス)。戻り値: キーと値のdict。"""
    values = {}
    if not os.path.isfile(env_path):
        return values

    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip().strip('"').strip("'")

    return values


def resolve_credentials_path(args: argparse.Namespace) -> str:
    """サービスアカウントJSON鍵の絶対パスを解決する。優先順位は --credentials > 環境変数 > スキル直下の.envファイル。引数: args(解析済み引数)。戻り値: 検証済みの絶対パス(str)。"""
    credentials_path = args.credentials or os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")

    if not credentials_path:
        skill_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_file = os.path.join(skill_root, ".env")
        credentials_path = load_env_file(env_file).get("GOOGLE_SERVICE_ACCOUNT_JSON")

    if not credentials_path:
        fail(
            "サービスアカウントJSON鍵のパスが指定されていません。"
            "スキル直下の .env ファイルに GOOGLE_SERVICE_ACCOUNT_JSON=/path/to/service-account.json を設定するか、"
            "環境変数 GOOGLE_SERVICE_ACCOUNT_JSON、または --credentials で指定してください。"
        )

    if not os.path.isabs(credentials_path):
        fail(f"サービスアカウントJSON鍵のパスは絶対パスで指定してください: {credentials_path}")

    if not os.path.isfile(credentials_path):
        fail(f"サービスアカウントJSON鍵が見つかりません: {credentials_path}")

    return credentials_path


def resolve_property_id(args: argparse.Namespace) -> str:
    """--property-id または --property（properties.json参照）からGA4プロパティIDを解決する。引数: args(解析済み引数)。戻り値: プロパティID文字列。"""
    if args.property_id:
        return args.property_id

    if not args.property_key:
        fail("--property または --property-id のいずれかを指定してください。")

    properties_file = args.properties_file
    if not properties_file:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        properties_file = os.path.join(script_dir, "..", "config", "properties.json")
    properties_file = os.path.abspath(properties_file)

    if not os.path.isfile(properties_file):
        fail(f"properties.jsonが見つかりません: {properties_file}")

    try:
        with open(properties_file, "r", encoding="utf-8") as f:
            properties = json.load(f)
    except json.JSONDecodeError as e:
        fail(f"properties.jsonの形式が不正です（{properties_file}）: {e}")
        return ""  # fail()がexitするがlinter対策

    entry = properties.get(args.property_key)
    if entry is None:
        available = ", ".join(sorted(properties.keys())) or "（登録なし）"
        fail(f"property '{args.property_key}' はproperties.jsonに登録されていません。登録済みキー: {available}")

    property_id = entry.get("property_id")
    if not property_id:
        fail(f"property '{args.property_key}' に property_id が設定されていません（{properties_file}）")

    return str(property_id)


def parse_dimension_filters(raw_filters: "list[str]"):
    """`name=value` 形式の文字列群をGA4 API用のAND条件フィルタ式に変換する。引数: raw_filters(name=value文字列のリスト)。戻り値: FilterExpressionまたはNone。"""
    if not raw_filters:
        return None

    from google.analytics.data_v1beta.types import Filter, FilterExpression, FilterExpressionList

    expressions = []
    for raw in raw_filters:
        if "=" not in raw:
            fail(f"--dimension-filter は name=value 形式で指定してください: '{raw}'")
        name, value = raw.split("=", 1)
        expressions.append(
            FilterExpression(
                filter=Filter(
                    field_name=name,
                    string_filter=Filter.StringFilter(value=value),
                )
            )
        )

    if len(expressions) == 1:
        return expressions[0]

    return FilterExpression(and_group=FilterExpressionList(expressions=expressions))


def parse_order_by(order_by_arg: "str | None", dimension_names: "list[str]"):
    """--order-by 引数（metricName:desc等）をGA4 APIのOrderByオブジェクトに変換する。引数: order_by_arg(name:desc形式文字列), dimension_names(取得対象ディメンション名一覧)。戻り値: OrderByのリスト。"""
    if not order_by_arg:
        return []

    from google.analytics.data_v1beta.types import OrderBy

    if ":" in order_by_arg:
        field_name, direction = order_by_arg.split(":", 1)
    else:
        field_name, direction = order_by_arg, "desc"

    desc = direction.strip().lower() != "asc"

    if field_name in dimension_names:
        return [OrderBy(dimension=OrderBy.DimensionOrderBy(dimension_name=field_name), desc=desc)]

    return [OrderBy(metric=OrderBy.MetricOrderBy(metric_name=field_name), desc=desc)]


def run_report(client, property_id, dimensions, metrics, start_date, end_date, dimension_filter, order_bys, limit):
    """GA4 Data API にレポートリクエストを送信する。引数: client, dimensions/metrics(名前リスト), start_date/end_date, dimension_filter, order_bys, limit。戻り値: APIレスポンス(RunReportResponse)。"""
    from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, RunReportRequest

    request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[Dimension(name=d) for d in dimensions],
        metrics=[Metric(name=m) for m in metrics],
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        order_bys=order_bys,
        limit=limit,
    )
    if dimension_filter is not None:
        request.dimension_filter = dimension_filter

    return client.run_report(request)


def map_rows(response, dimensions, metrics) -> "list[dict]":
    """APIレスポンスの行データを、ディメンション名/メトリクス名をキーにした辞書のリストへ変換する。引数: response(APIレスポンス), dimensions/metrics(名前リスト)。戻り値: 辞書のリスト。"""
    rows = []
    for row in response.rows:
        mapped = {}
        for index, name in enumerate(dimensions):
            mapped[name] = row.dimension_values[index].value
        for index, name in enumerate(metrics):
            mapped[name] = row.metric_values[index].value
        rows.append(mapped)
    return rows


def main() -> None:
    """スクリプトのエントリーポイント。引数を解析し、GA4データを取得してJSONを標準出力に書き出す。引数なし。戻り値なし。"""
    args = parse_args()

    if not args.start_date or not args.end_date:
        fail("--start-date と --end-date を指定してください。")

    dimensions = [d.strip() for d in args.dimensions.split(",") if d.strip()]
    metrics = [m.strip() for m in args.metrics.split(",") if m.strip()]

    if not metrics:
        fail("--metrics を1つ以上指定してください。")

    credentials_path = resolve_credentials_path(args)
    property_id = resolve_property_id(args)
    dimension_filter = parse_dimension_filters(args.dimension_filters)
    order_bys = parse_order_by(args.order_by, dimensions)

    try:
        from google.oauth2 import service_account
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
    except ImportError:
        fail(
            "必要なパッケージがインストールされていません。"
            "`pip3 install -r scripts/requirements.txt` を実行してください。"
        )
        return

    try:
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=["https://www.googleapis.com/auth/analytics.readonly"],
        )
    except Exception as e:
        fail(f"サービスアカウント認証情報の読み込みに失敗しました: {e}")
        return

    client = BetaAnalyticsDataClient(credentials=credentials)

    try:
        response = run_report(
            client, property_id, dimensions, metrics, args.start_date, args.end_date, dimension_filter, order_bys, args.limit
        )
    except Exception as e:
        fail(f"GA4 Data APIへのリクエストに失敗しました（property_id={property_id}）: {e}")
        return

    result = {
        "property": args.property_key or property_id,
        "start_date": args.start_date,
        "end_date": args.end_date,
        "rows": map_rows(response, dimensions, metrics),
    }

    if args.compare_start_date and args.compare_end_date:
        try:
            compare_response = run_report(
                client,
                property_id,
                dimensions,
                metrics,
                args.compare_start_date,
                args.compare_end_date,
                dimension_filter,
                order_bys,
                args.limit,
            )
        except Exception as e:
            fail(f"比較期間のGA4 Data APIリクエストに失敗しました（property_id={property_id}）: {e}")
            return

        result["compare"] = {
            "start_date": args.compare_start_date,
            "end_date": args.compare_end_date,
            "rows": map_rows(compare_response, dimensions, metrics),
        }
    elif args.compare_start_date or args.compare_end_date:
        fail("比較期間を指定する場合は --compare-start-date と --compare-end-date を両方指定してください。")

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
