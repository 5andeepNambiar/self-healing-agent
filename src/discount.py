# src/discount.py
from src.math_utils import calculate_percentage

def apply_promotional_discount(original_price: float, discount_percent: float) -> float:
    """Calculates discounted price. Discount percent is between 0 and 100."""
    if discount_percent < 0 or discount_percent > 100:
        raise ValueError("Invalid discount range")
    
    discount_amount = (original_price * discount_percent) / 100
    return original_price - discount_amount