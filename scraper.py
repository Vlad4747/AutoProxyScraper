import asyncio
import aiohttp
import logging
from typing import List, Dict, Any
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

async def scrape_proxies(urls: List[str], user_agent: str, timeout: float) -> List[Dict[str, Any]]:
    logger.debug(f"Starting scrape_proxies with {len(urls)} URLs")
    headers = {'User-Agent': user_agent}
    all_proxies = []

    async def scrape_single(url: str) -> List[Dict[str, Any]]:
        proxies = []
        logger.debug(f"Scraping URL: {url}")
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers, timeout=timeout) as response:
                    logger.debug(f"Response status for {url}: {response.status}")
                    if response.status != 200:
                        logger.warning(f"Failed to fetch {url}: Status {response.status}")
                        return []
                    soup = BeautifulSoup(await response.text(), 'lxml')
                    table = soup.find('table')
                    if not table:
                        logger.warning(f"No proxy table found on {url}")
                        return []

                    for row in table.find_all('tr')[1:]:
                        cols = row.find_all('td')
                        if len(cols) >= 2:
                            try:
                                ip = cols[0].text.strip()
                                port = int(cols[1].text.strip())
                                proxies.append({"ip_address": ip, "port": port})
                            except ValueError as e:
                                logger.debug(f"Error parsing row on {url}: {e}")
                        await asyncio.sleep(0.05)  # Minimal delay to avoid rate-limiting
                    logger.info(f"Scraped {len(proxies)} proxies from {url}")
                    return proxies
            except Exception as e:
                logger.error(f"Error scraping {url}: {e}", exc_info=True)
                return []

    tasks = [scrape_single(url) for url in urls]
    logger.debug(f"Created {len(tasks)} scraping tasks")
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for result in results:
        if isinstance(result, list):
            all_proxies.extend(result)
        else:
            logger.error(f"Scrape task failed: {result}")

    logger.debug(f"Total proxies scraped: {len(all_proxies)}")
    return all_proxies