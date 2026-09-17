```typescript
// ❌ Pure but NOT domain — formats for human display
export const formatEventDate = (date: string | null) =>
  date ? format(parseISO(date), "MMMM d, yyyy") : undefined;
// → Belongs in presentation code; a hexagonal app may place it at the driving edge

// ✅ Pure AND domain — business rule that affects behavior
// The application supplies current time as data; domain code does not read a clock.
export const isPastEvent = (eventDate: Date | null, now: Date) =>
  eventDate ? eventDate.getTime() < now.getTime() : false;
// → Belongs in domain policy for events

// ✅ Pure AND domain — business calculation
export const calculateCommittedTotal = (items: readonly GiftItem[]) =>
  items.filter(i => i.status !== "idea").reduce((sum, i) => sum + i.pricePence, 0);
// → Belongs in domain policy for budgets
```
