# tests/test_discount.py
from src.discount import apply_promotional_discount
from src.math_utils import calculate_percentage

def test_apply_promotional_discount():
    # 20% off 100 should be 80
    assert apply_promotional_discount(100.0, 20.0) == 80.0

def test_calculate_percentage():
    # 25 out of 100 should be 25.0%
    assert calculate_percentage(25, 100) == 25.0  # Fails! Returns 2.5