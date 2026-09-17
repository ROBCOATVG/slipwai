```typescript
// packages/reporting/hexagon/application/src/dashboard-status.ts — provider-free policy
const toDashboardCard = (row: DashboardRow, now: Date): DashboardCard => ({
  title: row.eventTitle,
  emoji: row.occasionEmoji,
  daysAway: differenceInDays(parseISO(row.eventDate), now),
  savings: buildSavingsDisplay(row.savedAmount, row.targetAmount, now),
  isUrgent: differenceInDays(parseISO(row.eventDate), now) < 30,
});
```
