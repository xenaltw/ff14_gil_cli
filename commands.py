from universalis_client import UniversalisClient
from cache_store import CacheStore
from recipe_source import load_recipes
from profit_engine import analyze_opportunities, debug_recipe_cost, explain_sell_price
from ranker import rank_opportunities, diagnose_filters
from output import print_opportunities_table
import time
from tqdm import tqdm
from datetime import datetime, UTC
from refresh_status import write_refresh_status
from output import fmt_num
from market_deals import (
    load_marketable_items,
    build_high_value_candidates,
    save_high_value_candidates,
    load_high_value_candidates,
    scan_underpriced_items,
)
from output import print_underpriced_deals_table


def collect_required_item_ids(target_item_ids, recipe_map):
    visited_items = set()

    def dfs(item_id):
        if item_id in visited_items:
            return
        visited_items.add(item_id)

        recipe = recipe_map.get(item_id)
        if recipe is None:
            return

        for ing in recipe.ingredients:
            dfs(ing.item_id)

    for item_id in target_item_ids:
        dfs(item_id)

    return visited_items


def dedupe_recipes_by_item_id(recipes):
    unique = {}
    for r in recipes:
        if r.item_id not in unique:
            unique[r.item_id] = r
    return list(unique.values())


def run_scan(args):
    started_at = time.time()

    log_info("[STAGE] init cache/client")
    cache = CacheStore()
    client = UniversalisClient(cache=cache)

    log_info("[STAGE] load recipes")
    all_recipes = load_recipes()
    all_recipes = dedupe_recipes_by_item_id(all_recipes)

    full_recipe_map = {r.item_id: r for r in all_recipes}

    log_info("[STAGE] select target recipes")
    target_recipes = all_recipes

    if args.item_ids:
        wanted = set(args.item_ids)
        target_recipes = [r for r in target_recipes if r.item_id in wanted]

    if args.limit_recipes and args.limit_recipes > 0:
        target_recipes = target_recipes[:args.limit_recipes]

    log_info("[STAGE] collect required market item ids")
    target_item_ids = [r.item_id for r in target_recipes]
    required_item_ids = collect_required_item_ids(target_item_ids, full_recipe_map)

    log_info(f"[INFO] target recipes: {len(target_recipes)}")
    log_info(f"[INFO] required market item ids: {len(required_item_ids)}")

    log_info("[STAGE] fetch market data")
    market_fetch_started = time.time()
    market_map = client.get_market_data_bulk(
        world=args.world,
        item_ids=sorted(required_item_ids),
        allow_fetch=True,
        allow_stale=False,
        with_meta=False,
    )
    log_info(f"[INFO] fetched market data in {time.time() - market_fetch_started:.2f}s")

    if args.debug_item_id is not None:
        log_info(f"[STAGE] debug item {args.debug_item_id}")
        log_info(f"[DEBUG] recipe tree for item_id={args.debug_item_id}")
        debug_recipe_cost(args.debug_item_id, full_recipe_map, market_map)
        log_info("[DEBUG] end of recipe tree")

        market_item = market_map.get(args.debug_item_id)
        log_info(f"[DEBUG] sell price explanation: {explain_sell_price(market_item)}")

    log_info("[STAGE] analyze opportunities")
    analyze_started = time.time()
    opportunities = analyze_opportunities(
        target_recipes,
        market_map,
        recipe_map=full_recipe_map,
    )
    log_info(f"[INFO] analyzed opportunities in {time.time() - analyze_started:.2f}s")

    log_info("[STAGE] diagnose filters")
    diagnose_filters(
        opportunities,
        min_profit=args.min_profit,
        min_sales_per_day=args.min_sales_per_day,
        max_listings=args.max_listings,
    )

    log_info("[STAGE] rank opportunities")
    ranked = rank_opportunities(
        opportunities,
        min_profit=args.min_profit,
        min_sales_per_day=args.min_sales_per_day,
        max_listings=args.max_listings,
        limit=args.limit,
    )

    if args.max_listings is not None:
        ranked = [x for x in ranked if x.listing_count <= args.max_listings]

    log_info("[STAGE] print result table")
    print_opportunities_table(ranked)


