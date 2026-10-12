```typescript
it('should reflect deposits and withdrawals in the balance available to withdraw', () => {
  const state = [opened(), deposited(10_000), withdrawn(3_000)].reduce(evolve, initialState);

  // behaviour: £70 is available, £70.01 is not
  expect(decide({ type: 'Withdraw', amount: money(7_000) }, state).accepted).toBe(true);
  expect(decide({ type: 'Withdraw', amount: money(7_001) }, state).accepted).toBe(false);
});
```
