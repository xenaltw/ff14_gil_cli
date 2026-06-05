from universalis_client import UniversalisClient
from cache_store import CacheStore
from recipe_source import load_demo_recipes
from profit_engine import analyze_opportunities
from ranker import rank_opportunities
from output import print_opportunities_table, print_market_item_detail


def run_scan(args):
    cache = CacheStore()
    client = UniversalisClient(cache=cache)

    recipes = load_demo_recipes()
    item_ids = [r.item_id for r in recipes]

    market_map = client.get_market_data_bulk(world=args.world, item_ids=item_ids)
    opportunities = analyze_opportunities(recipes, market_map)
    ranked = rank_opportunities(
        opportunities,
        min_profit=args.min_profit,
        min_sales_per_day=args.min_sales_per_day,
        limit=args.limit,
    )
    print_opportunities_table(ranked)


def run_item(args):
    cache = CacheStore()
    client = UniversalisClient(cache=cache)
    data = client.get_market_data(world=args.world, item_id=args.item_id)
    print_market_item_detail(data)


def run_refresh(args):
    cache = CacheStore()
    client = UniversalisClient(cache=cache)
    recipes = load_demo_recipes()
    item_ids = [r.item_id for r in recipes]
    client.refresh_market_data_bulk(world=args.world, item_ids=item_ids)
    print(f"Refreshed {len(item_ids)} items for {args.world}")
