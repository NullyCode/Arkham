import logging
import time
import threading
from .order_status import is_valid_order

class TrailingMonitor:
    def __init__(self, symbol, price_monitor, order_manager, balance_manager):
        self.logger = logging.getLogger(__name__)
        self.symbol = symbol
        self.price_monitor = price_monitor
        self.order_manager = order_manager
        self.balance_manager = balance_manager
        self.is_running = True
        self.monitor_thread = None
        self.min_adjustment_interval = 3
        self.error_retry_interval = 3
        self.max_balance_check_attempts = 5
        self.max_sell_attempts = 3
        
    def start_monitoring(self, initial_size, price_deviation_pct, setup_new_grid_callback):
        # Reset price tracking for new cycle
        self.price_monitor.reset_tracking()
        
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(initial_size, price_deviation_pct, setup_new_grid_callback)
        )
        self.monitor_thread.start()

    def _handle_remaining_balance(self, price_deviation_pct):
        """Handle any remaining balance by placing a sell order"""
        try:
            available = self.balance_manager.get_available_balance()
            min_size = self.balance_manager.min_trade_size
            
            if available <= 0 or available < min_size:
                return True
                
            # Try to sell remaining balance
            current_price = self.price_monitor.get_current_price(self.symbol)
            if not current_price:
                return False
                
            sell_price = self.price_monitor.calculate_trailing_price(
                current_price,
                price_deviation_pct
            )
            
            order = self.order_manager.place_limit_sell(available, sell_price)
            if is_valid_order(order):
                self.logger.info(f"Placed sell order for remaining balance: {available}")
                return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"Error handling remaining balance: {e}")
            return False

    def _monitor_loop(self, total_size, price_deviation_pct, setup_new_grid_callback):
        remaining_size = total_size
        current_order = None
        last_adjustment_time = 0
        zero_balance_attempts = 0
        sell_attempts = 0

        while self.is_running and remaining_size > 0:
            try:
                # First check for active sell orders
                has_active_sells = self.balance_manager.check_active_sell_orders()
                if has_active_sells:
                    self.logger.info("Active sell orders exist, continuing monitoring")
                    zero_balance_attempts = 0
                    sell_attempts = 0
                    
                    # Monitor existing order for price adjustments
                    if current_order and is_valid_order(current_order):
                        current_time = time.time()
                        current_price = self.price_monitor.get_current_price(self.symbol)
                        
                        if current_price:
                            current_order_price = float(current_order['price'])
                            needs_adjustment = self.price_monitor.calculate_price_deviation(
                                current_price,
                                current_order_price,
                                price_deviation_pct
                            )

                            if needs_adjustment and current_time - last_adjustment_time >= self.min_adjustment_interval:
                                order_status = self.order_manager.get_order_status(current_order['orderId'])
                                if order_status and order_status['remaining_size'] > 0:
                                    if self.order_manager.cancel_order(current_order['orderId']):
                                        new_price = self.price_monitor.calculate_trailing_price(
                                            current_price,
                                            price_deviation_pct
                                        )
                                        current_order = self.order_manager.place_limit_sell(
                                            order_status['remaining_size'],
                                            new_price
                                        )
                                        if is_valid_order(current_order):
                                            last_adjustment_time = current_time
                                            self.logger.info(f"Adjusted sell order price to {new_price}")
                                        else:
                                            current_order = None
                    
                    time.sleep(self.error_retry_interval)
                    continue

                # Check available balance
                available = self.balance_manager.get_available_balance()
                min_size = self.balance_manager.min_trade_size

                if available >= min_size:
                    # We have enough balance to sell
                    if not current_order:
                        # Try to place new sell order
                        current_price = self.price_monitor.get_current_price(self.symbol)
                        if current_price:
                            sell_price = self.price_monitor.calculate_trailing_price(
                                current_price,
                                price_deviation_pct
                            )
                            current_order = self.order_manager.place_limit_sell(
                                available,
                                sell_price
                            )
                            if is_valid_order(current_order):
                                last_adjustment_time = time.time()
                                sell_attempts = 0
                            else:
                                sell_attempts += 1
                                if sell_attempts >= self.max_sell_attempts:
                                    self.logger.error("Max sell attempts reached")
                                    return
                    
                    zero_balance_attempts = 0
                    
                else:
                    # No sufficient balance and no active orders
                    zero_balance_attempts += 1
                    self.logger.warning(f"Zero balance check attempt {zero_balance_attempts}/{self.max_balance_check_attempts}")
                    
                    if zero_balance_attempts >= self.max_balance_check_attempts:
                        # Double check no active orders and no significant balance
                        if not self.balance_manager.check_active_sell_orders():
                            if self._handle_remaining_balance(price_deviation_pct):
                                self.logger.info("All coins sold successfully")
                                setup_new_grid_callback()
                                return

                time.sleep(1)

            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                if current_order and is_valid_order(current_order):
                    self.order_manager.cancel_order(current_order['orderId'])
                current_order = None
                time.sleep(self.error_retry_interval)

        if remaining_size <= 0:
            # Final check for any remaining balance
            if self._handle_remaining_balance(price_deviation_pct):
                self.logger.info("All coins sold successfully")
                setup_new_grid_callback()

    def stop(self):
        self.is_running = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join()