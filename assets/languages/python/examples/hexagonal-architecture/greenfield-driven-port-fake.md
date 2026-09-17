```python
from dataclasses import dataclass
from typing import Protocol


# Driven port — application-owned because the use case consults it for rates
class TaxRateProvider(Protocol):
    def rate_for(self, amount: "Money") -> "TaxRate": ...


@dataclass(frozen=True)
class TaxCalculation:
    """ForCalculatingTaxes use case — takes its driven port as a dependency
    instead of hardcoding a constant."""

    rates: TaxRateProvider

    def tax_on(self, amount: "Money") -> "Money":
        return apply_rate(amount, self.rates.rate_for(amount))


def create_tax_calculation(rates: TaxRateProvider) -> "ForCalculatingTaxes":
    return TaxCalculation(rates)
```
