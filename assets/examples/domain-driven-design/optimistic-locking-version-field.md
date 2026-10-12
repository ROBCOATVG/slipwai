```typescript
type Occasion = {
  readonly id: OccasionId;
  readonly version: number;  // incremented on each save
  readonly name: string;
  readonly budget: Money;
  readonly giftIdeas: ReadonlyArray<GiftIdea>;
};
```
