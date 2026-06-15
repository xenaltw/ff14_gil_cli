def rank_opportunities(
    opportunities,
    min_profit=0,
    min_sales_per_day=0,
    max_listings=None,
    limit=20,
):
    rows = []

    for row in opportunities:
        if row.profit_buy_all < min_profit:
            continue
        if row.sales_per_day < min_sales_per_day:
            continue
        if max_listings is not None and max_listings != 0 and row.listing_count > max_listings:
            continue
        rows.append(row)

    rows.sort(key=lambda x: x.score, reverse=True)

    if limit is not None and limit > 0:
        rows = rows[:limit]

    return rows

def diagnose_filters(
    opportunities,
    min_profit=0,
    min_sales_per_day=0,
    max_listings=None,
):
    total = len(opportunities)
    fail_profit = 0
    fail_sales = 0
    fail_listings = 0
    passed = 0

    for row in opportunities:
        blocked = False

        if row.profit_buy_all < min_profit:
            fail_profit += 1
            blocked = True

        if row.sales_per_day < min_sales_per_day:
            fail_sales += 1
            blocked = True

        if max_listings is not None and max_listings != 0 and row.listing_count > max_listings:
            fail_listings += 1
            blocked = True

        if not blocked:
            passed += 1

    print(f"[DIAG] total opportunities: {total}")
    print(f"[DIAG] fail profit < {min_profit}: {fail_profit}")
    print(f"[DIAG] fail sales/day < {min_sales_per_day}: {fail_sales}")
    if max_listings is not None and max_listings != 0:
        print(f"[DIAG] fail listings > {max_listings}: {fail_listings}")
    print(f"[DIAG] passed all filters: {passed}")
