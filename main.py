import argparse

from config import DEFAULT_MIN_PROFIT, DEFAULT_MIN_SALES_PER_DAY, DEFAULT_WORLD, DEFAULT_LIMIT, DEFAULT_LIMIT_RECIPES
from commands import run_scan, run_item, run_refresh
from commands import (
    run_scan,
    run_item,
    run_refresh,
    run_build_high_value_candidates,
    run_scan_underpriced,
)


def build_parser():
    parser = argparse.ArgumentParser(
        prog="ff14-gil-cli",
        description="Scan FF14 market data and rank profitable craftable items."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="Scan market and rank craft opportunities")
    scan_parser.add_argument("--world", default=DEFAULT_WORLD)
    scan_parser.add_argument("--min-profit", type=float, default=DEFAULT_MIN_PROFIT)
    scan_parser.add_argument("--min-sales-per-day", type=float, default=DEFAULT_MIN_SALES_PER_DAY)
    scan_parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    scan_parser.add_argument("--limit-recipes", type=int, default=DEFAULT_LIMIT_RECIPES)
    scan_parser.add_argument("--item-ids", nargs="+", type=int, default=None)
    scan_parser.add_argument("--debug-item-id", type=int, default=None)

    item_parser = subparsers.add_parser("item", help="Inspect one item")
    item_parser.add_argument("item_id", type=int)
    item_parser.add_argument("--world", default=DEFAULT_WORLD)

    refresh_parser = subparsers.add_parser("refresh", help="Refresh cached market data")
    refresh_parser.add_argument("--world", default=DEFAULT_WORLD)
    refresh_parser.add_argument("--limit-items", type=int, default=None, help="Only refresh the first N items for testing")

    build_candidates_parser = subparsers.add_parser(
        "build-high-value-candidates",
        help="Build high-value item candidates from all marketable items",
    )
    build_candidates_parser.add_argument("--world", default=DEFAULT_WORLD)
    build_candidates_parser.add_argument("--min-median-price", type=float, default=10000.0)
    build_candidates_parser.add_argument("--min-recent-sales", type=int, default=5)
    build_candidates_parser.add_argument("--min-sales-per-day", type=float, default=0.1)
    build_candidates_parser.add_argument("--limit-items", type=int, default=None)

    scan_underpriced_parser = subparsers.add_parser(
        "scan-underpriced",
        help="Scan underpriced deals from candidate snapshot",
    )
    scan_underpriced_parser.add_argument("--default-world", default=DEFAULT_WORLD)
    scan_underpriced_parser.add_argument("--world", default="陸行鳥")
    scan_underpriced_parser.add_argument("--min-recent-sales", type=int, default=5)
    scan_underpriced_parser.add_argument("--min-sales-per-day", type=float, default=0.1)
    scan_underpriced_parser.add_argument("--limit", type=int, default=20)
    scan_underpriced_parser.add_argument("--limit-items", type=int, default=None)


    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "scan":
        run_scan(args)
    elif args.command == "item":
        run_item(args)
    elif args.command == "refresh":
        run_refresh(args)
    elif args.command == "build-high-value-candidates":
        run_build_high_value_candidates(args)
    elif args.command == "scan-underpriced":
        run_scan_underpriced(args)



if __name__ == "__main__":
    main()
