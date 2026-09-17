```typescript
// packages/reporting/adapters/driven/postgres/src/dashboard.ts — JOINs for display
const getDashboardCards = async (db: Database, userId: string) => {
  return db.select({
    eventTitle: events.title,
    occasionEmoji: occasions.emoji,
    savedAmount: savingsGoals.savedAmount,
    recipientName: recipients.name,
  })
  .from(events)
  .innerJoin(occasions, ...)
  .leftJoin(savingsGoals, ...)
  .innerJoin(recipients, ...)
  .where(eq(events.userId, userId))
  .all();
};
```
