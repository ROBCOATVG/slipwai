```typescript
// Application/use case: receives identity and coordinates domain behaviour
const createPledgingToOccasions = (
  persistence: PledgePersistence,
): ForPledgingToOccasions => ({
  pledgeToOccasion: async (dto: { readonly principal: AuthenticatedPledger; ... }) => {
    // Application code doesn't check JWT tokens or session cookies.
    // It authorizes a provider-free principal and invokes domain rules.
  },
});
```
