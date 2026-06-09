import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm


from config import (
    UNIVERSALIS_BASE_URL,
    CACHE_TTL_SECONDS,
    DEFAULT_BATCH_SIZE,
    REQUEST_TIMEOUT,
)
from models import MarketItem, Listing, SaleEntry


class UniversalisClient:
    def __init__(self, cache):
        self.cache = cache
        self.session = requests.Session()

        retry = Retry(
            total=3,
            connect=3,
            read=3,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _build_url(self, world: str, item_ids):
        joined = ",".join(str(x) for x in item_ids)
        return f"{UNIVERSALIS_BASE_URL}/{world}/{joined}"

    def get_market_data(self, world: str, item_id: int) -> MarketItem:
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

        tqdm.write(f"[INFO] cache hit: {len(output)}")
        tqdm.write(f"[INFO] cache miss: {len(uncached)}")

        batch_indexes = range(0, len(uncached), DEFAULT_BATCH_SIZE)

        for i in tqdm(batch_indexes, desc="Fetch market batches", unit="batch"):
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
        resp = self.session.get(url, timeout=(3, REQUEST_TIMEOUT))
        resp.raise_for_status()
        payload = resp.json()

        items = payload["items"] if "items" in payload else {str(batch[0]): payload}

        for item_id_str, item_json in items.items():
            item_id = int(item_id_str)
            self.cache.put_market_json(world, item_id, item_json)
            output[item_id] = self._parse_item(world, item_id, item_json)
            time.sleep(0.05)

    def _parse_item(self, world: str, item_id: int, raw: dict) -> MarketItem:
        listings = []
        for x in raw.get("listings", []):
            price = x.get("pricePerUnit")
            if price is None:
                continue

            listings.append(
                Listing(
                    price_per_unit=float(price),
                    quantity=int(x.get("quantity", 0)),
                    hq=bool(x.get("hq", False)),
                )
            )

        recent_sales = []
        for x in raw.get("recentHistory", []):
            price = x.get("pricePerUnit")
            if price is None:
                continue

            recent_sales.append(
                SaleEntry(
                    price_per_unit=float(price),
                    quantity=int(x.get("quantity", 0)),
                    hq=bool(x.get("hq", False)),
                    timestamp=x.get("timestamp"),
                )
            )

        current_average_price = raw.get("currentAveragePrice")
        regular_sale_velocity = raw.get("regularSaleVelocity")

        return MarketItem(
            item_id=item_id,
            listings=listings,
            recent_sales=recent_sales,
            current_average_price=(
                float(current_average_price)
                if current_average_price is not None
                else None
            ),
            regular_sale_velocity=(
                float(regular_sale_velocity)
                if regular_sale_velocity is not None
                else None
            ),
        )