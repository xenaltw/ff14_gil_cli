from tabulate import tabulate


def print_opportunities_table(opportunities):
    rows = []
    for x in opportunities:
        rows.append([
            x.item_id,
            x.item_name,
            round(x.est_sell_price, 1),
            round(x.craft_cost, 1),
            round(x.gross_profit, 1),
            round(x.sales_per_day, 2),
            x.listing_count,
            round(x.score, 1),
        ])

    print(tabulate(
        rows,
        headers=[
            "Item ID", "Item Name", "Sell", "Cost", "Profit",
            "Sales/Day", "Listings", "Score"
        ],
        tablefmt="github"
    ))


def print_market_item_detail(data):
    print(f"Item ID: {data.item_id}")
    print(f"World: {data.world}")
    print(f"Current Avg Price: {data.current_average_price}")
    print(f"Regular Sale Velocity: {data.regular_sale_velocity}")
    print(f"Listings: {len(data.listings)}")
    print(f"Recent History Count: {len(data.recent_history)}")
