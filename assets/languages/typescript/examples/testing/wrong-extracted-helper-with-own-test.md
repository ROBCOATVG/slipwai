```typescript
// prepare-participant-data.ts (new file, one caller)
export const prepareParticipantData = (items: Item[]) => ({
  yourClaims: items.filter(i => i.isClaimed && i.isClaimedByCurrentUser),
  available: items.filter(i => !i.isClaimedByCurrentUser),
});

// prepare-participant-data.test.ts (tests the helper directly)
it('filters claims', () => { ... });
```