def run_item(args):
    started_at = time.time()

    log_info("[STAGE] init cache/client")
    cache = CacheStore()
    client = UniversalisClient(cache=cache)

    log_info("[STAGE] load recipes")
    all_recipes = load_recipes()
    all_recipes = dedupe_recipes_by_item_id(all_recipes)

    full_recipe_map = {r.item_id: r for r in all_recipes}

    log_info("[STAGE] select target recipe")
    target_recipes = [r for r in all_recipes if r.item_id == args.item_id]

    if not target_recipes:
        log_info(f"[ERROR] recipe not found for item_id={args.item_id}")
        return

    recipe = target_recipes[0]
    log_info(
        f"[INFO] target recipe: {recipe.item_name} "
        f"(item_id={recipe.item_id}, job={recipe.job}, level={recipe.level}, yield={recipe.yield_amount})"
    )

    log_info("[INFO] ingredients:")
    for ing in recipe.ingredients:
        log_info(f"  - {ing.item_name} ({ing.item_id}) x{ing.quantity}")

    log_info("[STAGE] collect required market item ids")
    target_item_ids = [r.item_id for r in target_recipes]
    required_item_ids = collect_required_item_ids(target_item_ids, full_recipe_map)

    log_info(f"[INFO] target recipes: {len(target_recipes)}")
    log_info(f"[INFO] required market item ids: {len(required_item_ids)}")

    log_info("[STAGE] fetch market data")
    market_fetch_started = time.time()
    market_map = client.get_market_data_bulk(
        world=args.world,
        item_ids=sorted(required_item_ids),
        allow_fetch=True,
        allow_stale=False,
        with_meta=False,
    )
    log_info(f"[INFO] fetched market data in {time.time() - market_fetch_started:.2f}s")

    log_info(f"[STAGE] debug item {args.item_id}")
    log_info(f"[DEBUG] recipe tree for item_id={args.item_id}")
    debug_recipe_cost(args.item_id, full_recipe_map, market_map)
    log_info("[DEBUG] end of recipe tree")

    market_item = market_map.get(args.item_id)
    log_info(f"[DEBUG] sell price explanation: {explain_sell_price(market_item)}")

    log_info("[STAGE] analyze opportunities")
    analyze_started = time.time()
    opportunities = analyze_opportunities(
        target_recipes,
        market_map,
        recipe_map=full_recipe_map,
    )
    log_info(f"[INFO] analyzed opportunities in {time.time() - analyze_started:.2f}s")

    if not opportunities:
        log_info(f"[ERROR] no opportunity generated for item_id={args.item_id}")
        return

    log_info("[STAGE] print item opportunities")
    for row in opportunities:
        print()
        print(f"Item ID: {row.item_id}")
        print(f"Item Name: {row.item_name}")
        print(f"Est Sell Price: {fmt_num(row.est_sell_price)}")
        print(f"Market Buy Price: {fmt_num(row.market_buy_price)}")
        print(f"Craft Cost (BuyAll): {fmt_num(row.craft_cost_buy_all)}")
        print(f"Craft Cost (Best): {fmt_num(row.craft_cost_best)}")
        print(f"Profit(BuyAll): {fmt_num(row.profit_buy_all)}")
        print(f"Profit(Best): {fmt_num(row.profit_best)}")
        print(f"Sales/Day: {fmt_num(row.sales_per_day)}")
        print(f"Listing Count: {fmt_num(row.listing_count)}")
        print(f"Score: {fmt_num(row.score)}")

    log_info(f"[DONE] item analyzed in {time.time() - started_at:.2f}s")



def run_refresh(args):
    started_at = time.time()
    started_at_iso = datetime.now(UTC).isoformat()
    done_items = 0

    cache = CacheStore()
    client = UniversalisClient(cache=cache)
    recipes = load_recipes()
    item_ids = [r.item_id for r in recipes]

    if getattr(args, "limit_items", None) is not None:
        item_ids = item_ids[:args.limit_items]

    total_items = len(item_ids)

    write_refresh_status(
        replace=True,
        status="running",
        world=args.world,
        started_at=started_at_iso,
        finished_at=None,
        done_items=0,
        total_items=total_items,
        progress=0.0,
        last_message=f"starting refresh ({total_items} items)",
        error=None,
    )

    try:
        client.refresh_market_data_bulk(world=args.world, item_ids=item_ids)

        done_items = total_items
        elapsed = time.time() - started_at

        write_refresh_status(
            status="success",
            world=args.world,
            started_at=started_at_iso,
            finished_at=datetime.now(UTC).isoformat(),
            done_items=done_items,
            total_items=total_items,
            progress=100.0,
            last_message=f"refreshed {done_items} items in {elapsed:.2f}s",
            error=None,
            elapsed_seconds=round(elapsed, 2),
        )

        print(f"Refreshed {done_items} items for {args.world}")

    except Exception as e:
        elapsed = time.time() - started_at

        write_refresh_status(
            status="failed",
            world=args.world,
            started_at=started_at_iso,
            finished_at=datetime.now(UTC).isoformat(),
            done_items=done_items,
            total_items=total_items,
            progress=round(done_items * 100.0 / total_items, 2) if total_items else 0.0,
            last_message="refresh failed",
            error=str(e),
            elapsed_seconds=round(elapsed, 2),
        )
        raise

