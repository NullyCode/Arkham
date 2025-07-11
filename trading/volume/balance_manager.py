import logging
import time
from decimal import Decimal
from api.trading_api import get_balances, get_active_orders, get_pair_info

class BalanceManager:
    def __init__(self, symbol):
        self.logger = logging.getLogger(__name__)
        self.symbol = symbol
        self.base_currency = symbol.split('_')[0] if '_' in symbol else symbol.split('/')[0]
        self.last_known_balance = None
        self.max_retries = 3
        self.retry_delay = 3  # seconds
        self.min_trade_size = self._get_min_trade_size()

    def _get_min_trade_size(self):
        """Get minimum trade size for the symbol"""
        try:
            pair_info = get_pair_info(self.symbol)
            if pair_info and 'minSize' in pair_info:
                return float(pair_info['minSize'])
            return 0
        except Exception as e:
            self.logger.error(f"Error getting minimum trade size: {e}")
            return 0

    def get_total_balance(self):
        """Get total balance including both available and in orders"""
        try:
            available = self.get_available_balance()
            active_orders = get_active_orders(self.symbol)
            in_orders = sum(
                float(order['size']) - float(order.get('executedSize', 0))
                for order in active_orders
                if order['side'] == 'sell'
            )
            
            total = available + in_orders
            self.logger.info(f"Total {self.base_currency} balance: {total} (available: {available}, in orders: {in_orders})")
            return total
            
        except Exception as e:
            self.logger.error(f"Error getting total balance: {e}")
            return self.last_known_balance if self.last_known_balance is not None else 0

    def get_available_balance(self):
        """Get available balance for the trading pair's base currency with retries"""
        for attempt in range(self.max_retries):
            try:
                balances = get_balances()
                if not balances:
                    self.logger.error("Failed to retrieve balances")
                    continue

                for balance in balances:
                    if balance['symbol'] == self.base_currency:
                        available = float(balance['free'])
                        self.last_known_balance = available
                        self.logger.info(f"Available {self.base_currency} balance: {available}")
                        return available

                self.logger.error(f"Balance for {self.base_currency} not found in response")
                if self.last_known_balance is not None:
                    return self.last_known_balance
                return 0

            except Exception as e:
                self.logger.error(f"Error getting balance (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)

        if self.last_known_balance is not None:
            self.logger.warning(f"Using last known balance: {self.last_known_balance}")
            return self.last_known_balance
        return 0

    def check_active_sell_orders(self):
        """Check if there are any active sell orders"""
        try:
            active_orders = get_active_orders(self.symbol)
            sell_orders = [order for order in active_orders if order['side'] == 'sell']
            return len(sell_orders) > 0
        except Exception as e:
            self.logger.error(f"Error checking active sell orders: {e}")
            return False

    def can_start_new_cycle(self):
        """Check if conditions are met to start a new cycle"""
        try:
            # Get available balance
            available = self.get_available_balance()
            
            # Check if there are active sell orders
            has_active_sells = self.check_active_sell_orders()
            
            # Get minimum trade size
            min_size = self.min_trade_size
            
            self.logger.info(f"Checking cycle conditions: available={available}, min_size={min_size}, has_active_sells={has_active_sells}")
            
            # Can start new cycle if:
            # 1. No available balance or balance below min trade size
            # 2. No active sell orders
            return (available == 0 or available < min_size) and not has_active_sells
            
        except Exception as e:
            self.logger.error(f"Error checking cycle conditions: {e}")
            return False

    def validate_sell_size(self, desired_size):
        """Validate and adjust sell size against total balance"""
        try:
            total_balance = self.get_total_balance()
            self.logger.info(f"Validating sell size {desired_size} against total balance {total_balance}")

            if total_balance <= 0:
                if self.last_known_balance and self.last_known_balance > 0:
                    self.logger.warning("Using last known balance for validation")
                    total_balance = self.last_known_balance
                else:
                    self.logger.error(f"No {self.base_currency} balance available for selling")
                    return 0

            # Check against minimum trade size
            if total_balance < self.min_trade_size:
                self.logger.warning(f"Total balance {total_balance} is below minimum trade size {self.min_trade_size}")
                return 0

            total_balance = Decimal(str(total_balance))
            desired_size = Decimal(str(desired_size))
            buffer = Decimal('0.999')
            max_size = total_balance * buffer

            if desired_size > max_size:
                self.logger.warning(f"Desired size {desired_size} exceeds total balance {total_balance}, adjusting to {max_size}")
                return float(max_size)
            
            return float(desired_size)

        except Exception as e:
            self.logger.error(f"Error validating sell size: {e}")
            if self.last_known_balance is not None:
                try:
                    return min(float(desired_size), self.last_known_balance * 0.999)
                except:
                    pass
            return 0