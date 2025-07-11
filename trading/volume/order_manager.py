import logging
import time
from decimal import Decimal
from api.trading_api import place_order, cancel_order, get_active_orders, get_order_history
from .order_status import (
    OrderStatus, 
    create_insufficient_balance_status,
    create_placement_failed_status,
    create_assumed_complete_status,
    is_valid_order
)

class OrderManager:
    def __init__(self, symbol):
        self.logger = logging.getLogger(__name__)
        self.symbol = symbol
        self.retry_interval = 3
        self.max_retries = 5
        self.fail_threshold = 5

    def place_market_sell(self, size):
        """Place a market sell order with retries"""
        fail_count = 0
        
        for attempt in range(self.max_retries):
            try:
                sell_order = place_order(
                    symbol=self.symbol,
                    side='sell',
                    order_type='limitGtc',
                    size=str(size)
                )
                
                if sell_order and is_valid_order(sell_order):
                    self.logger.info(f"Placed market sell order: {sell_order}")
                    return sell_order
                
                fail_count += 1
                self.logger.error(f"Failed to place market sell order (attempt {attempt + 1})")
                
                if fail_count >= self.fail_threshold:
                    return create_assumed_complete_status()
                    
            except Exception as e:
                self.logger.error(f"Error placing market sell order (attempt {attempt + 1}): {e}")
                fail_count += 1
                
                if fail_count >= self.fail_threshold:
                    return create_placement_failed_status(fail_count, str(e))
            
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_interval)
                
        return create_placement_failed_status(fail_count, "Max retries exceeded")

    def place_limit_sell(self, size, price):
        """Place a limit sell order with retries"""
        fail_count = 0
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                sell_order = place_order(
                    symbol=self.symbol,
                    side='sell',
                    order_type='limitGtc',
                    size=str(size),
                    price=price
                )
                
                if sell_order and is_valid_order(sell_order):
                    self.logger.info(f"Placed limit sell order: price={price}")
                    return sell_order
                
                fail_count += 1
                self.logger.error(f"Failed to place limit sell order (attempt {attempt + 1})")
                
                if "insufficient balance" in str(last_error):
                    return create_insufficient_balance_status(
                        available=float(str(last_error).split("has ")[1].split(" ")[0]),
                        required=float(size)
                    )
                    
            except Exception as e:
                last_error = e
                self.logger.error(f"Error placing limit sell order (attempt {attempt + 1}): {e}")
                fail_count += 1
            
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_interval)
                
        return create_placement_failed_status(fail_count, str(last_error) if last_error else "Unknown error")

    def cancel_order(self, order_id):
        """Cancel an existing order with retries"""
        fail_count = 0
        
        for attempt in range(self.max_retries):
            try:
                result = cancel_order(order_id)
                if result:
                    self.logger.info(f"Cancelled order {order_id}")
                    return True
                
                fail_count += 1
                self.logger.error(f"Failed to cancel order {order_id} (attempt {attempt + 1})")
                
                if fail_count >= self.fail_threshold:
                    return None
                    
            except Exception as e:
                self.logger.error(f"Error cancelling order (attempt {attempt + 1}): {e}")
                fail_count += 1
                
                if fail_count >= self.fail_threshold:
                    return None
            
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_interval)
                
        return False

    def get_order_status(self, order_id):
        """Get detailed order status with retries"""
        fail_count = 0
        
        for attempt in range(self.max_retries):
            try:
                active_orders = get_active_orders(self.symbol)
                for order in active_orders:
                    if order['orderId'] == order_id:
                        return {
                            'status': 'active',
                            'executed_size': float(order['executedSize']),
                            'remaining_size': self.get_remaining_size(order)
                        }

                history = get_order_history(self.symbol, limit=50)
                for order in history:
                    if order['orderId'] == order_id:
                        return {
                            'status': order['status'],
                            'executed_size': float(order['executedSize']),
                            'remaining_size': 0 if order['status'] == 'closed' else self.get_remaining_size(order)
                        }
                
                fail_count += 1
                if fail_count >= self.fail_threshold:
                    return {
                        'status': 'closed',
                        'executed_size': None,
                        'remaining_size': 0
                    }
                        
            except Exception as e:
                self.logger.error(f"Error getting order status (attempt {attempt + 1}): {e}")
                fail_count += 1
                
                if fail_count >= self.fail_threshold:
                    return {
                        'status': 'closed',
                        'executed_size': None,
                        'remaining_size': 0
                    }
            
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_interval)
                
        return None

    def get_remaining_size(self, order):
        """Calculate remaining size for partially filled orders"""
        try:
            executed_size = Decimal(order['executedSize'])
            total_size = Decimal(order['size'])
            return float(total_size - executed_size)
        except Exception as e:
            self.logger.error(f"Error calculating remaining size: {e}")
            return None