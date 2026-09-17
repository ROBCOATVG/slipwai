```java
/**
 * The same loop, retried. A version conflict means the stream moved: reload and re-decide against fresh
 * state rather than replaying a decision taken against state that no longer exists.
 */
final class CommandHandler<S, C, E> {

    private static final int MAX_ATTEMPTS = 3;

    private final Decider<S, C, E> decider;
    private final EventStore<E> store;

    CommandHandler(Decider<S, C, E> decider, EventStore<E> store) {
        this.decider = decider;
        this.store = store;
    }

    CommandResult<E> handle(String streamId, C command) {
        for (int attempt = 0; attempt < MAX_ATTEMPTS; attempt++) {
            EventStore.Stream<E> stream = store.readStream(streamId);   // load
            S state = rehydrate(decider, stream.events());              // rehydrate (pure)

            switch (decider.decide(command, state)) {                   // decide (pure)
                case Decision.Rejected<E> rejected -> {
                    return CommandResult.refused(rejected.reason());
                }
                case Decision.Accepted<E> accepted -> {
                    if (store.appendToStream(streamId, accepted.events(), stream.version())
                            == EventStore.AppendOutcome.APPENDED) {
                        return CommandResult.accepted(accepted.events());
                    }
                    // VERSION_CONFLICT: fall through and try again against reloaded state.
                }
            }
        }
        return CommandResult.refused("concurrent-modification");
    }
}
```
