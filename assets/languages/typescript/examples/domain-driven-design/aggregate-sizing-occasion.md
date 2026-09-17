```typescript
// ❌ TOO LARGE — User doesn't need to be in the Occasion aggregate
type Occasion = {
  readonly organizer: User;         // Embedded user — wrong!
  readonly contributors: User[];    // Embedded users — wrong!
  readonly giftIdeas: GiftIdea[];
};

// ✅ RIGHT SIZE — only what's needed for consistency
type Occasion = {
  readonly organizerId: UserId;     // Reference by ID
  readonly giftIdeas: ReadonlyArray<GiftIdea>;  // Owned — needed for budget invariant
  readonly budget: Money;           // Owned — needed for budget invariant
};
```
