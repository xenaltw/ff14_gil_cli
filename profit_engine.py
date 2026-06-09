import math
from models import CraftOpportunity
import math
import statistics
from tqdm import tqdm


def _lowest_listing_price(market_item):
    if not market_item or not market_item.listings:
        return None

    prices = [x.price_per_unit for x in market_item.listings if x.price_per_unit > 0]
    if not prices:
        return None
    return float(min(prices))


def _estimate_sell_price(market_item):
    if market_item is None:
        return None

    lowest_listing = _lowest_listing_price(market_item)
    recent_prices = _recent_sale_prices(market_item)

    if recent_prices:
        recent_median = float(statistics.median(recent_prices))

        if len(recent_prices) >= 5:
            sell_price = recent_median
        else:
            sell_price = float(statistics.mean(recent_prices))

        if lowest_listing is not None and lowest_listing > recent_median * 3:
            return recent_median

        return sell_price

    return lowest_listing


def _estimate_sales_per_day(market_item):
    if market_item is None:
        return 0.0

    if market_item.regular_sale_velocity is not None:
        return float(market_item.regular_sale_velocity)

    return 0.0


def compute_buy_all_cost(recipe, market_map):
    total = 0.0

    for ing in recipe.ingredients:
        ing_market = market_map.get(ing.item_id)
        unit_cost = _lowest_listing_price(ing_market)

        if unit_cost is None:
            return math.inf

        total += unit_cost * ing.quantity

    if recipe.yield_amount > 0:
        total /= recipe.yield_amount

    return total


def compute_best_cost(item_id, recipe_map, market_map, memo=None, visiting=None):
    if memo is None:
        memo = {}
    if visiting is None:
        visiting = set()

    if item_id in memo:
        return memo[item_id]

    if item_id in visiting:
        return math.inf

    market_buy_price = _lowest_listing_price(market_map.get(item_id))
    recipe = recipe_map.get(item_id)

    if recipe is None:
        if market_buy_price is None:
            memo[item_id] = math.inf
            return math.inf

        memo[item_id] = market_buy_price
        return market_buy_price

    visiting.add(item_id)

    material_total = 0.0
    for ing in recipe.ingredients:
        ing_cost = compute_best_cost(
            ing.item_id,
            recipe_map,
            market_map,
            memo=memo,
            visiting=visiting,
        )

        if math.isinf(ing_cost):
            material_total = math.inf
            break

        material_total += ing_cost * ing.quantity

    visiting.remove(item_id)

    if math.isinf(material_total):
        craft_cost = math.inf
    else:
        craft_cost = material_total / recipe.yield_amount if recipe.yield_amount > 0 else material_total

    candidates = []
    if market_buy_price is not None:
        candidates.append(market_buy_price)
    if not math.isinf(craft_cost):
        candidates.append(craft_cost)

    if not candidates:
        best_cost = math.inf
    else:
        best_cost = min(candidates)

    memo[item_id] = best_cost
    return best_cost


def listing_bonus_penalty(listings: int) -> float:
    if listings == 0:
        return 8000.0
    if 1 <= listings <= 3:
        return 5000.0 - (listings - 1) * 1000.0  # 1:5000, 2:4000, 3:3000
    if 4 <= listings <= 5:
        return 1000.0

    if 6 <= listings <= 20:
        return - (listings - 5) * 200.0

    return - (3000.0 + (listings - 20) * 800.0)


def compute_score(profit_buy_all, sales_per_day, listing_count):
    base = profit_buy_all * 0.7 + sales_per_day * 1000
    return base + listing_bonus_penalty(listing_count)


def analyze_opportunities(recipes, market_map, recipe_map):
    results = []
    memo = {}

    for recipe in tqdm(recipes, desc="Analyze recipes", unit="recipe"):
        product_market = market_map.get(recipe.item_id)

        market_buy_price = _lowest_listing_price(product_market)
        est_sell_price = _estimate_sell_price(product_market)
        sales_per_day = _estimate_sales_per_day(product_market)
        listing_count = len(product_market.listings) if product_market else 0

        craft_cost_buy_all = compute_buy_all_cost(recipe, market_map)
        craft_cost_best = compute_best_cost(recipe.item_id, recipe_map, market_map, memo=memo)

        if est_sell_price is None:
            continue

        profit_buy_all = est_sell_price - craft_cost_buy_all if not math.isinf(craft_cost_buy_all) else -math.inf
        profit_best = est_sell_price - craft_cost_best if not math.isinf(craft_cost_best) else -math.inf

        score = compute_score(profit_buy_all, sales_per_day, listing_count)

        results.append(
            CraftOpportunity(
                item_id=recipe.item_id,
                item_name=recipe.item_name,
                market_buy_price=market_buy_price or 0.0,
                est_sell_price=est_sell_price,
                craft_cost_buy_all=craft_cost_buy_all,
                craft_cost_best=craft_cost_best,
                profit_buy_all=profit_buy_all,
                profit_best=profit_best,
                sales_per_day=sales_per_day,
                listing_count=listing_count,
                score=score,
            )
        )

    return results


