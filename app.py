from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI, Form, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config import (
    DEFAULT_MIN_PROFIT,
    DEFAULT_MIN_SALES_PER_DAY,
    DEFAULT_WORLD,
    DEFAULT_LIMIT,
    DEFAULT_LIMIT_RECIPES,
)
from commands import (
    run_refresh,
    dedupe_recipes_by_item_id,
    collect_required_item_ids,
)
from cache_store import CacheStore
from universalis_client import UniversalisClient
from recipe_source import load_recipes
from profit_engine import analyze_opportunities
from ranker import rank_opportunities
from refresh_status import read_refresh_status
import math


app = FastAPI(title="FF14 Gil CLI Web")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def scan_data(
    world: str,
    min_profit: float,
    min_sales_per_day: float,
    limit: int,
    limit_recipes: int | None = None,
    item_ids: list[int] | None = None,
):
    cache = CacheStore()
    client = UniversalisClient(cache=cache)

    all_recipes = load_recipes()
    all_recipes = dedupe_recipes_by_item_id(all_recipes)
    full_recipe_map = {r.item_id: r for r in all_recipes}

    target_recipes = all_recipes

    if item_ids:
        wanted = set(item_ids)
        target_recipes = [r for r in target_recipes if r.item_id in wanted]

    if limit_recipes and limit_recipes > 0:
        target_recipes = target_recipes[:limit_recipes]

    target_item_ids = [r.item_id for r in target_recipes]
    required_item_ids = collect_required_item_ids(target_item_ids, full_recipe_map)

    market_entries = client.get_market_data_bulk(
        world=world,
        item_ids=sorted(required_item_ids),
        allow_fetch=False,
        allow_stale=True,
        with_meta=True,
    )

    market_map = {item_id: x["payload"] for item_id, x in market_entries.items()}

    market_meta = {
        item_id: {
            "fetched_at": x["fetched_at"],
            "age_seconds": x["age_seconds"],
            "is_expired": x["is_expired"],
        }
        for item_id, x in market_entries.items()
    }

    opportunities = analyze_opportunities(
        target_recipes,
        market_map,
        recipe_map=full_recipe_map,
    )

    ranked = rank_opportunities(
        opportunities,
        min_profit=min_profit,
        min_sales_per_day=min_sales_per_day,
        limit=limit,
    )

    debug_rows = sorted(
        opportunities,
        key=lambda x: (
            float("-inf")
            if (isinstance(x.profit_buy_all, float) and math.isnan(x.profit_buy_all))
            else x.profit_buy_all
        ),
        reverse=True,
    )[:20]

    stats = {
        "target_recipes": len(target_recipes),
        "required_item_ids": len(required_item_ids),
        "cached_market_items": len(market_map),
        "fresh_market_items": sum(1 for x in market_entries.values() if not x["is_expired"]),
        "stale_market_items": sum(1 for x in market_entries.values() if x["is_expired"]),
        "opportunities": len(opportunities),
        "ranked": len(ranked),
        "neg_inf_profit": sum(
            1 for x in opportunities
            if math.isinf(x.profit_buy_all) and x.profit_buy_all < 0
        ),
        "nan_sales": sum(
            1 for x in opportunities
            if isinstance(x.sales_per_day, float) and math.isnan(x.sales_per_day)
        ),
        "pass_profit": sum(
            1 for x in opportunities
            if x.profit_buy_all >= min_profit
        ),
        "pass_sales": sum(
            1 for x in opportunities
            if x.sales_per_day >= min_sales_per_day
        ),
        "pass_both": sum(
            1 for x in opportunities
            if x.profit_buy_all >= min_profit and x.sales_per_day >= min_sales_per_day
        ),
    }

    return {
        "rows": ranked,
        "debug_rows": debug_rows,
        "stats": stats,
    }


@app.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    world: str = Query(DEFAULT_WORLD),
    min_profit: float = Query(DEFAULT_MIN_PROFIT),
    min_sales_per_day: float = Query(DEFAULT_MIN_SALES_PER_DAY),
    limit: int = Query(DEFAULT_LIMIT),
    limit_recipes: int | None = Query(DEFAULT_LIMIT_RECIPES),
):
    result = scan_data(
        world=world,
        min_profit=min_profit,
        min_sales_per_day=min_sales_per_day,
        limit=limit,
        limit_recipes=limit_recipes,
    )

    rows = result["rows"]
    debug_rows = result["debug_rows"]
    stats = result["stats"]

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "request": request,
            "rows": rows,
            "debug_rows": debug_rows,
            "stats": stats,
            "world": world,
            "min_profit": min_profit,
            "min_sales_per_day": min_sales_per_day,
            "limit": limit,
            "limit_recipes": limit_recipes,
        },
    )


@app.get("/api/scan")
def api_scan(
    world: str = Query(DEFAULT_WORLD),
    min_profit: float = Query(DEFAULT_MIN_PROFIT),
    min_sales_per_day: float = Query(DEFAULT_MIN_SALES_PER_DAY),
    limit: int = Query(DEFAULT_LIMIT),
    limit_recipes: int | None = Query(DEFAULT_LIMIT_RECIPES),
):
    result = scan_data(...)
    rows = result["rows"]

    return JSONResponse(
        {
            "rows": [
                {
                    "item_id": r.item_id,
                    "item_name": r.item_name,
                    "market_buy_price": r.market_buy_price,
                    "est_sell_price": r.est_sell_price,
                    "craft_cost_buy_all": r.craft_cost_buy_all,
                    "craft_cost_best": r.craft_cost_best,
                    "profit_buy_all": r.profit_buy_all,
                    "profit_best": r.profit_best,
                    "sales_per_day": r.sales_per_day,
                    "listing_count": r.listing_count,
                    "score": r.score,
                }
                for r in rows
            ],
            "stats": result["stats"],
        }
    )


@app.post("/refresh")
def refresh_now(world: str = Form(DEFAULT_WORLD)):
    args = SimpleNamespace(world=world)
    run_refresh(args)
    return RedirectResponse(url=f"/?world={world}", status_code=303)

@app.get("/api/refresh-status")
def api_refresh_status():
    return read_refresh_status()
