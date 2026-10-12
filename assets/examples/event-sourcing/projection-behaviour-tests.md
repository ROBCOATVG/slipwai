```typescript
const accountEnvelope = (
  data: AccountEvent,
  globalPosition: bigint,
  streamId: StreamId = accountId,
): AccountProjectionEnvelope => ({ streamId, globalPosition, data });

it('should reflect net balance from a sequence of account events', () => {
  const view = [
    accountEnvelope(opened(), 1n),
    accountEnvelope(deposited(10_000), 2n),
    accountEnvelope(withdrawn(3_000), 3n),
  ].reduce(apply, emptyBalanceView);

  expect(view).toEqual({
    status: 'open',
    accountId,
    currency: 'GBP',
    balanceMinorUnits: 7_000,
  });
});

it('should surface a duplicate account opening as corrupt projection history', () => {
  const history = [
    accountEnvelope(opened('GBP'), 1n),
    accountEnvelope(opened('EUR'), 2n),
  ];

  expect(() => history.reduce(apply, emptyBalanceView))
    .toThrow('Corrupt balance projection');
});
```
