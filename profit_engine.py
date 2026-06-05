from models import CraftOpportunity


def _lowest_listing_price(market_item):
    if not market_item or not market_item.listings:
        return 0
    return min(x.price_per_unit for x in market_item.listings if x.price_per_unit > 0)


def _estimate_sell_price(market_item):
    if market_item is None:
        return 0
    if market_item.current_average_price and market_item.current_average_price > 0:
        return market_item.current_average_price
    return _lowest_listing_price(market_item)


def _estimate_sales_per_day(market_item):
    if market_item is None:
        return 0.0
    if market_item.regular_sale_velocity is not None:
        return float(market_item.regular_sale_velocity)
    return 0.0


def analyze_opportunities(recipes, market_map):
    results = []

    for recipe in recipes:
        craft_cost = 0
        for ing in recipe.ingredients:
            ing_market = market_map.get(ing.item_id)
            unit_cost = _lowest_listing_price(ing_market)
            craft_cost += unit_cost * ing.quantity

        if recipe.yield_amount > 0:
            craft_cost = craft_cost / recipe.yield_amount

        product_market = market_map.get(recipe.item_id)
        est_sell_price = _estimate_sell_price(product_market)
        sales_per_day = _estimate_sales_per_day(product_market)
        listing_count = len(product_market.listings) if product_market else 0
        gross_profit = est_sell_price - craft_cost
        score = gross_profit * 0.7 + sales_per_day * 1000 - listing_count * 100

        results.append(
            CraftOpportunity(
                item_id=recipe.item_id,
                item_name=recipe.item_name,
                est_sell_price=est_sell_price,
                craft_cost=craft_cost,
                gross_profit=gross_profit,
                sales_per_day=sales_per_day,
                listing_count=listing_count,
                score=score,
            )
        )

    return results
