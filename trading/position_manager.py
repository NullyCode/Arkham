import logging
from decimal import Decimal

class PositionManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.current_position = None
        self.filled_orders = []  # Track filled buy orders
        
    def update_position(self, filled_order):
        """Update position when a buy order is filled"""
        try:
            # Extract execution details using the correct field names from Arkham API
            executed_size = Decimal(str(filled_order['size']))  # Use 'size' instead of 'lastSize'
            executed_price = Decimal(str(filled_order['price']))  # Use 'price' instead of 'lastPrice'
            
            if executed_size <= 0 or executed_price <= 0:
                self.logger.error(f"Invalid order execution data: size={executed_size}, price={executed_price}")
                return
                
            self.logger.info(f"Processing executed order: size={executed_size}, price={executed_price}")
            
            # Add new filled order
            self.filled_orders.append({
                'price': executed_price,
                'size': executed_size
            })
            
            # Calculate total position
            total_size = sum(Decimal(str(order['size'])) for order in self.filled_orders)
            weighted_sum = sum(Decimal(str(order['price'])) * Decimal(str(order['size'])) for order in self.filled_orders)
            
            if total_size > 0:
                avg_price = weighted_sum / total_size
                self.current_position = {
                    'entry_price': float(avg_price),
                    'size': float(total_size)
                }
                self.logger.info(f"Updated position: entry_price={self.current_position['entry_price']}, size={self.current_position['size']}")
            else:
                self.logger.error("Calculated total size is 0, position not updated")
                
        except Exception as e:
            self.logger.error(f"Error updating position: {e}")
            
    def get_take_profit_price(self, profit_percentage):
        """Calculate take profit price based on average entry"""
        try:
            if not self.current_position:
                self.logger.warning("No position exists to calculate take-profit price")
                return None
                
            entry_price = Decimal(str(self.current_position['entry_price']))
            profit_mult = 1 + (Decimal(str(profit_percentage)) / 100)
            take_profit_price = float(entry_price * profit_mult)
            
            self.logger.info(f"Calculated take-profit price: {take_profit_price} (entry: {entry_price}, profit: {profit_percentage}%)")
            return take_profit_price
            
        except Exception as e:
            self.logger.error(f"Error calculating take-profit price: {e}")
            return None
        
    def get_position_size(self):
        """Get total position size"""
        try:
            if not self.current_position:
                return 0
            return float(self.current_position['size'])
        except Exception as e:
            self.logger.error(f"Error getting position size: {e}")
            return 0
        
    def clear_position(self):
        """Clear position and filled orders history"""
        try:
            self.logger.info("Clearing position and order history")
            self.current_position = None
            self.filled_orders.clear()
        except Exception as e:
            self.logger.error(f"Error clearing position: {e}")