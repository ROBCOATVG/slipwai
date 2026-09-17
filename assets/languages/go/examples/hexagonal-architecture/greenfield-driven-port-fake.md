```go
package taxation

// TaxRateProvider is a driven port — application-owned because the use case
// consults it to look up the rate for an amount.
type TaxRateProvider interface {
	RateFor(amount Money) TaxRate
}

// TaxCalculation is the ForCalculatingTaxes use case. It holds its driven
// port dependency as a field instead of hardcoding a constant rate.
type TaxCalculation struct {
	Rates TaxRateProvider
}

// NewTaxCalculation wires the driven port into the use case.
func NewTaxCalculation(rates TaxRateProvider) *TaxCalculation {
	return &TaxCalculation{Rates: rates}
}

// TaxOn consults the driven port to compute the tax owed on amount.
func (c *TaxCalculation) TaxOn(amount Money) Money {
	return ApplyRate(amount, c.Rates.RateFor(amount))
}
```
