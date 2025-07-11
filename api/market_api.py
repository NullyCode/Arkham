import requests
import logging
from config.api_config import BASE_URL

logger = logging.getLogger(__name__)

def get_trading_pairs():
    try:
        response = requests.get(f"{BASE_URL}/public/pairs")
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to get trading pairs: {response.text}")
            return []
    except Exception as e:
        logger.error(f"Error getting trading pairs: {e}")
        return []

def get_ticker(symbol):
    try:
        response = requests.get(f"{BASE_URL}/public/ticker?symbol={symbol}")
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to get ticker: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error getting ticker: {e}")
        return None