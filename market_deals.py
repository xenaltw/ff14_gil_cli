import json
import statistics
from pathlib import Path
import time
from models import CandidateItem, UnderpricedDeal

ITEMS_JSON = Path("data/items.json")
HIGH_VALUE_CANDIDATES_JSON = Path("data/high_value_candidates.json")


def load_marketable_items(path=ITEMS_JSON):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = []

    for item in payload.values():
        if not item.get("can_market", False):
            continue

        item_id = int(item["item_id"])
        item_name = item.get("name", str(item_id))
        rows.append(CandidateItem(item_id=item_id, item_name=item_name))

    rows.sort(key=lambda x: x.item_id)
    return rows


def _recent_sale_prices(market_item, days=7):
    if market_item is None:
        return []

    cutoff_ts = int(time.time()) - days * 24 * 60 * 60
    prices = []

    for row in market_item.recent_sales:
        if row.price_per_unit is None or row.price_per_unit <= 0:
            continue

        ts = getattr(row, "timestamp", None)
        if ts is None:
            continue

        if int(ts) < cutoff_ts:
            continue

        prices.append(float(row.price_per_unit))

    return prices


def build_high_value_candidates(
    items,
    market_map,
    min_recent_sales=5,
    min_sales_per_day=0.1,
    min_median_price=10000.0,
):
    rows = []

    for item in items:
        market_item = market_map.get(item.item_id)
        if market_item is None:
            continue

        prices = _recent_sale_prices(market_item)
        if len(prices) < min_recent_sales:
            continue

        median_price = statistics.median(prices)
        sales_per_day = float(market_item.regular_sale_velocity or 0.0)

        if median_price < min_median_price:
            continue
        if sales_per_day < min_sales_per_day:
            continue

        rows.append(CandidateItem(item_id=item.item_id, item_name=item.item_name))

    rows.sort(key=lambda x: x.item_id)
    return rows


def save_high_value_candidates(rows, path=HIGH_VALUE_CANDIDATES_JSON):
    payload = [
        {
            "item_id": row.item_id,
            "item_name": row.item_name,
        }
        for row in rows
    ]
    Path(path).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_high_value_candidates(path=HIGH_VALUE_CANDIDATES_JSON):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return [
        CandidateItem(
            item_id=int(row["item_id"]),
            item_name=row["item_name"],
        )
        for row in payload
    ]


def buy_threshold_ratio(median_price: float) -> float:
    if median_price < 10_000:
        return 0.45
    if median_price < 30_000:
        return 0.50
    if median_price < 80_000:
        return 0.58
    if median_price < 150_000:
        return 0.63
    if median_price < 300_000:
        return 0.67
    return 0.72


def min_gap_threshold(median_price: float) -> float:
    if median_price < 10_000:
        return 3_000
    if median_price < 30_000:
        return 5_000
    if median_price < 80_000:
        return 10_000
    if median_price < 150_000:
        return 20_000
    if median_price < 300_000:
        return 35_000
    return 50_000


def _lowest_listing(market_item):
    if market_item is None or not market_item.listings:
        return None

    valid = [x for x in market_item.listings if x.price_per_unit and x.price_per_unit > 0]
    if not valid:
        return None

    return min(valid, key=lambda x: x.price_per_unit)


def scan_underpriced_items(
    candidates,
    default_world_market_map,
    target_world_market_map,
    min_recent_sales=5,
    min_sales_per_day=0.1,
):
    rows = []

    for item in candidates:
        default_world_item = default_world_market_map.get(item.item_id)
        target_world_item = target_world_market_map.get(item.item_id)

        if target_world_item is None:
            continue

        target_recent_prices = _recent_sale_prices(target_world_item)
        if len(target_recent_prices) < min_recent_sales:
            continue

        target_world_median_price = float(statistics.median(target_recent_prices))
        sales_per_day = float(target_world_item.regular_sale_velocity or 0.0)

        if sales_per_day < min_sales_per_day:
            continue

        lowest = _lowest_listing(target_world_item)
        if lowest is None:
            continue

        lowest_listing_price = float(lowest.price_per_unit)
        if target_world_median_price <= 0:
            continue

        price_gap = target_world_median_price - lowest_listing_price
        price_ratio = lowest_listing_price / target_world_median_price

        if price_ratio > buy_threshold_ratio(target_world_median_price):
            continue

        if price_gap < min_gap_threshold(target_world_median_price):
            continue

        default_world_median_price = None
        if default_world_item is not None:
            default_recent_prices = _recent_sale_prices(default_world_item)
            if default_recent_prices:
                default_world_median_price = float(statistics.median(default_recent_prices))

        rows.append(
            UnderpricedDeal(
                item_id=item.item_id,
                item_name=item.item_name,
                world_name=lowest.world_name or "Unknown",
                lowest_listing_price=lowest_listing_price,
                target_world_median_price=target_world_median_price,
                default_world_median_price=default_world_median_price,
                price_gap=price_gap,
                price_ratio=price_ratio,
                sales_per_day=sales_per_day,
                recent_sales_count=len(target_recent_prices),
            )
        )

    rows.sort(key=lambda x: (x.price_gap, x.sales_per_day), reverse=True)
    return rows
