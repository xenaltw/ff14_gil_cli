import json
import sqlite3
import time

from config import CACHE_DB_PATH


class CacheStore:
    def __init__(self, db_path=CACHE_DB_PATH):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self._init_schema()

    def _init_schema(self):
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS market_cache (
            world TEXT NOT NULL,
            item_id INTEGER NOT NULL,
            payload TEXT NOT NULL,
            fetched_at INTEGER NOT NULL,
            PRIMARY KEY (world, item_id)
        )
        """)
        self.conn.commit()

    def get_market_json(self, world, item_id, ttl_seconds):
        row = self.conn.execute(
            "SELECT payload, fetched_at FROM market_cache WHERE world = ? AND item_id = ?",
            (world, item_id)
        ).fetchone()

        if row is None:
            return None

        payload, fetched_at = row
        if int(time.time()) - fetched_at > ttl_seconds:
            return None

        return json.loads(payload)

    def put_market_json(self, world, item_id, payload):
        self.conn.execute(
            """
            INSERT OR REPLACE INTO market_cache(world, item_id, payload, fetched_at)
            VALUES (?, ?, ?, ?)
            """,
            (world, item_id, json.dumps(payload), int(time.time()))
        )
        self.conn.commit()
