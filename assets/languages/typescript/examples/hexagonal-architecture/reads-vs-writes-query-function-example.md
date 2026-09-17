```typescript
// Query function — JOINs across aggregates for display
// Lives at packages/reporting/adapters/driven/postgres/queries/, outside the hexagon
const getParticipantEventView = async (db: Database, eventId: string) => {
  return db.select({ ... })
    .from(events)
    .innerJoin(occasions, ...)
    .leftJoin(giftClaims, ...)
    .where(eq(events.id, eventId))
    .all();
};
```
