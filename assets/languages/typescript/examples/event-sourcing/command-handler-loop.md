```typescript
// use-case: load → decide → append (with optimistic concurrency)
const handleCommand = async (
  store: EventStore<AccountEvent>,
  streamId: StreamId,
  command: AccountCommand,
): Promise<CommandResult> => {
  // 1. LOAD the stream's events (and the version we read at)
  const { events, version } = await store.readStream(streamId);

  // 2. REHYDRATE current state by folding — pure
  const state = events.reduce(evolve, initialState);

  // 3. DECIDE — pure business logic
  const decision = decide(command, state);
  if (!decision.accepted) return { success: false, reason: decision.reason };

  // 4. APPEND the new events, asserting the stream has not moved since we read it
  const outcome = await store.appendToStream(streamId, decision.events, { expectedVersion: version });
  if (outcome === 'version-conflict') return { success: false, reason: 'concurrent-modification' };

  return { success: true, events: decision.events };
};
```
