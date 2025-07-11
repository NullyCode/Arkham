import logging
from decimal import Decimal
from api.market_api import get_ticker

class PriceMonitor:
    def __init__(self, first_order_offset=0.02):
        self.logger = logging.getLogger(__name__)
        self.last_known_price = None
        self.highest_tracked_price = None
        self.first_order_offset_pct = first_order_offset

    def get_current_price(self, symbol):
        """Get current market price with validation"""
        try:
            ticker = get_ticker(symbol)
            if ticker and 'price' in ticker:
                price = float(ticker['price'])
                if price > 0:
                    self.last_known_price = price
                    # Update highest tracked price if this is a new high
                    if self.highest_tracked_price is None or price > self.highest_tracked_price:
                        self.highest_tracked_price = price
                    return price
            return self.last_known_price
        except Exception as e:
            self.logger.error(f"Error getting current price: {e}")
            return self.last_known_price

    def calculate_price_deviation(self, current_price, order_price, target_deviation):
        """Calculate if price deviation exceeds threshold"""
        try:
            if not current_price or not order_price:
                return False

            # Update highest tracked price if current price is higher
            if self.highest_tracked_price is None or current_price > self.highest_tracked_price:
                self.highest_tracked_price = current_price
                return True  # Trigger adjustment for new high

            # Calculate deviation from highest price
            price_drop_pct = ((self.highest_tracked_price - current_price) / self.highest_tracked_price) * 100
            
            # If price has dropped more than deviation threshold, need to adjust
            if price_drop_pct > target_deviation:
                # Reset highest tracked price to current price
                self.highest_tracked_price = current_price
                return True

            # Check if current order price is too far from ideal trailing price
            ideal_price = self.calculate_trailing_price(current_price, target_deviation)
            price_diff_pct = abs((order_price - ideal_price) / ideal_price) * 100
            buffer = 0.5  # 0.01% buffer to prevent constant adjustments

            return price_diff_pct > buffer

        except Exception as e:
            self.logger.error(f"Error calculating price deviation: {e}")
            return False

    def calculate_trailing_price(self, current_price, deviation_pct):
        """Calculate trailing limit price based on current price"""
        try:
            # If we have a highest tracked price, use it to calculate trailing price
            reference_price = self.highest_tracked_price if self.highest_tracked_price else current_price
            
            # Calculate minimum acceptable price (trailing stop level)
            min_acceptable_price = reference_price * (1 - deviation_pct / 100)
            
            # Use the higher of current price and minimum acceptable price
            trailing_price = max(current_price, min_acceptable_price)
            
            # Add markup based on first_order_offset parameter
            markup = trailing_price * (self.first_order_offset_pct / 100)
            final_price = trailing_price + markup
            
            self.logger.info(f"Calculated trailing price: {final_price} (current: {current_price}, highest: {reference_price}, deviation: {deviation_pct}%, offset: {self.first_order_offset_pct}%)")
            return final_price
            
        except Exception as e:
            self.logger.error(f"Error calculating trailing price: {e}")
            return None

    def reset_tracking(self):
        """Reset price tracking for new cycle"""
        self.highest_tracked_price = None