# calculator.py

def add(a: float, b: float) -> float:
    return a + b

def multiply(a: float, b: float) -> float:
    return a * b

def divide(a: float, b: float) -> float:
    if b == 0:
        return 0.0
    return a / b

# --- TESTS ---
def test_add():
    assert add(2, 3) == 5.0

def test_multiply():
    assert multiply(2, 3) == 6.0

def test_divide():
    assert divide(10, 2) == 5.0
    assert divide(10, 0) == 0.0  # Fails here!