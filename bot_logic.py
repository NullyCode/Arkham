import time
import logging
from decimal import Decimal
from api_client import ArkhamClient

class TradingBot:
    def __init__(self):
        self.api = ArkhamClient()
        self.logger = logging.getLogger(__name__)
        self.active_orders = []
        self.current_position = None
        self.is_running = False
        
    def calculate_grid_levels(self, current_price, usdt_amount, num_orders, price_drop, first_order_offset):
        try:
            current_price = Decimal(str(current_price))
            usdt_per_order = Decimal(str(usdt_amount)) / Decimal(str(num_orders))
            
            grid_levels = []
            first_price = current_price * (1 - Decimal(str(first_order_offset)) / 100)
            price_step = (Decimal(str(price_drop)) / 100) / (num_orders - 1)
            
            for i in range(num_orders):
                price = first_price * (1 - price_step * i)
                size = usdt_per_order / price
                grid_levels.append({
                    'price': float(price),
                    'size': float(size)
                })
                
            return grid_levels
        except Exception as e:
            self.logger.error(f"Error calculating grid levels: {e}")
            return []
            
    def place_grid_orders(self, symbol, grid_levels):
        try:
            placed_orders = []
            for level in grid_levels:
                order = self.api.place_order(
                    symbol=symbol,
                    side='buy',
                    order_type='limitGtc',
                    size=level['size'],
                    price=level['price']
                )
                if order:
                    placed_orders.append(order)
                    
            return placed_orders
        except Exception as e:
            self.logger.error(f"Error placing grid orders: {e}")
            return []
            
    def monitor_orders(self, symbol, target_profit_pct, price_deviation_pct):
        while self.is_running:
            try:
                ticker = self.api.get_ticker(symbol)
                if not ticker:
                    continue
                    
                current_price = float(ticker['price'])
                
                # Check for filled orders
                for order in self.active_orders:
                    if order['status'] == 'filled':
                        self.handle_filled_order(order, current_price, target_profit_pct)
                        
                # Check if price moved too far up
                if self.should_adjust_grid(current_price, price_deviation_pct):
                    self.adjust_grid(symbol, current_price)
                    
                time.sleep(1)  # Avoid excessive API calls
                
            except Exception as e:
                self.logger.error(f"Error monitoring orders: {e}")
                time.sleep(5)
                
    def handle_filled_order(self, filled_order, current_price, target_profit_pct):
        try:
            if not self.current_position:
                self.current_position = {
                    'entry_price': float(filled_order['price']),
                    'size': float(filled_order['size'])
                }
            else:
                # Average down the position
                total_size = self.current_position['size'] + float(filled_order['size'])
                total_cost = (self.current_position['entry_price'] * self.current_position['size'] + 
                            float(filled_order['price']) * float(filled_order['size']))
                self.current_position['entry_price'] = total_cost / total_size
                self.current_position['size'] = total_size
                
            # Check if we should take profit
            profit_pct = (current_price - self.current_position['entry_price']) / self.current_position['entry_price'] * 100
            if profit_pct >= target_profit_pct:
                self.take_profit(filled_order['symbol'], current_price)
                
        except Exception as e:
            self.logger.error(f"Error handling filled order: {e}")
            
    def take_profit(self, symbol, current_price):
        try:
            if self.current_position:
                # Place market sell order
                self.api.place_order(
                    symbol=symbol,
                    side='sell',
                    order_type='limitGtc',
                    size=self.current_position['size']
                )
                self.current_position = None
                
        except Exception as e:
            self.logger.error(f"Error taking profit: {e}")
            
    def should_adjust_grid(self, current_price, deviation_pct):
        if not self.active_orders:
            return False
            
        highest_order_price = max(float(order['price']) for order in self.active_orders)
        price_difference_pct = (current_price - highest_order_price) / highest_order_price * 100
        
        return price_difference_pct > deviation_pct
        
    def adjust_grid(self, symbol, current_price):
        try:
            # Cancel all existing orders
            for order in self.active_orders:
                self.api.cancel_order(order['orderId'])
                
            # Calculate and place new grid orders
            self.active_orders = []
            # Recalculate grid levels and place new orders...
            
        except Exception as e:
            self.logger.error(f"Error adjusting grid: {e}")
            
    def start(self, symbol, usdt_amount, num_orders, price_drop, first_order_offset, target_profit_pct, price_deviation_pct):
        try:
            self.is_running = True
            ticker = self.api.get_ticker(symbol)
            if not ticker:
                raise Exception("Could not get current price")
                
            current_price = float(ticker['price'])
            grid_levels = self.calculate_grid_levels(
                current_price, usdt_amount, num_orders, price_drop, first_order_offset
            )
            
            self.active_orders = self.place_grid_orders(symbol, grid_levels)
            self.monitor_orders(symbol, target_profit_pct, price_deviation_pct)
            
        except Exception as e:
            self.logger.error(f"Error starting bot: {e}")
            self.is_running = False
            
    def stop(self):
        self.is_running = False
        # Cancel all active orders
        for order in self.active_orders:
            self.api.cancel_order(order['orderId'])