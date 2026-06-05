import time
import requests

from config import UNIVERSALIS_BASE_URL, REQUEST_TIMEOUT, CACHE_TTL_SECONDS, DEFAULT_BATCH_SIZE
from models import Listing, SaleEntry, MarketItemData


class UniversalisClient:
    def __init__(self, cache):
        self.cache = cache
        self.session = requests.Session()

    def _build_url(self, world: str, item_ids):
        joined = ",".join(str(x) for x in item_ids)
        return f"{UNIVERSALIS_BASE_URL}/{world}/{joined}"

    def get_market_data(self, world: str, item_id: int) -> MarketItemData:
        result = self.get_market_data_bulk(world, [item_id])
        return result[item_id]

    def get_market_data_bulk(self, world: str, item_ids):
        output = {}
        uncached = []

        for item_id in item_ids:
            cached = self.cache.get_market_json(world, item_id, CACHE_TTL_SECONDS)
            if cached is not None:
                output[item_id] = self._parse_item(world, item_id, cached)
            else:
                uncached.append(item_id)

        for i in range(0, len(uncached), DEFAULT_BATCH_SIZE):
            batch = uncached[i:i + DEFAULT_BATCH_SIZE]
            self._fetch_batch(world, batch, output)

        return output

    def refresh_market_data_bulk(self, world: str, item_ids):
        for i in range(0, len(item_ids), DEFAULT_BATCH_SIZE):
            batch = item_ids[i:i + DEFAULT_BATCH_SIZE]
            temp = {}
            self._fetch_batch(world, batch, temp)

    def _fetch_batch(self, world, batch, output):
        url = self._build_url(world, batch)
        resp = self.session.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        payload = resp.json()

        items = payload["items"] if "items" in payload else {str(batch[0]): payload}

        for item_id_str, item_json in items.items():
            item_id = int(item_id_str)
            self.cache.put_market_json(world, item_id, item_json)
            output[item_id] = self._parse_item(world, item_id, item_json)
            time.sleep(0.05)

    def _parse_item(self, world, item_id, raw):
        listings = [
            Listing(
                price_per_unit=x.get("pricePerUnit", 0),
                quantity=x.get("quantity", 0),
                hq=x.get("hq", False),
            )
            for x in raw.get("listings", [])
        ]

        recent_history = [
            SaleEntry(
                price_per_unit=x.get("pricePerUnit", 0),
                quantity=x.get("quantity", 0),
                timestamp=x.get("timestamp", 0),
                hq=x.get("hq", False),
            )
            for x in raw.get("recentHistory", [])
        ]

        return MarketItemData(
            item_id=item_id,
            world=world,
            listings=listings,
            recent_history=recent_history,
            current_average_price=raw.get("currentAveragePrice"),
            regular_sale_velocity=raw.get("regularSaleVelocity"),
            nq_sale_velocity=raw.get("nqSaleVelocity"),
            hq_sale_velocity=raw.get("hqSaleVelocity"),
        )
