def rank_opportunities(opportunities, min_profit, min_sales_per_day, limit=20):
    filtered = [
        x for x in opportunities
        if x.profit_buy_all >= min_profit and x.sales_per_day >= min_sales_per_day
    ]
    filtered.sort(key=lambda x: x.score, reverse=True)
    return filtered[:limit]


def diagnose_filters(opportunities, min_profit, min_sales_per_day):
    profit_ok = [x for x in opportunities if x.profit_buy_all >= min_profit]
    sales_ok = [x for x in opportunities if x.sales_per_day >= min_sales_per_day]
    both_ok = [
        x for x in opportunities
        if x.profit_buy_all >= min_profit and x.sales_per_day >= min_sales_per_day
    ]

    print(f"[INFO] opportunities total: {len(opportunities)}")
    print(f"[INFO] profit-qualified: {len(profit_ok)}")
    print(f"[INFO] sales-qualified: {len(sales_ok)}")
    print(f"[INFO] both-qualified: {len(both_ok)}")