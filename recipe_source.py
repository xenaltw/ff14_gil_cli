import json
from pathlib import Path

from models import Recipe, RecipeIngredient


def load_items_map(json_path: str = "data/items.json"):
    path = Path(json_path)
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    items = {}
    for k, v in raw.items():
        item_id = int(k)
        items[item_id] = {
            "item_id": item_id,
            "name": v.get("name", ""),
        }
    return items


def load_recipes(json_path: str = "data/recipes.json"):
    path = Path(json_path)
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    recipes = []
    for row in raw:
        ingredients = [
            RecipeIngredient(
                item_id=int(x["item_id"]),
                quantity=int(x["quantity"]),
                item_name=x.get("item_name", ""),
            )
            for x in row.get("ingredients", [])
        ]

        recipes.append(
            Recipe(
                item_id=int(row["item_id"]),
                item_name=row.get("item_name", ""),
                job=row.get("job", ""),
                level=int(row.get("level", 0)),
                yield_amount=int(row.get("yield_amount", 1)),
                ingredients=ingredients,
            )
        )

    return recipes


def build_recipe_map(recipes):
    return {r.item_id: r for r in recipes}
