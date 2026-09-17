```typescript
// packages/gifting/adapters/driven/postgres/src/drizzle-pledge-persistence.ts
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

// packages/gifting/adapters/driven/postgres/src/drizzle-pledge-projection.ts
const createDrizzlePledgeProjection = (db: Database): PledgeProjection => ({
  recordFrom: async (event) => {
    await db.insert(pledgeProjection).values(toProjectionRow(event))
      .onConflictDoNothing({
        target: pledgeProjection.eventId,
      });
  },
});
```
