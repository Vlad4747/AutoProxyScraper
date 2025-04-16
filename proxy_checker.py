import asyncio
import aiohttp
import logging
import time
from typing import List, Dict, Any, Optional
from tqdm import tqdm
from database import ProxyDatabase
import ipaddress

logger = logging.getLogger(__name__)

class ProxyChecker:
    def __init__(self, config: Dict[str, Any], db: ProxyDatabase):
        self.test_url = config['test_url']
        self.max_workers = config['max_workers']
        self.request_timeout = config['request_timeout']
        self.max_delay_ms = config['max_delay_ms']
        self.ip_api_concurrency = config['ip_api_concurrency']
        self.db = db
        self.working_proxies: List[Dict[str, Any]] = []
        logger.debug("ProxyChecker initialized")

    def _validate_ip(self, ip: str) -> bool:
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            logger.debug(f"Invalid IP address: {ip}")
            return False

    async def _get_country(self, ip: str, session: aiohttp.ClientSession) -> str:
        async with asyncio.Semaphore(self.ip_api_concurrency):
            try:
                async with session.get(
                    f"http://ip-api.com/json/{ip}",
                    timeout=self.request_timeout
                ) as response:
                    logger.debug(f"IP API response for {ip}: {response.status}")
                    if response.status == 200:
                        data = await response.json()
                        return data.get("country", "Unknown") if data.get("status") == "success" else "Unknown"
                    logger.info(f"IP API returned status {response.status} for {ip}")
                    return "Unknown"
            except Exception as e:
                logger.info(f"Error fetching country for IP {ip}: {e}")
                return "Unknown"

    async def check_proxy(self, proxy: Dict[str, Any], session: aiohttp.ClientSession) -> Optional[Dict[str, Any]]:
        if not self._validate_ip(proxy['ip_address']):
            return None

        proxy_str = f"{proxy['ip_address']}:{proxy['port']}"
        proxy_url = f"http://{proxy_str}"
        logger.debug(f"Checking proxy {proxy_str}")

        try:
            start_time = time.perf_counter()
            async with session.get(
                self.test_url,
                proxy=proxy_url,
                timeout=self.request_timeout,
                ssl=False
            ) as response:
                elapsed_time = (time.perf_counter() - start_time) * 1000
                logger.debug(f"Response for {proxy_str}: {response.status}, Delay: {elapsed_time:.2f}ms")
                if response.status != 200 or elapsed_time > self.max_delay_ms:
                    logger.debug(f"Proxy {proxy_str} failed: Status {response.status}, Delay: {elapsed_time:.2f}ms")
                    return None

                data = await response.json()
                if not isinstance(data, dict) or 'origin' not in data:
                    logger.debug(f"Proxy {proxy_str} returned invalid JSON")
                    return None

                origin_ip = data['origin']
                anonymity = 'elite' if origin_ip != proxy['ip_address'] else 'transparent'
                country = await self._get_country(proxy['ip_address'], session)

                result = {
                    "ip_address": proxy['ip_address'],
                    "port": proxy['port'],
                    "delay_ms": elapsed_time,
                    "country": country,
                    "updated": time.time(),
                    "anonymity": anonymity,
                    "protocol": "http"
                }
                logger.info(f"Proxy {proxy_str} is working: Delay {elapsed_time:.2f}ms, Anonymity: {anonymity}")
                return result
        except (aiohttp.ClientProxyConnectionError, aiohttp.ClientResponseError, asyncio.TimeoutError) as e:
            logger.debug(f"Proxy {proxy_str} error: {e}")
            return None
        except Exception as e:
            logger.info(f"Unexpected error checking proxy {proxy_str}: {e}")
            return None

    async def run(self, proxies: List[Dict[str, Any]], socketio) -> None:
        logger.debug(f"Starting proxy check with {len(proxies)} proxies")
        if not proxies:
            logger.warning("No proxies to check")
            return

        self.working_proxies.clear()
        start_time = time.perf_counter()
        success_count = 0
        semaphore = asyncio.Semaphore(self.max_workers)

        async def check_with_semaphore(proxy: Dict[str, Any], session: aiohttp.ClientSession):
            async with semaphore:
                return await self.check_proxy(proxy, session)

        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(limit=self.max_workers)
        ) as session:
            tasks = [check_with_semaphore(proxy, session) for proxy in proxies]
            logger.debug(f"Created {len(tasks)} proxy check tasks")
            for i, future in enumerate(tqdm(
                asyncio.as_completed(tasks),
                total=len(proxies),
                desc="Checking proxies"
            )):
                result = await future
                if result:
                    self.working_proxies.append(result)
                    success_count += 1
                socketio.emit('progress_update', {
                    'current_step': i + 1,
                    'total_steps': len(proxies),
                    'working_proxies': len(self.working_proxies)
                })

        self.db.save_proxies(self.working_proxies)
        total_time = time.perf_counter() - start_time
        logger.info(f"Checked {len(proxies)} proxies in {total_time:.2f}s, Found {success_count} working")