import yaml
import logging
from typing import Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    if not Path(config_path).is_file():
        logger.error(f"Config file {config_path} not found")
        raise FileNotFoundError(f"Config file {config_path} not found")

    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
            required_sections = {
                'logging': ['file'],
                'database': ['file'],
                'proxy': ['test_url', 'max_workers', 'request_timeout', 'max_delay_ms', 'ttl', 'ip_api_concurrency'],
                'scraper': ['urls', 'user_agent', 'timeout'],
                'backup_proxies': ['file']
            }
            for section, keys in required_sections.items():
                if section not in config:
                    raise ValueError(f"Missing config section: {section}")
                for key in keys:
                    if key not in config[section]:
                        raise ValueError(f"Missing config key: {section}.{key}")
            return config
    except Exception as e:
        logger.error(f"Failed to load config {config_path}: {e}")
        raise