from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Listing:
    price_per_unit: int
    quantity: int
    hq: bool = False


@dataclass
class SaleEntry:
    price_per_unit: int
    quantity: int
    timestamp: int
    hq: bool = False


@dataclass
class MarketItemData:
    item_id: int
    world: str
    listings: List[Listing] = field(default_factory=list)
    recent_history: List[SaleEntry] = field(default_factory=list)
    current_average_price: Optional[float] = None
    regular_sale_velocity: Optional[float] = None
    nq_sale_velocity: Optional[float] = None
    hq_sale_velocity: Optional[float] = None


@dataclass
class RecipeIngredient:
    item_id: int
    quantity: int
    item_name: str = ""


@dataclass
class Recipe:
    item_id: int
    item_name: str
    job: str
    level: int
    yield_amount: int
    ingredients: List[RecipeIngredient] = field(default_factory=list)


@dataclass
class CraftOpportunity:
    item_id: int
    item_name: str
    est_sell_price: float
    craft_cost: float
    gross_profit: float
    sales_per_day: float
    listing_count: int
    score: float
