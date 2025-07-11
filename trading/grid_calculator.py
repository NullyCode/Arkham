import logging
from decimal import Decimal
from api.trading_api import get_balances, get_pair_info

logger = logging.getLogger(__name__)

def get_available_usdt():
    """Get available USDT balance"""
    try:
        balances = get_balances()
        for balance in balances:
            if balance['symbol'] == 'USDT':
                return float(balance['free'])
        return 0
    except Exception as e:
        logger.error(f"Error getting USDT balance: {e}")
        return 0

def get_min_notional(symbol):
    """Get minimum notional value for the trading pair"""
    try:
        pair_info = get_pair_info(symbol)
        if pair_info and 'minNotional' in pair_info:
            return float(pair_info['minNotional'])
        return 0
    except Exception as e:
        logger.error(f"Error getting minimum notional: {e}")
        return 0

def calculate_order_size(price, usdt_amount, min_notional):
    """Calculate maximum possible order size based on available USDT"""
    try:
        # Convert to Decimal for precise calculation
        price = Decimal(str(price))
        usdt = Decimal(str(usdt_amount))
        min_notional = Decimal(str(min_notional))

        # Calculate maximum possible size
        max_size = usdt / price

        # Ensure minimum notional is met
        if price * max_size < min_notional:
            logger.warning(f"Order size too small to meet minimum notional requirement")
            return 0

        # Add larger buffer (0.2%) to account for price fluctuations and fees
        buffer = Decimal('0.998')
        adjusted_size = max_size * buffer

        # Round down to 4 decimal places to ensure order acceptance
        rounded_size = adjusted_size.quantize(Decimal('0.0001'), rounding='ROUND_DOWN')

        return float(rounded_size)

    except Exception as e:
        logger.error(f"Error calculating order size: {e}")
        return 0

def calculate_grid_levels(current_price, usdt_amount, num_orders, price_drop, first_order_offset, symbol):
    """Calculate grid levels with proper rounding and balance check"""
    try:
        # Get available USDT balance
        available_usdt = get_available_usdt()
        logger.info(f"Available USDT balance: {available_usdt}")
        
        # Get minimum notional value
        min_notional = get_min_notional(symbol)
        
        # Use the smaller of requested amount or available balance
        actual_usdt = min(float(usdt_amount), available_usdt)
        
        if actual_usdt <= 0:
            logger.error("Insufficient USDT balance")
            return []
            
        current_price = Decimal(str(current_price))
        usdt_per_order = Decimal(str(actual_usdt)) / Decimal(str(num_orders))
        
        grid_levels = []
        first_price = current_price * (1 - Decimal(str(first_order_offset)) / 100)
        
        # Handle single order case
        if num_orders == 1:
            size = calculate_order_size(float(first_price), float(actual_usdt), min_notional)
            if size > 0:
                grid_levels.append({
                    'price': float(first_price),
                    'size': size
                })
        else:
            price_step = (Decimal(str(price_drop)) / 100) / (num_orders - 1)
            for i in range(num_orders):
                price = first_price * (1 - price_step * i)
                size = calculate_order_size(float(price), float(usdt_per_order), min_notional)
                if size > 0:
                    grid_levels.append({
                        'price': float(price),
                        'size': size
                    })
            
        if not grid_levels:
            logger.warning("No valid grid levels could be calculated")
            
        # If we couldn't create multiple levels, try single order with all available USDT
        if len(grid_levels) == 0 and actual_usdt >= min_notional:
            size = calculate_order_size(float(current_price), actual_usdt, min_notional)
            if size > 0:
                grid_levels.append({
                    'price': float(current_price),
                    'size': size
                })
                logger.info(f"Created single order with all available USDT: {actual_usdt}")
            
        return grid_levels
        
    except Exception as e:
        logger.error(f"Error calculating grid levels: {e}")
        return []