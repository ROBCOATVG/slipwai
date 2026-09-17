```typescript
// packages/taxation/hexagon/application/src/for-calculating-taxes.ts
interface ForCalculatingTaxes {
  readonly taxOn: (amount: Money) => Money;
}

// tests: expect the constant
it('returns the flat placeholder tax', () => {
  const calculator = createTaxCalculation();
  expect(calculator.taxOn(createMoney(100, 'GBP'))).toEqual(createMoney(0, 'GBP'));
});
```
