import asyncio
import json
import logging
import logging.handlers
import sys
import time
from threading import Thread
from typing import Dict, Any
from pathlib import Path

# Add project root to sys.path for direct execution
sys.path.append(str(Path(__file__).parent))


try:
    from config_manager import load_config
    from database import ProxyDatabase
    from proxy_checker import ProxyChecker
    from scraper import scrape_proxies
    from web_app import create_app
except ImportError as e:
    print(f"Import error: {e}. Ensure all modules are in the project directory.")
    sys.exit(1)

def setup_logging(log_file: str) -> None:
    handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10_000_000, backupCount=5, encoding='utf-8'
    )
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.DEBUG)  # Keep DEBUG for detailed logging
    logger.debug("Logging setup completed")

async def process_proxies(config: Dict[str, Any], checker: ProxyChecker, socketio) -> None:
    logger.debug("Starting process_proxies")
    db = checker.db
    all_proxies = db.load_proxies(config['proxy']['ttl'])
    logger.debug(f"Loaded {len(all_proxies)} proxies from database")
    
    try:
        new_proxies = await scrape_proxies(
            config['scraper']['urls'],
            config['scraper']['user_agent'],
            config['scraper']['timeout']
        )
        logger.info(f"Scraped {len(new_proxies)} new proxies")
    except Exception as e:
        logger.error(f"Scraping failed: {e}", exc_info=True)
        new_proxies = []
        logger.info("Continuing with database and backup proxies")

    try:
        with open(config['backup_proxies']['file'], 'r', encoding='utf-8') as f:
            backup_proxies = json.load(f)
            if not isinstance(backup_proxies, list):
                logger.warning("Backup proxies file contains invalid data")
                backup_proxies = []
            logger.info(f"Loaded {len(backup_proxies)} backup proxies")
            all_proxies.extend(backup_proxies)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.warning(f"Failed to load backup proxies: {e}")
        backup_proxies = []

    all_proxies.extend(new_proxies)
    unique_proxies = list({f"{p['ip_address']}:{p['port']}": p for p in all_proxies}.values())
    logger.info(f"Total unique proxies to check: {len(unique_proxies)}")

    if not unique_proxies:
        logger.warning("No proxies to check, skipping proxy check")
        return

    logger.debug("Starting proxy check")
    try:
        await checker.run(unique_proxies, socketio)
        logger.debug("Proxy check completed")
    except Exception as e:
        logger.error(f"Proxy check failed: {e}", exc_info=True)
    db.cleanup_old_proxies(config['proxy']['ttl'])
    logger.debug("Old proxies cleaned up")

async def periodic_check(config: Dict[str, Any], socketio) -> None:
    logger.debug("Initializing ProxyChecker")
    checker = ProxyChecker(config['proxy'], ProxyDatabase(config['database']['file']))
    while True:
        try:
            logger.info("Starting periodic proxy check")
            start_time = time.perf_counter()
            await process_proxies(config, checker, socketio)
            logger.info(f"Periodic check completed in {time.perf_counter() - start_time:.2f}s")
        except Exception as e:
            logger.error(f"Periodic check failed: {e}", exc_info=True)
        logger.debug("Sleeping for 30 minutes")
        await asyncio.sleep(1800)  # 30 minutes

def main():
    logger.debug("Starting main function")
    try:
        logger.debug("Loading configuration")
        config = load_config()
        logger.debug("Configuration loaded successfully")
        setup_logging(config['logging']['file'])
        
        logger.debug("Creating Flask app and SocketIO")
        app, socketio = create_app()
        logger.debug("Starting Flask thread")
        flask_thread = Thread(target=lambda: socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=False), daemon=True)
        flask_thread.start()
        
        logger.debug("Running periodic check")
        asyncio.run(periodic_check(config, socketio))
    except KeyboardInterrupt:
        logger.info("Program terminated by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Critical error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    # Set SelectorEventLoopPolicy on Windows to fix aiodns issue
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        logger.debug("Set WindowsSelectorEventLoopPolicy for aiodns compatibility")
    logger.debug("Program started")
    main()