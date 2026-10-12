```typescript
const rehydrate = <State, C extends { type: string }, E extends { type: string }>(
  decider: Decider<State, C, E>,
  events: readonly E[],
): State => events.reduce(decider.evolve, decider.initialState);
```
