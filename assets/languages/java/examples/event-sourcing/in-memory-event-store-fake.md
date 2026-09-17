```java
/**
 * A real implementation of the port backed by a map — not a mock. It has behaviour: it refuses a stale
 * expected version, which is the one thing a mock would have to be told to do and would then never
 * disagree with the caller about.
 */
final class InMemoryEventStore<E> implements EventStore<E> {

    private final Map<String, List<E>> streams = new HashMap<>();

    @Override
    public Stream<E> readStream(String streamId) {
        List<E> events = List.copyOf(streams.getOrDefault(streamId, List.of()));
        return new Stream<>(events, events.size() - 1);
    }

    @Override
    public AppendOutcome appendToStream(String streamId, List<E> events, int expectedVersion) {
        List<E> current = streams.getOrDefault(streamId, List.of());
        if (current.size() - 1 != expectedVersion) {
            return AppendOutcome.VERSION_CONFLICT;
        }
        List<E> updated = new ArrayList<>(current);
        updated.addAll(events);
        streams.put(streamId, updated);
        return AppendOutcome.APPENDED;
    }
}

@Test
void persistsADepositSoALaterWithdrawalSeesTheFunds() {
    CommandHandler<AccountState, AccountCommand, AccountEvent> handle =
            new CommandHandler<>(decider, new InMemoryEventStore<>());
    handle.handle(streamId, new AccountCommand.Open(GBP));
    handle.handle(streamId, new AccountCommand.Deposit(money(10_000)));

    CommandResult<AccountEvent> result =
            handle.handle(streamId, new AccountCommand.Withdraw(money(6_000)));

    assertThat(result.events()).containsExactly(new AccountEvent.MoneyWithdrawn(money(6_000)));
}

@Test
void refusesAnAppendMadeAgainstAStaleVersion() {
    EventStore<AccountEvent> store = new InMemoryEventStore<>();
    store.appendToStream(streamId, List.of(opened()), -1);

    EventStore.AppendOutcome outcome =
            store.appendToStream(streamId, List.of(deposited(10)), -1);   // stale

    assertThat(outcome).isEqualTo(EventStore.AppendOutcome.VERSION_CONFLICT);
}
```
