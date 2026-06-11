from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_URL = "https://github.com/thewakingsands/ffxiv-datamining-tc.git"
DEFAULT_REPO_DIR = Path("raw_data/ffxiv-datamining-tc")
DEFAULT_OUT_DIR = Path("data")


def run_cmd(cmd: list[str], cwd: Path | None = None) -> str:
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] command failed: {' '.join(cmd)}", file=sys.stderr)
        if e.stdout:
            print("[STDOUT]", e.stdout, file=sys.stderr)
        if e.stderr:
            print("[STDERR]", e.stderr, file=sys.stderr)
        raise


def ensure_repo(repo_url: str, repo_dir: Path, force_clone: bool = False) -> None:
    if force_clone and repo_dir.exists():
        shutil.rmtree(repo_dir)

    if not repo_dir.exists():
        repo_dir.parent.mkdir(parents=True, exist_ok=True)
        print(f"[INFO] cloning repo into {repo_dir}")
        run_cmd(["git", "clone", repo_url, str(repo_dir)])
        return

    git_dir = repo_dir / ".git"
    if not git_dir.exists():
        raise RuntimeError(f"{repo_dir} exists but is not a git repo")

    print(f"[INFO] pulling latest changes in {repo_dir}")
    run_cmd(["git", "pull"], cwd=repo_dir)


def safe_int(value, default=0):
    try:
        if value is None:
            return default
        s = str(value).strip()
        if s == "":
            return default
        return int(s)
    except (TypeError, ValueError):
        return default


def parse_bool(value) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def read_exd_csv_rows(csv_path: Path):
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)

        _row1 = next(reader)  # metadata index row
        row2 = next(reader)   # semantic header row
        _row3 = next(reader)  # type row

        dict_reader = csv.DictReader(f, fieldnames=row2)
        for row in dict_reader:
            yield row


def load_items(item_csv_path: Path):
    items = {}

    for row in read_exd_csv_rows(item_csv_path):
        item_id = safe_int(row.get("#"))
        if item_id <= 0:
            continue

        name = (row.get("Name") or "").strip()
        if not name:
            continue

        can_market = not parse_bool(row.get("IsUntradable"))

        items[item_id] = {
            "item_id": item_id,
            "name": name,
            "can_market": can_market,
        }

    return items


def load_craft_types(craft_type_csv_path: Path):
    craft_type_map = {}

    for row in read_exd_csv_rows(craft_type_csv_path):
        craft_type_id = safe_int(row.get("#"))
        if craft_type_id <= 0:
            continue

        craft_type_map[craft_type_id] = (row.get("Name") or "").strip()

    return craft_type_map


def load_recipe_levels(recipe_level_csv_path: Path):
    recipe_level_map = {}

    for row in read_exd_csv_rows(recipe_level_csv_path):
        recipe_level_id = safe_int(row.get("#"))
        if recipe_level_id <= 0:
            continue

        recipe_level_map[recipe_level_id] = safe_int(row.get("ClassJobLevel"))

    return recipe_level_map


def load_recipes(recipe_csv_path: Path, items_map, craft_type_map, recipe_level_map):
    recipes = []

    for row in read_exd_csv_rows(recipe_csv_path):
        recipe_id = safe_int(row.get("#"))
        result_item_id = safe_int(row.get("Item{Result}"))

        if recipe_id <= 0 or result_item_id <= 0:
            continue

        craft_type_id = safe_int(row.get("CraftType"))
        recipe_level_id = safe_int(row.get("RecipeLevelTable"))

        ingredients = []
        for i in range(8):
            ing_item_id = safe_int(row.get(f"Item{{Ingredient}}[{i}]"))
            ing_amount = safe_int(row.get(f"Amount{{Ingredient}}[{i}]"))

            if ing_item_id <= 0 or ing_amount <= 0:
                continue

            ing_info = items_map.get(ing_item_id, {})
            ingredients.append({
                "item_id": ing_item_id,
                "quantity": ing_amount,
                "item_name": ing_info.get("name", ""),
            })

        result_item = items_map.get(result_item_id, {})

        recipes.append({
            "recipe_id": recipe_id,
            "item_id": result_item_id,
            "item_name": result_item.get("name", ""),
            "job_id": craft_type_id,
            "job": craft_type_map.get(craft_type_id, ""),
            "recipe_level_id": recipe_level_id,
            "level": recipe_level_map.get(recipe_level_id, 0),
            "yield_amount": safe_int(row.get("Amount{Result}"), 1),
            "can_hq": parse_bool(row.get("CanHq")),
            "ingredients": ingredients,
        })

    return recipes


def write_json_outputs(items_map, recipes, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)

    items_out = out_dir / "items.json"
    recipes_out = out_dir / "recipes.json"

    normalized_items = {str(k): v for k, v in items_map.items()}

    with items_out.open("w", encoding="utf-8") as f:
        json.dump(normalized_items, f, ensure_ascii=False, indent=2)

    with recipes_out.open("w", encoding="utf-8") as f:
        json.dump(recipes, f, ensure_ascii=False, indent=2)

    print(f"[INFO] wrote {items_out}")
    print(f"[INFO] wrote {recipes_out}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Fetch FFXIV datamining CSVs and build local items/recipes JSON DB."
    )
    parser.add_argument("--repo-url", default=REPO_URL)
    parser.add_argument("--repo-dir", type=Path, default=DEFAULT_REPO_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--skip-fetch", action="store_true")
    parser.add_argument("--force-clone", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()

    if not args.skip_fetch:
        ensure_repo(args.repo_url, args.repo_dir, force_clone=args.force_clone)
    else:
        print("[INFO] skip-fetch enabled; using existing local repo")

    item_csv = args.repo_dir / "Item.csv"
    recipe_csv = args.repo_dir / "Recipe.csv"
    craft_type_csv = args.repo_dir / "CraftType.csv"
    recipe_level_csv = args.repo_dir / "RecipeLevelTable.csv"

    for path in [item_csv, recipe_csv, craft_type_csv, recipe_level_csv]:
        if not path.exists():
            raise FileNotFoundError(f"missing required csv: {path}")

    print("[INFO] loading items...")
    items_map = load_items(item_csv)

    print("[INFO] loading craft types...")
    craft_type_map = load_craft_types(craft_type_csv)

    print("[INFO] loading recipe levels...")
    recipe_level_map = load_recipe_levels(recipe_level_csv)

    print("[INFO] loading recipes...")
    recipes = load_recipes(recipe_csv, items_map, craft_type_map, recipe_level_map)

    print("[INFO] writing outputs...")
    write_json_outputs(items_map, recipes, args.out_dir)

    print(f"[INFO] total items loaded: {len(items_map)}")
    print(f"[INFO] total recipes loaded: {len(recipes)}")


if __name__ == "__main__":
    main()
