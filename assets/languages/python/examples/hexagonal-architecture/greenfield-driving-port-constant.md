```python
from typing import Protocol


# Driving port — exposed by the application, called by driving adapters
class ForCalculatingTaxes(Protocol):
    def tax_on(self, amount: "Money") -> "Money": ...


# tests: expect the constant
def test_returns_the_flat_placeholder_tax() -> None:
    calculator = create_tax_calculation()

    assert calculator.tax_on(create_money(100, "GBP")) == create_money(0, "GBP")
```
