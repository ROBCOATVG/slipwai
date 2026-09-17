```java
/** The driven port the use case discovered it needs: a rate has to come from somewhere. */
public interface TaxRateProvider {
    TaxRate rateFor(Money amount);
}

/** The use case consumes it, and knows nothing about where a rate is actually kept. */
final class TaxCalculation implements ForCalculatingTaxes {

    private final TaxRateProvider rates;

    TaxCalculation(TaxRateProvider rates) {
        this.rates = rates;
    }

    @Override
    public Money taxOn(Money amount) {
        return rates.rateFor(amount).applyTo(amount);
    }
}

/** The first adapter is a constant one. It is still a real implementation of the port. */
final class FlatTaxRateProvider implements TaxRateProvider {

    @Override
    public TaxRate rateFor(Money amount) {
        return TaxRate.percent(20);
    }
}
```
