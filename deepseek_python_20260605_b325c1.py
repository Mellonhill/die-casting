import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from contextlib import contextmanager
from loguru import logger
from config import settings

class PatentCache:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.cache_db_path
        self.ttl_seconds = settings.cache_ttl_hours * 3600
        self._init_db()
    
    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_cache (
                    key TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    expires_at TIMESTAMP NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS patents_cache (
                    patent_id TEXT PRIMARY KEY,
                    material TEXT NOT NULL,
                    data TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL
                )
            """)
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def get_api_result(self, key: str) -> Optional[List[Dict[str, Any]]]:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT data, expires_at FROM api_cache WHERE key = ?", (key,))
                row = cursor.fetchone()
                if row:
                    expires_at = datetime.fromisoformat(row["expires_at"])
                    if datetime.now() < expires_at:
                        return json.loads(row["data"])
                    else:
                        self._delete_key(key)
        except Exception as e:
            logger.error(f"Cache read error: {e}")
        return None
    
    def set_api_result(self, key: str, data: List[Dict[str, Any]]):
        try:
            now = datetime.now()
            expires_at = now + timedelta(seconds=self.ttl_seconds)
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO api_cache (key, data, created_at, expires_at) VALUES (?, ?, ?, ?)",
                    (key, json.dumps(data, default=str), now.isoformat(), expires_at.isoformat())
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Cache write error: {e}")
    
    def _delete_key(self, key: str):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM api_cache WHERE key = ?", (key,))
            conn.commit()

cache = PatentCache()