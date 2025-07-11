"""
Order status handling and validation
"""
from dataclasses import dataclass
from typing import Optional

@dataclass
class OrderStatus:
    status: str
    order_id: Optional[str] = None
    available_balance: Optional[float] = None
    required_size: Optional[float] = None
    attempts: Optional[int] = None
    error: Optional[str] = None

def create_insufficient_balance_status(available: float, required: float) -> OrderStatus:
    return OrderStatus(
        status='insufficient_balance',
        available_balance=available,
        required_size=required
    )

def create_placement_failed_status(attempts: int, error: str) -> OrderStatus:
    return OrderStatus(
        status='placement_failed',
        attempts=attempts,
        error=error
    )

def create_assumed_complete_status() -> OrderStatus:
    return OrderStatus(status='assumed_complete')

def is_valid_order(order: dict) -> bool:
    return isinstance(order, dict) and 'orderId' in order