```typescript
const rehydrate = (events: readonly AccountEvent[]): AccountState =>
  events.reduce(evolve, initialState);
```
