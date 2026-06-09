from universalis_client import UniversalisClient
from cache_store import CacheStore
from recipe_source import load_recipes
from profit_engine import analyze_opportunities, debug_recipe_cost, explain_sell_price
from ranker import rank_opportunities, diagnose_filters
from output import print_opportunities_table
import time
from tqdm import tqdm


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

    if args.limit_recipes is not None:
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
    )

    log_info("[STAGE] rank opportunities")
    ranked = rank_opportunities(
        opportunities,
        min_profit=args.min_profit,
        min_sales_per_day=args.min_sales_per_day,
        limit=args.limit,
    )

    log_info("[STAGE] print result table")
    print_opportunities_table(ranked)


def run_item(args):
    cache = CacheStore()
    client = UniversalisClient(cache=cache)
    data = client.get_market_data(world=args.world, item_id=args.item_id)
    print_market_item_detail(data)


def run_refresh(args):
    cache = CacheStore()
    client = UniversalisClient(cache=cache)
    recipes = load_recipes()
    item_ids = [r.item_id for r in recipes]
    client.refresh_market_data_bulk(world=args.world, item_ids=item_ids)
    print(f"Refreshed {len(item_ids)} items for {args.world}")


def log_info(msg: str):
    if tqdm is not None:
        tqdm.write(msg)
    else:
        print(msg)
