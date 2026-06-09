import argparse

from config import DEFAULT_MIN_PROFIT, DEFAULT_MIN_SALES_PER_DAY, DEFAULT_WORLD, DEFAULT_LIMIT, DEFAULT_LIMIT_RECIPES
from commands import run_scan, run_item, run_refresh


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


if __name__ == "__main__":
    main()