def print_market_item_detail(data):
    if data is None:
        print("No market data.")
        return

    print(f"Item ID: {data.item_id}")
    print(f"Sales/Day: {data.regular_sale_velocity}")
    print(f"Current Avg Price: {data.current_average_price}")
    print(f"Listings: {len(data.listings)}")
    print(f"Recent Sales: {len(data.recent_sales)}")

    if data.listings:
        print("\n== Listings ==")
        for i, row in enumerate(data.listings[:20], 1):
            print(
                f"[{i}] price={row.price_per_unit} "
                f"qty={row.quantity} hq={getattr(row, 'hq', False)}"
            )

    if data.recent_sales:
        print("\n== Recent Sales ==")
        for i, row in enumerate(data.recent_sales[:20], 1):
            print(
                f"[{i}] sold={row.price_per_unit} "
                f"qty={row.quantity} hq={getattr(row, 'hq', False)} "
                f"ts={getattr(row, 'timestamp', None)}"
            )

def log_info(msg: str):
    if tqdm is not None:
        tqdm.write(msg)
    else:
        print(msg)


def run_build_high_value_candidates(args):
    started_at = time.time()

    log_info("[STAGE] init cache/client")
    cache = CacheStore()
    client = UniversalisClient(cache=cache)

    log_info("[STAGE] load all marketable items")
    items = load_marketable_items()
    log_info(f"[INFO] marketable items: {len(items)}")

    if args.limit_items is not None and args.limit_items > 0:
        items = items[:args.limit_items]
        log_info(f"[INFO] limited items for testing: {len(items)}")

    item_ids = [x.item_id for x in items]

    log_info("[STAGE] fetch market data for default world")
    market_map = client.get_market_data_bulk(
        world=args.world,
        item_ids=item_ids,
        allow_fetch=True,
        allow_stale=False,
        with_meta=False,
    )

    log_info("[STAGE] build candidate snapshot")
    rows = build_high_value_candidates(
        items=items,
        market_map=market_map,
        min_recent_sales=args.min_recent_sales,
        min_sales_per_day=args.min_sales_per_day,
        min_median_price=args.min_median_price,
    )

    save_high_value_candidates(rows)
    log_info(f"[INFO] candidates saved: {len(rows)}")
    log_info(f"[DONE] built candidates in {time.time() - started_at:.2f}s")


def run_scan_underpriced(args):
    started_at = time.time()

    log_info("[STAGE] init cache/client")
    cache = CacheStore()
    client = UniversalisClient(cache=cache)

    log_info("[STAGE] load high value candidates")
    candidates = load_high_value_candidates()
    log_info(f"[INFO] candidate items: {len(candidates)}")

    if args.limit_items is not None and args.limit_items > 0:
        candidates = candidates[:args.limit_items]
        log_info(f"[INFO] limited items for testing: {len(candidates)}")

    item_ids = [x.item_id for x in candidates]

    log_info("[STAGE] fetch default world history baseline")
    default_world_market_map = client.get_market_data_bulk(
        world=args.default_world,
        item_ids=item_ids,
        allow_fetch=True,
        allow_stale=False,
        with_meta=False,
    )

    log_info("[STAGE] fetch target world current listings")
    target_world_market_map = client.get_market_data_bulk(
        world=args.world,
        item_ids=item_ids,
        allow_fetch=True,
        allow_stale=False,
        with_meta=False,
    )

    log_info("[STAGE] analyze underpriced deals")
    rows = scan_underpriced_items(
        candidates=candidates,
        default_world_market_map=default_world_market_map,
        target_world_market_map=target_world_market_map,
        min_recent_sales=args.min_recent_sales,
        min_sales_per_day=args.min_sales_per_day,
    )

    log_info(f"[INFO] underpriced deals found: {len(rows)}")
    print_underpriced_deals_table(rows, limit=args.limit)
    log_info(f"[DONE] scanned underpriced deals in {time.time() - started_at:.2f}s")
