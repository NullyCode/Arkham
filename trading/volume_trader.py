import logging
from trading.volume.order_manager import OrderManager
from trading.volume.price_monitor import PriceMonitor
from trading.volume.delay_manager import DelayManager
from trading.volume.trailing_monitor import TrailingMonitor
from trading.volume.balance_manager import BalanceManager

class VolumeTrader:
    def __init__(self, symbol, min_delay, max_delay, delay_callback, first_order_offset=0.02):
        self.logger = logging.getLogger(__name__)
        self.symbol = symbol
        self.is_running = True
        self.use_trailing_limit = False
        self.price_deviation_pct = 0
        
        # Initialize components
        self.balance_manager = BalanceManager(symbol)
        self.order_manager = OrderManager(symbol)
        self.price_monitor = PriceMonitor(first_order_offset)
        self.delay_manager = DelayManager(min_delay, max_delay, delay_callback)
        self.trailing_monitor = TrailingMonitor(
            symbol,
            self.price_monitor,
            self.order_manager,
            self.balance_manager
        )

    def handle_filled_buy(self, filled_order, setup_new_grid_callback):
        """Handle filled buy order with either market sell or trailing limit sell"""
        try:
            # Wait for random delay
            delay = self.delay_manager.get_random_delay()
            self.logger.info(f"Waiting {delay:.1f} seconds before sell order")
            self.delay_manager.start_countdown()
            self.delay_manager.countdown_thread.join()

            if not self.is_running:
                return

            # Validate available balance
            available_size = self.balance_manager.validate_sell_size(filled_order['size'])
            if available_size <= 0:
                self.logger.error("No balance available for selling")
                return

            # Get current market price
            current_price = self.price_monitor.get_current_price(self.symbol)
            if not current_price:
                self.logger.error("Failed to get current market price")
                return

            if self.use_trailing_limit:
                # Start trailing monitor with validated size
                self.trailing_monitor.start_monitoring(
                    available_size,
                    self.price_deviation_pct,
                    setup_new_grid_callback
                )
            else:
                # Place market sell order
                sell_order = self.order_manager.place_market_sell(available_size)
                if sell_order:
                    self.logger.info("Market sell order placed successfully")
                    setup_new_grid_callback()
                else:
                    self.logger.error("Failed to place market sell order")

        except Exception as e:
            self.logger.error(f"Error handling filled buy order: {e}")

    def stop(self):
        """Stop all components"""
        self.is_running = False
        self.delay_manager.stop()
        self.trailing_monitor.stop()