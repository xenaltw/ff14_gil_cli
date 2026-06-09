from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Listing:
    price_per_unit: float
    quantity: int
    hq: bool = False


@dataclass
class SaleEntry:
    price_per_unit: float
    quantity: int
    hq: bool = False
    timestamp: Optional[int] = None


@dataclass
class MarketItem:
    item_id: int
    listings: list[Listing] = field(default_factory=list)
    recent_sales: list[SaleEntry] = field(default_factory=list)
    current_average_price: Optional[float] = None
    regular_sale_velocity: Optional[float] = None


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
    market_buy_price: float
    est_sell_price: float
    craft_cost_buy_all: float
    craft_cost_best: float
    profit_buy_all: float
    profit_best: float
    sales_per_day: float
    listing_count: int
    score: float
