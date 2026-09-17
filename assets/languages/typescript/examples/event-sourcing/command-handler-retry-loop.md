```typescript
const makeCommandHandler =
  <State, C extends { type: string }, E extends { type: string }>(
    decider: Decider<State, C, E>,
    store: EventStore<E>,
    maxAttempts = 3,
  ) =>
  async (streamId: StreamId, command: C): Promise<CommandResult> => {
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      const { events, version } = await store.readStream(streamId);       // load
      const state = events.reduce(decider.evolve, decider.initialState);  // rehydrate (pure)

      const decision = decider.decide(command, state);                    // decide (pure)
      if (!decision.accepted) return { success: false, reason: decision.reason };

      const outcome = await store.appendToStream(streamId, decision.events, { expectedVersion: version });
      if (outcome === 'ok') return { success: true, events: decision.events };
      // version-conflict: the stream moved under us — loop to reload and re-decide against fresh state
    }
    return { success: false, reason: 'concurrent-modification' };
  };
```
