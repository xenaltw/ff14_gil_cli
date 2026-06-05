def rank_opportunities(opportunities, min_profit, min_sales_per_day, limit=20):
    filtered = [
        x for x in opportunities
        if x.gross_profit >= min_profit and x.sales_per_day >= min_sales_per_day
    ]
    filtered.sort(key=lambda x: x.score, reverse=True)
    return filtered[:limit]
