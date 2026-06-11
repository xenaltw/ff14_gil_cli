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
from refresh_status import write_refresh_status

class UniversalisClient:
    def __init__(self, cache=None, ttl_seconds=CACHE_TTL_SECONDS):
        self.cache = cache
        self.session = requests.Session()
        self.ttl_seconds = ttl_seconds

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

    def get_market_data(
        self,
        world: str,
        item_id: int,
        allow_fetch: bool = True,
        allow_stale: bool = False,
        with_meta: bool = False,
    ):
        entry = self.cache.get_market_entry(world, item_id, self.ttl_seconds)

        if entry is not None:
            if not entry["is_expired"] or allow_stale:
                print("[DEBUG] cache hit")
                print("[DEBUG] cached payload keys:", list(entry["payload"].keys())[:50])

                parsed = self._parse_item(world, item_id, entry["payload"])

                if with_meta:
                    return {
                        "payload": parsed,
                        "fetched_at": entry["fetched_at"],
                        "age_seconds": entry["age_seconds"],
                        "is_expired": entry["is_expired"],
                    }
                return parsed

        if not allow_fetch:
            return None

        raw_payload = self._fetch_batch_raw(world, [item_id]).get(item_id)
        print("[DEBUG] fetched raw is None =", raw_payload is None)
        if raw_payload:
            print("[DEBUG] fetched payload keys:", list(raw_payload.keys())[:50])
            print("[DEBUG] listings len:", len(raw_payload.get("listings", [])))
            print("[DEBUG] recentHistory len:", len(raw_payload.get("recentHistory", [])))
            print("[DEBUG] regularSaleVelocity:", raw_payload.get("regularSaleVelocity"))
            print("[DEBUG] itemID:", raw_payload.get("itemID"))

        if raw_payload is None:
            return None

        self.cache.put_market_json(world, item_id, raw_payload)

        entry = self.cache.get_market_entry(world, item_id, self.ttl_seconds)
        parsed = self._parse_item(world, item_id, raw_payload)

        if with_meta:
            return {
                "payload": parsed,
                "fetched_at": entry["fetched_at"] if entry else None,
                "age_seconds": entry["age_seconds"] if entry else 0,
                "is_expired": entry["is_expired"] if entry else False,
            }

        return parsed

    def get_market_data_bulk(
        self,
        world: str,
        item_ids,
        allow_fetch: bool = True,
        allow_stale: bool = False,
        with_meta: bool = False,
    ):
        output = {}
        uncached = []
        fresh_hits = 0
        stale_hits = 0
        misses = 0

        for item_id in item_ids:
            entry = self.cache.get_market_entry(world, item_id, self.ttl_seconds)

            if entry is None:
                uncached.append(item_id)
                misses += 1
                continue

            if entry["is_expired"] and not allow_stale:
                uncached.append(item_id)
                misses += 1
                continue

            parsed = self._parse_item(world, item_id, entry["payload"])

            if entry["is_expired"]:
                stale_hits += 1
            else:
                fresh_hits += 1

            if with_meta:
                output[item_id] = {
                    "payload": parsed,
                    "fetched_at": entry["fetched_at"],
                    "age_seconds": entry["age_seconds"],
                    "is_expired": entry["is_expired"],
                }
            else:
                output[item_id] = parsed

        tqdm.write(f"[INFO] fresh cache hit: {fresh_hits}")
        tqdm.write(f"[INFO] stale cache hit: {stale_hits}")
        tqdm.write(f"[INFO] cache miss: {misses}")

        if not allow_fetch or not uncached:
            return output

        with tqdm(total=len(uncached), desc="[FETCH]", unit="item", leave=True) as pbar:
            for start in range(0, len(uncached), DEFAULT_BATCH_SIZE):
                batch = uncached[start:start + DEFAULT_BATCH_SIZE]
                fetched_raw = self._fetch_batch_raw(world, batch)

                for item_id, raw_payload in fetched_raw.items():
                    self.cache.put_market_json(world, item_id, raw_payload)
                    entry = self.cache.get_market_entry(world, item_id, self.ttl_seconds)
                    parsed = self._parse_item(world, item_id, raw_payload)

                    if with_meta:
                        output[item_id] = {
                            "payload": parsed,
                            "fetched_at": entry["fetched_at"] if entry else None,
                            "age_seconds": entry["age_seconds"] if entry else 0,
                            "is_expired": entry["is_expired"] if entry else False,
                        }
                    else:
                        output[item_id] = parsed

                pbar.update(len(batch))

        return output

    def refresh_market_data_bulk(self, world: str, item_ids):
        total_items = len(item_ids)
        done_items = 0
        batch_total = (total_items + DEFAULT_BATCH_SIZE - 1) // DEFAULT_BATCH_SIZE

        for batch_no, i in enumerate(range(0, total_items, DEFAULT_BATCH_SIZE), start=1):
            batch = item_ids[i:i + DEFAULT_BATCH_SIZE]
            self._fetch_batch(world, batch, output={})
            done_items += len(batch)

            write_refresh_status(
                status="running",
                world=world,
                done_items=done_items,
                total_items=total_items,
                progress=round(done_items * 100.0 / total_items, 2) if total_items else 100.0,
                batch_done=batch_no,
                batch_total=batch_total,
                last_message=f"refreshed batch {batch_no}/{batch_total}",
                error=None,
            )

            print(f"[REFRESH] world={world} progress={done_items}/{total_items} batch={batch_no}/{batch_total}")

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
    def _fetch_batch_raw(self, world, batch):
        url = self._build_url(world, batch)
        resp = self.session.get(url, timeout=(3, REQUEST_TIMEOUT))
        resp.raise_for_status()
        payload = resp.json()

        items = payload["items"] if "items" in payload else {str(batch[0]): payload}

        output = {}
        for item_id_str, item_json in items.items():
            item_id = int(item_id_str)
            output[item_id] = item_json
            time.sleep(0.05)

        return output

