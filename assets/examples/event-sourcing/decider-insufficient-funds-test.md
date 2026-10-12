```typescript
// ✅ Ordinary behaviour-driven test through the public decider API.
// The returned events are the observable behaviour of the public `decide` function.

const openAccount = (currency: Currency = 'GBP'): AccountEvent =>
  ({ type: 'AccountOpened', currency });
const money = (minorUnits: number, currency: Currency = 'GBP'): Money => ({ minorUnits, currency });
const deposited = (minorUnits: number): AccountEvent => ({ type: 'MoneyDeposited', amount: money(minorUnits) });

it('should reject a withdrawal that exceeds the balance', () => {
  const state = [openAccount(), deposited(5_000)].reduce(evolve, initialState);

  const decision = decide({ type: 'Withdraw', amount: money(10_000) }, state);

  expect(decision).toEqual({ accepted: false, reason: 'insufficient-funds' });
});

it('should record a deposit as a MoneyDeposited event on an open account', () => {
  const state = [openAccount()].reduce(evolve, initialState);

  const decision = decide({ type: 'Deposit', amount: money(5_000) }, state);

  expect(decision).toEqual({ accepted: true, events: [{ type: 'MoneyDeposited', amount: money(5_000) }] });
});
```
