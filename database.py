import sqlite3
import logging
import time  # Added import for time
from typing import List, Dict, Any
from contextlib import contextmanager
from threading import Lock

logger = logging.getLogger(__name__)

class ProxyDatabase:
    def __init__(self, db_file: str, pool_size: int = 5):
        self.db_file = db_file
        self.pool_size = pool_size
        self.conn_pool: List[sqlite3.Connection] = []
        self.lock = Lock()
        self._init_db()

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS proxies
                            (ip_address TEXT, port INTEGER, delay_ms REAL, country TEXT, updated REAL,
                             anonymity TEXT, protocol TEXT, PRIMARY KEY (ip_address, port))''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_updated ON proxies(updated)')
            conn.commit()
            logger.debug("Database schema initialized")

    @contextmanager
    def _get_connection(self):
        with self.lock:
            if not self.conn_pool:
                conn = sqlite3.connect(self.db_file, check_same_thread=False)
                conn.row_factory = sqlite3.Row
                self.conn_pool.append(conn)
            conn = self.conn_pool.pop(0)
        
        try:
            yield conn
        finally:
            with self.lock:
                try:
                    conn.execute("SELECT 1")  # Check connection validity
                    self.conn_pool.append(conn)
                except sqlite3.Error:
                    logger.warning("Invalid connection, closing")
                    conn.close()

    def save_proxies(self, proxies: List[Dict[str, Any]]) -> None:
        if not proxies:
            logger.debug("No proxies to save")
            return
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.executemany(
                    '''INSERT OR REPLACE INTO proxies
                       (ip_address, port, delay_ms, country, updated, anonymity, protocol)
                       VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    [(p['ip_address'], p['port'], p['delay_ms'], p['country'], p['updated'],
                      p['anonymity'], p['protocol']) for p in proxies]
                )
                conn.commit()
                logger.info(f"Saved {len(proxies)} proxies to database")
            except sqlite3.Error as e:
                logger.error(f"Database error saving proxies: {e}")

    def load_proxies(self, ttl: float) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('SELECT * FROM proxies WHERE updated > ?', (time.time() - ttl,))
                proxies = [dict(row) for row in cursor.fetchall()]
                logger.info(f"Loaded {len(proxies)} proxies from database")
                return proxies
            except sqlite3.Error as e:
                logger.error(f"Database error loading proxies: {e}")
                return []

    def cleanup_old_proxies(self, ttl: float) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('DELETE FROM proxies WHERE updated < ?', (time.time() - ttl,))
                deleted = cursor.rowcount
                conn.commit()
                logger.info(f"Cleaned up {deleted} old proxies")
                return deleted
            except sqlite3.Error as e:
                logger.error(f"Database error cleaning up proxies: {e}")
                return 0