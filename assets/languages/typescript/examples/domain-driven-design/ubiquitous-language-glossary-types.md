```typescript
// ✅ Uses domain language
type GiftIdea = {
  readonly id: GiftIdeaId;
  readonly description: string;
  readonly occasion: OccasionId;
  readonly estimatedCost: Money;
  readonly status: 'proposed' | 'selected' | 'purchased';
};

// ❌ Technical jargon
type Item = { readonly id: string; readonly text: string; readonly parentId: string; };
```
