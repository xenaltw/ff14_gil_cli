from models import Recipe, RecipeIngredient


def load_demo_recipes():
    return [
        Recipe(
            item_id=36115,
            item_name="Grade 8 Tincture of Strength",
            job="ALC",
            level=90,
            yield_amount=3,
            ingredients=[
                RecipeIngredient(item_id=36088, quantity=1, item_name="Integral Armilla"),
                RecipeIngredient(item_id=36109, quantity=1, item_name="Lunar Adamantite Powder"),
            ],
        ),
        Recipe(
            item_id=44176,
            item_name="Claro Walnut Spinning Wheel",
            job="CRP",
            level=100,
            yield_amount=1,
            ingredients=[
                RecipeIngredient(item_id=44100, quantity=6, item_name="Claro Walnut Lumber"),
                RecipeIngredient(item_id=44120, quantity=2, item_name="Mythbrine Sand"),
            ],
        ),
    ]
