```typescript
type OccasionId = string & { readonly __brand: 'OccasionId' };
type GiftIdeaId = string & { readonly __brand: 'GiftIdeaId' };

const createOccasionId = (raw: string): OccasionId => {
  if (!raw.trim()) throw new Error('OccasionId cannot be empty');
  return raw as OccasionId; // justified: factory validates, then brands
};
```
