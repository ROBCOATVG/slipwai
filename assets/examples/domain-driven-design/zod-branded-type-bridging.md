```typescript
// Schema at trust boundary — parses raw strings into branded types
const PledgeInputSchema = z.object({
  occasionId: z.string().min(1).transform(createOccasionId),
  contributorId: z.string().min(1).transform(createContributorId),
  amount: z.object({ minorUnits: z.number().int().safe().positive(), currency: CurrencySchema }),
});

// Reconstitution from persistence — same pattern, used at the integration boundary
// (a driven adapter in hexagonal architecture loads the gift ideas alongside the row)
const toOccasion = (row: OccasionRow, giftIdeas: ReadonlyArray<GiftIdea>): Occasion => ({
  id: createOccasionId(row.id),
  name: row.name,
  giftIdeas,
  budget: createMoney(row.budgetMinorUnits, parseCurrency(row.budgetCurrency)),
  totalPledged: createMoney(row.pledgedMinorUnits, parseCurrency(row.budgetCurrency)),
  isFundingClosed: row.isFundingClosed,
});
```
