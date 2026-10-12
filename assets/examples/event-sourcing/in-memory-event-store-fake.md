```typescript
// A real implementation of the port backed by a Map — not a mock. Because the
// port is typed EventStore<E>, the fake needs no casts anywhere.
const makeInMemoryStore = <E>(): EventStore<E> => {
  const streams = new Map<string, E[]>();
  return {
    readStream: async (id) => {
      const events = streams.get(id) ?? [];
      return { events, version: events.length };
    },
    appendToStream: async (id, events, { expectedVersion }) => {
      const current = streams.get(id) ?? [];
      if (current.length !== expectedVersion) return 'version-conflict';
      streams.set(id, [...current, ...events]);
      return 'ok';
    },
  };
};

it('should persist a deposit so a later withdrawal sees the funds', async () => {
  const handle = makeCommandHandler(accountDecider, makeInMemoryStore<AccountEvent>());
  await handle(streamId, { type: 'Open', currency: 'GBP' });
  await handle(streamId, { type: 'Deposit', amount: money(10_000) });

  const result = await handle(streamId, { type: 'Withdraw', amount: money(6_000) });

  expect(result).toEqual({
    success: true,
    events: [{ type: 'MoneyWithdrawn', amount: money(6_000) }],
  });
});

it('should reject a concurrent append made against a stale version', async () => {
  const store = makeInMemoryStore<AccountEvent>();
  await store.appendToStream(streamId, [opened()], { expectedVersion: 0 });

  const outcome = await store.appendToStream(streamId, [deposited(10)], { expectedVersion: 0 }); // stale

  expect(outcome).toBe('version-conflict');
});
```
