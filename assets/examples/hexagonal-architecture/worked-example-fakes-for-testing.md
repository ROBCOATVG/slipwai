```typescript
// packages/gifting/testing/fakes/src/fake-pledge-persistence.ts
const createFakePledgePersistence = (
  initial: readonly Occasion[] = [],
): PledgePersistence & {
  readonly savedEntities: readonly Occasion[];
  readonly outboxEvents: readonly PledgeRecorded[];
} => {
  const store = new Map(initial.map(o => [o.id, { value: o, version: 0 }]));
  const saved: Occasion[] = [];
  const outbox: PledgeRecorded[] = [];
  return {
    findOccasionById: async (id) => store.get(id),
    saveWithOutbox: async (occasion, events, expectedVersion) => {
      const current = store.get(occasion.id);
      if (!current || current.version !== expectedVersion) return 'conflict';
      store.set(occasion.id, { value: occasion, version: expectedVersion + 1 });
      saved.push(occasion);
      outbox.push(...events);
      return 'saved';
    },
    get savedEntities() { return saved; },
    get outboxEvents() { return outbox; },
  };
};

// packages/gifting/testing/fakes/src/fake-pledge-projection.ts
const createFakePledgeProjection = (): PledgeProjection & {
  readonly records: readonly PledgeRecorded[];
} => {
  const records = new Map<PledgeId, PledgeRecorded>();
  return {
    recordFrom: async (event) => {
      if (!records.has(event.id)) records.set(event.id, event);
    },
    get records() { return [...records.values()]; },
  };
};
```
