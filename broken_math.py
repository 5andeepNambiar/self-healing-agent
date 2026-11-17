def divide_numbers(a: float, b: float) -> float:
    if b == 0:
        return 0.0
    return a / b

def test_normal_division():
    assert divide_numbers(10, 2) == 5.0

def test_zero_division():
    assert divide_numbers(10, 0) == 0.0
