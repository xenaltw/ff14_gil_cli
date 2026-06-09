from tabulate import tabulate
from wcwidth import wcswidth


def display_width(text: str) -> int:
    width = wcswidth(text)
    return width if width >= 0 else len(text)


def pad_left(text: str, width: int) -> str:
    text = str(text)
    pad = max(0, width - display_width(text))
    return " " * pad + text


def pad_right(text: str, width: int) -> str:
    text = str(text)
    pad = max(0, width - display_width(text))
    return text + " " * pad


def fmt_num(value):
    if value == float("inf"):
        return "inf"
    if value == float("-inf"):
        return "-inf"
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value:.1f}"
    return str(value)


def print_opportunities_table(opportunities):
    headers = [
        "Item ID",
        "Item Name",
        "Sell",
        "Buy",
        "Craft(BuyAll)",
        "Craft(Best)",
        "Profit(BuyAll)",
        "Profit(Best)",
        "Sales/Day",
        "Listings",
        "Score",
    ]

    rows = []
    for o in opportunities:
        rows.append([
            str(o.item_id),
            o.item_name,
            fmt_num(o.est_sell_price),
            fmt_num(o.market_buy_price),
            fmt_num(o.craft_cost_buy_all),
            fmt_num(o.craft_cost_best),
            fmt_num(o.profit_buy_all),
            fmt_num(o.profit_best),
            fmt_num(o.sales_per_day),
            fmt_num(o.listing_count),
            fmt_num(o.score),
        ])

    col_widths = []
    for col_idx, header in enumerate(headers):
        max_width = display_width(header)
        for row in rows:
            max_width = max(max_width, display_width(row[col_idx]))
        col_widths.append(max_width)

    numeric_cols = {0, 2, 3, 4, 5, 6, 7, 8, 9, 10}

    def format_row(row):
        out = []
        for i, cell in enumerate(row):
            if i in numeric_cols:
                out.append(pad_left(cell, col_widths[i]))
            else:
                out.append(pad_right(cell, col_widths[i]))
        return "| " + " | ".join(out) + " |"

    header_line = format_row(headers)
    separator = "|-" + "-|-".join("-" * w for w in col_widths) + "-|"

    print(header_line)
    print(separator)
    for row in rows:
        print(format_row(row))


def print_market_item_detail(data):
    print(f"Item ID: {data.item_id}")
    print(f"World: {data.world}")
    print(f"Current Avg Price: {data.current_average_price}")
    print(f"Regular Sale Velocity: {data.regular_sale_velocity}")
    print(f"Listings: {len(data.listings)}")
    print(f"Recent History Count: {len(data.recent_history)}")