def validate_opportunities(opportunities):
    bad_zero_best = []
    bad_best_gt_buyall = []
    bad_inf = []

    for x in opportunities:
        if x.craft_cost_best == 0 and x.craft_cost_buy_all > 0:
            bad_zero_best.append(x)

        if (
            not math.isinf(x.craft_cost_best)
            and not math.isinf(x.craft_cost_buy_all)
            and x.craft_cost_best > x.craft_cost_buy_all + 1e-6
        ):
            bad_best_gt_buyall.append(x)

        if math.isinf(x.craft_cost_best) or math.isinf(x.craft_cost_buy_all):
            bad_inf.append(x)

    print(f"[CHECK] zero best cost but buy-all > 0: {len(bad_zero_best)}")
    print(f"[CHECK] best cost > buy-all: {len(bad_best_gt_buyall)}")
    print(f"[CHECK] inf cost count: {len(bad_inf)}")

    for x in bad_zero_best[:10]:
        print("[ZERO_BEST]", x.item_id, x.item_name, x.craft_cost_buy_all, x.craft_cost_best)


def debug_recipe_cost(item_id, recipe_map, market_map, depth=0, visited=None):
    if visited is None:
        visited = set()

    indent = "  " * depth
    recipe = recipe_map.get(item_id)
    market_price = _lowest_listing_price(market_map.get(item_id))

    if recipe is None:
        print(f"{indent}- item {item_id}: no recipe, buy={market_price}, craft=N/A, chosen={market_price}")
        return math.inf if market_price is None else market_price

    if item_id in visited:
        print(f"{indent}- item {item_id}: cycle detected")
        return math.inf

    visiting_note = f"{indent}- item {item_id} {recipe.item_name}: buy={market_price}, yield={recipe.yield_amount}"
    print(visiting_note)

    visited.add(item_id)

    material_total = 0.0
    for ing in recipe.ingredients:
        ing_buy = _lowest_listing_price(market_map.get(ing.item_id))
        ing_recipe = recipe_map.get(ing.item_id)

        print(f"{indent}  ingredient {ing.item_id} {ing.item_name} x{ing.quantity}, direct_buy={ing_buy}, has_recipe={ing_recipe is not None}")

        ing_best = debug_recipe_cost(ing.item_id, recipe_map, market_map, depth + 1, visited)

        if math.isinf(ing_best):
            print(f"{indent}    -> chosen=INF (unresolved)")
            material_total = math.inf
            break

        subtotal = ing_best * ing.quantity
        print(f"{indent}    -> chosen_unit={ing_best}, subtotal={subtotal}")
        material_total += subtotal

    visited.remove(item_id)

    craft_cost = math.inf
    if not math.isinf(material_total):
        craft_cost = material_total / recipe.yield_amount if recipe.yield_amount > 0 else material_total

    candidates = []
    if market_price is not None:
        candidates.append(("buy", market_price))
    if not math.isinf(craft_cost):
        candidates.append(("craft", craft_cost))

    if not candidates:
        chosen_mode = "unresolved"
        best = math.inf
    else:
        chosen_mode, best = min(candidates, key=lambda x: x[1])

    print(f"{indent}  summary: buy={market_price}, craft={craft_cost}, chosen={chosen_mode}:{best}")
    return best


def _lowest_listing_price(market_item):
    if not market_item or not market_item.listings:
        return None

    prices = [x.price_per_unit for x in market_item.listings if x.price_per_unit > 0]
    if not prices:
        return None
    return float(min(prices))


def _recent_sale_prices(market_item):
    if not market_item or not market_item.recent_sales:
        return []

    return [
        x.price_per_unit
        for x in market_item.recent_sales
        if x.price_per_unit is not None and x.price_per_unit > 0
    ]


def explain_sell_price(market_item):
    lowest_listing = _lowest_listing_price(market_item)
    recent_prices = _recent_sale_prices(market_item)

    if not recent_prices:
        return {
            "mode": "lowest_listing_fallback",
            "lowest_listing": lowest_listing,
            "recent_count": 0,
            "recent_mean": None,
            "recent_median": None,
            "chosen": lowest_listing,
        }

    recent_mean = float(statistics.mean(recent_prices))
    recent_median = float(statistics.median(recent_prices))

    if len(recent_prices) >= 5:
        chosen = recent_median
        mode = "recent_median"
    else:
        chosen = recent_mean
        mode = "recent_mean"

    if lowest_listing is not None and lowest_listing > recent_median * 3:
        chosen = recent_median
        mode = "recent_median_guardrail"

    return {
        "mode": mode,
        "lowest_listing": lowest_listing,
        "recent_count": len(recent_prices),
        "recent_mean": recent_mean,
        "recent_median": recent_median,
        "chosen": chosen,
    }
