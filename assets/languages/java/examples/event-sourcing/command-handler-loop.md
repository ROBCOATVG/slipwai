```java
/** The use case: load, rehydrate, decide, append. The only impure steps are the first and the last. */
CommandResult handleCommand(EventStore<AccountEvent> store, String streamId, AccountCommand command) {
    // 1. LOAD the stream, and the version it was read at
    EventStore.Stream<AccountEvent> stream = store.readStream(streamId);

    // 2. REHYDRATE by folding — pure
    AccountState state = rehydrate(decider, stream.events());

    // 3. DECIDE — pure business logic
    if (decider.decide(command, state) instanceof Decision.Rejected<AccountEvent> rejected) {
        return CommandResult.refused(rejected.reason());
    }
    Decision.Accepted<AccountEvent> accepted =
            (Decision.Accepted<AccountEvent>) decider.decide(command, state);

    // 4. APPEND, asserting the stream has not moved since step 1
    EventStore.AppendOutcome outcome =
            store.appendToStream(streamId, accepted.events(), stream.version());
    return outcome == EventStore.AppendOutcome.VERSION_CONFLICT
            ? CommandResult.refused("concurrent-modification")
            : CommandResult.accepted(accepted.events());
}
```
