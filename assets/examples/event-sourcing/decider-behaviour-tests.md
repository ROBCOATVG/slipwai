```typescript
// Event factories — complete, valid data with overrides (testing skill's factory pattern)
const opened = (currency: Currency = 'GBP'): AccountEvent => ({ type: 'AccountOpened', currency });
const money = (minorUnits: number, currency: Currency = 'GBP'): Money => ({ minorUnits, currency });
const deposited = (minorUnits: number): AccountEvent => ({ type: 'MoneyDeposited', amount: money(minorUnits) });
const withdrawn = (minorUnits: number): AccountEvent => ({ type: 'MoneyWithdrawn', amount: money(minorUnits) });

it('should record a deposit as MoneyDeposited on an open account', () => {
  const state = [opened()].reduce(evolve, initialState);

  const decision = decide({ type: 'Deposit', amount: money(5_000) }, state);

  expect(decision).toEqual({
    accepted: true,
    events: [{ type: 'MoneyDeposited', amount: money(5_000) }],
  });
});

it('should reject a withdrawal that exceeds the balance', () => {
  const state = [opened(), deposited(5_000)].reduce(evolve, initialState);

  const decision = decide({ type: 'Withdraw', amount: money(10_000) }, state);

  expect(decision).toEqual({ accepted: false, reason: 'insufficient-funds' });
});

it('should reject any operation on an account that was never opened', () => {
  const decision = decide({ type: 'Deposit', amount: money(5_000) }, initialState);

  expect(decision).toEqual({ accepted: false, reason: 'not-open' });
});
```
