import requests
import hmac
import hashlib
import base64
import time
import json
import logging
from config import API_KEY, API_SECRET, BASE_URL

class ArkhamClient:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
    
    def get_auth_headers(self, method, path, body=''):
        timestamp = str(int((time.time() + 300) * 1_000_000))
        message = f"{API_KEY}{timestamp}{method}{path}{body}"
        
        secret_bytes = base64.b64decode(API_SECRET)
        signature = hmac.new(
            secret_bytes,
            message.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        signature_b64 = base64.b64encode(signature).decode('ascii')
        
        return {
            'Arkham-Api-Key': API_KEY,
            'Arkham-Expires': timestamp,
            'Arkham-Signature': signature_b64,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def get_trading_pairs(self):
        try:
            response = requests.get(f"{BASE_URL}/public/pairs")
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"Failed to get trading pairs: {response.text}")
                return []
        except Exception as e:
            self.logger.error(f"Error getting trading pairs: {e}")
            return []
    
    def get_ticker(self, symbol):
        try:
            response = requests.get(f"{BASE_URL}/public/ticker?symbol={symbol}")
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"Failed to get ticker: {response.text}")
                return None
        except Exception as e:
            self.logger.error(f"Error getting ticker: {e}")
            return None
    
    def get_balances(self):
        try:
            headers = self.get_auth_headers('GET', '/account/balances')
            response = requests.get(
                f"{BASE_URL}/account/balances",
                headers=headers
            )
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"Failed to get balances: {response.text}")
                return []
        except Exception as e:
            self.logger.error(f"Error getting balances: {e}")
            return []
            
    def place_order(self, symbol, side, order_type, size, price=None):
        try:
            path = '/orders/new'
            data = {
                "symbol": symbol,
                "side": side,
                "type": order_type,
                "size": str(size),
                "price": str(price) if price else "0",
                "postOnly": False
            }
            
            headers = self.get_auth_headers('POST', path, json.dumps(data))
            response = requests.post(
                f"{BASE_URL}{path}",
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"Failed to place order: {response.text}")
                return None
        except Exception as e:
            self.logger.error(f"Error placing order: {e}")
            return None
            
    def cancel_order(self, order_id):
        try:
            path = '/orders/cancel'
            data = {
                "orderId": order_id
            }
            
            headers = self.get_auth_headers('POST', path, json.dumps(data))
            response = requests.post(
                f"{BASE_URL}{path}",
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"Failed to cancel order: {response.text}")
                return None
        except Exception as e:
            self.logger.error(f"Error canceling order: {e}")
            return None