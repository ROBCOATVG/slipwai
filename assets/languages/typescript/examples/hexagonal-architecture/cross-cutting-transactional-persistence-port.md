```typescript
// Application-owned driven port: one semantic operation must save both or neither.
type StoredOccasion = { readonly value: Occasion; readonly version: number };

interface PledgePersistence {
  readonly findOccasionById: (id: OccasionId) => Promise<StoredOccasion | undefined>;
  readonly saveWithOutbox: (
    occasion: Occasion,
    events: readonly PledgeRecorded[],
    expectedVersion: number,
  ) => Promise<'saved' | 'conflict'>;
}

// Driven adapter owns the database transaction mechanics.
const createDrizzlePledgePersistence = (db: Database): PledgePersistence => ({
  findOccasionById: async (id) => {
    const row = await db.select().from(occasions).where(eq(occasions.id, id)).get();
    return row ? { value: toOccasion(row), version: row.version } : undefined;
  },
  saveWithOutbox: async (occasion, events, expectedVersion) =>
    db.transaction(async (tx) => {
      const updated = await tx.update(occasions)
        .set({ ...toRow(occasion), version: expectedVersion + 1 })
        .where(and(
          eq(occasions.id, occasion.id),
          eq(occasions.version, expectedVersion),
        ))
        .returning({ id: occasions.id });
      if (updated.length !== 1) return 'conflict';
      await tx.insert(outbox).values(events.map(toOutboxRow));
      return 'saved';
    }),
});
```
