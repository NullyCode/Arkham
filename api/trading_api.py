import json
import requests
import logging
from decimal import Decimal
from urllib.parse import urlencode
from config.api_config import BASE_URL
from utils.auth import generate_auth_headers

logger = logging.getLogger(__name__)

def get_pair_info(symbol):
    """Get trading pair information including minimum sizes and price precision"""
    try:
        response = requests.get(f"{BASE_URL}/public/pair?symbol={symbol}")
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to get pair info: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error getting pair info: {e}")
        return None

def format_number(number, tick_size):
    """Format number according to tick size"""
    tick_decimals = abs(Decimal(str(tick_size)).as_tuple().exponent)
    return f"{{:.{tick_decimals}f}}".format(float(number))

def place_order(symbol, side, order_type, size, price=None):
    try:
        # Get pair info for minimum sizes and price precision
        pair_info = get_pair_info(symbol)
        if not pair_info:
            raise Exception("Could not get pair information")

        # Format size and price according to pair requirements
        min_size = Decimal(pair_info['minSize'])
        min_tick_price = Decimal(pair_info['minTickPrice'])
        min_notional = Decimal(pair_info['minNotional'])

        # Validate size
        size = Decimal(str(size))
        if size < min_size:
            raise Exception(f"Size {size} is below minimum {min_size}")

        # Format size according to lot size
        size = format_number(size, min_size)

        # Validate and format price for limit orders
        data = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "size": size,
            "postOnly": False
        }

        if price and order_type != 'market':
            price = Decimal(str(price))
            # Round price to valid tick size
            price = format_number(price, min_tick_price)
            data["price"] = price

            # Check minimum notional
            notional = Decimal(price) * Decimal(size)
            if notional < min_notional:
                raise Exception(f"Order notional {notional} is below minimum {min_notional}")

        path = '/orders/new'
        headers = generate_auth_headers('POST', path, json.dumps(data))
        
        logger.info(f"Placing order: {data}")
        response = requests.post(
            f"{BASE_URL}{path}",
            headers=headers,
            json=data
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to place order: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error placing order: {e}")
        return None

def cancel_order(order_id):
    try:
        path = '/orders/cancel'
        data = {
            "orderId": order_id
        }
        
        headers = generate_auth_headers('POST', path, json.dumps(data))
        response = requests.post(
            f"{BASE_URL}{path}",
            headers=headers,
            json=data
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to cancel order: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error canceling order: {e}")
        return None

def get_balances():
    try:
        path = '/account/balances'
        headers = generate_auth_headers('GET', path)
        response = requests.get(
            f"{BASE_URL}{path}",
            headers=headers
        )
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to get balances: {response.text}")
            return []
    except Exception as e:
        logger.error(f"Error getting balances: {e}")
        return []

def get_order_history(symbol=None, limit=100):
    try:
        path = '/orders/history'
        params = {}
        if symbol:
            params['symbol'] = symbol
        params['limit'] = limit
        
        query = f"?{urlencode(params)}" if params else ""
        headers = generate_auth_headers('GET', f"{path}{query}")
        
        response = requests.get(
            f"{BASE_URL}{path}",
            headers=headers,
            params=params
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to get order history: {response.text}")
            return []
    except Exception as e:
        logger.error(f"Error getting order history: {e}")
        return []

def get_active_orders(symbol=None):
    try:
        path = '/orders'
        params = {}
        if symbol:
            params['symbol'] = symbol
            
        query = f"?{urlencode(params)}" if params else ""
        headers = generate_auth_headers('GET', f"{path}{query}")
        
        response = requests.get(
            f"{BASE_URL}{path}",
            headers=headers,
            params=params
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to get active orders: {response.text}")
            return []
    except Exception as e:
        logger.error(f"Error getting active orders: {e}")
        return []