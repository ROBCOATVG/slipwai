```typescript
// packages/taxation/hexagon/application/src/tax-rate-provider.ts
interface TaxRateProvider {
  readonly rateFor: (amount: Money) => TaxRate;
}

const createTaxCalculation = (rates: TaxRateProvider): ForCalculatingTaxes => ({
  taxOn: (amount) => applyRate(amount, rates.rateFor(amount)),
});
```
