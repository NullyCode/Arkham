import logging
import time
from PyQt6.QtCore import QThread, pyqtSignal
from decimal import Decimal

from api.market_api import get_ticker
from api.trading_api import place_order, cancel_order, get_active_orders
from trading.grid_calculator import calculate_grid_levels
from trading.position_manager import PositionManager
from trading.volume_trader import VolumeTrader

class BotWorker(QThread):
    error = pyqtSignal(str)
    delay_updated = pyqtSignal(float)
    
    def __init__(self, params):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.params = params
        self.grid_orders = {}  # Track grid orders by order ID
        self.take_profit_order = None
        self.position_manager = PositionManager()
        self.has_filled_orders = False
        self.volume_trader = None if params['mode'] == "Grid Trading" else VolumeTrader(
            params['symbol'],
            params['min_delay'],
            params['max_delay'],
            self.delay_updated.emit,
            params['first_order_offset']  # Pass first_order_offset to VolumeTrader
        )
        if self.volume_trader:
            self.volume_trader.use_trailing_limit = params.get('use_trailing_limit', False)
            self.volume_trader.price_deviation_pct = params.get('price_deviation_pct', 0)
        self.is_running = False
        
    def run(self):
        try:
            self.is_running = True
            self.logger.info(f"Starting bot with parameters: {self.params}")
            
            # Initial grid setup
            self.setup_grid()
            
            # Main monitoring loop
            while self.is_running:
                try:
                    self.monitor_orders()
                    time.sleep(2)  # Avoid excessive API calls
                except Exception as e:
                    self.logger.error(f"Error in monitoring loop: {e}")
                    self.error.emit(str(e))
                    time.sleep(5)
                    
        except Exception as e:
            self.logger.error(f"Bot error: {e}")
            self.error.emit(str(e))
        finally:
            self.is_running = False
            
    def stop(self):
        """Stop the bot and cancel all orders"""
        self.is_running = False
        if self.volume_trader:
            self.volume_trader.stop()
        self.cancel_all_orders()
        
    def setup_grid(self):
        """Set up initial grid orders"""
        try:
            # Reset the filled orders flag when creating new grid
            self.has_filled_orders = False
            
            # Get current price
            ticker = get_ticker(self.params['symbol'])
            if not ticker:
                raise Exception("Could not get current price")
                
            current_price = float(ticker['price'])
            self.logger.info(f"Current price for {self.params['symbol']}: {current_price}")
            
            # Calculate grid levels
            grid_levels = calculate_grid_levels(
                current_price,
                self.params['usdt_amount'],
                self.params['num_orders'],
                self.params['price_drop'],
                self.params['first_order_offset'],
                self.params['symbol']
            )
            
            self.logger.info(f"Calculated {len(grid_levels)} grid levels")
            
            # Place grid orders
            self.logger.info("Placing grid orders...")
            self.place_grid_orders(grid_levels)
            
        except Exception as e:
            self.logger.error(f"Error setting up grid: {e}")
            raise
            
    def place_grid_orders(self, grid_levels):
        """Place all grid buy orders"""
        try:
            for level in grid_levels:
                self.logger.info(f"Placing buy order at price {level['price']} with size {level['size']}")
                
                order = place_order(
                    symbol=self.params['symbol'],
                    side='buy',
                    order_type='limitGtc',
                    size=level['size'],
                    price=level['price']
                )
                
                if order:
                    self.logger.info(f"Successfully placed buy order: {order}")
                    self.grid_orders[order['orderId']] = order
                else:
                    self.logger.error(f"Failed to place order at price {level['price']}")
                    
        except Exception as e:
            self.logger.error(f"Error placing grid orders: {e}")
            raise
            
    def monitor_orders(self):
        """Monitor orders for fills and price deviations"""
        try:
            active_orders = get_active_orders(self.params['symbol'])
            active_order_ids = {order['orderId'] for order in active_orders}
            
            # Check for filled buy orders
            for order_id in list(self.grid_orders.keys()):
                if order_id not in active_order_ids:
                    filled_order = self.grid_orders.pop(order_id)
                    self.logger.info(f"Buy order filled: {filled_order}")
                    
                    if self.params['mode'] == "Grid Trading":
                        self.handle_filled_buy_order_grid(filled_order)
                    else:
                        # Start volume trading cycle
                        self.volume_trader.handle_filled_buy(filled_order, self.setup_grid)
                    
            if self.params['mode'] == "Grid Trading":
                # Check if take-profit order was filled
                if self.take_profit_order and self.take_profit_order['orderId'] not in active_order_ids:
                    self.handle_filled_sell_order_grid()
            
            # Check price deviation for both modes if no orders are filled
            if not self.has_filled_orders:
                self.check_price_deviation()
                
        except Exception as e:
            self.logger.error(f"Error monitoring orders: {e}")
            
    def handle_filled_buy_order_grid(self, filled_order):
        """Handle a filled buy order in grid trading mode"""
        try:
            self.logger.info(f"Processing filled buy order (grid mode): {filled_order}")
            
            # Set flag that we have filled orders in this cycle
            self.has_filled_orders = True
            
            # Update position
            self.position_manager.update_position(filled_order)
            self.logger.info(f"Updated position: {self.position_manager.current_position}")
            
            if self.position_manager.current_position:
                # Cancel existing take-profit order if any
                if self.take_profit_order:
                    self.logger.info("Cancelling existing take-profit order")
                    cancel_order(self.take_profit_order['orderId'])
                    self.take_profit_order = None
                
                # Place new take-profit order
                self.place_take_profit_order()
            else:
                self.logger.warning("Position not updated, skipping take-profit order")
                
        except Exception as e:
            self.logger.error(f"Error handling filled buy order: {e}")
            
    def handle_filled_sell_order_grid(self):
        """Handle a filled sell order in grid trading mode"""
        try:
            self.logger.info("Take-profit order filled, restarting bot with same parameters")
            
            # Clear position and orders
            self.position_manager.clear_position()
            self.take_profit_order = None
            
            # Cancel remaining grid orders
            self.cancel_all_orders()
            
            # Start new grid with same parameters
            self.setup_grid()
            
        except Exception as e:
            self.logger.error(f"Error handling filled sell order: {e}")
            
    def place_take_profit_order(self):
        """Place take-profit sell order (grid mode only)"""
        try:
            if not self.position_manager.current_position:
                self.logger.warning("No position exists to place take-profit order")
                return
                
            take_profit_price = self.position_manager.get_take_profit_price(
                self.params['target_profit_pct']
            )
            position_size = self.position_manager.get_position_size()
            
            if not take_profit_price or position_size <= 0:
                self.logger.error(f"Invalid take-profit parameters: price={take_profit_price}, size={position_size}")
                return
                
            self.logger.info(f"Placing take-profit order: price={take_profit_price}, size={position_size}")
            
            order = place_order(
                symbol=self.params['symbol'],
                side='sell',
                order_type='limitGtc',
                size=position_size,
                price=take_profit_price
            )
            
            if order:
                self.logger.info(f"Take-profit order placed successfully: {order}")
                self.take_profit_order = order
            else:
                self.logger.error("Failed to place take-profit order")
                
        except Exception as e:
            self.logger.error(f"Error placing take-profit order: {e}")
            
    def check_price_deviation(self):
        """Check if price has moved too far from grid"""
        try:
            if not self.grid_orders:
                return
                
            ticker = get_ticker(self.params['symbol'])
            if not ticker:
                return
                
            current_price = float(ticker['price'])
            highest_order_price = max(float(order['price']) for order in self.grid_orders.values())
            
            price_difference_pct = ((current_price - highest_order_price) / highest_order_price) * 100
            
            # Check if price deviation exceeds threshold
            if price_difference_pct > self.params['price_deviation_pct']:
                self.logger.info(f"Price moved too far (diff: {price_difference_pct}%), adjusting grid...")
                self.cancel_all_orders()
                self.setup_grid()
                
        except Exception as e:
            self.logger.error(f"Error checking price deviation: {e}")
            
    def cancel_all_orders(self):
        """Cancel all active orders"""
        try:
            for order_id in list(self.grid_orders.keys()):
                cancel_order(order_id)
                del self.grid_orders[order_id]
                
            if self.take_profit_order:
                cancel_order(self.take_profit_order['orderId'])
                self.take_profit_order = None
                
        except Exception as e:
            self.logger.error(f"Error cancelling orders: {e}")