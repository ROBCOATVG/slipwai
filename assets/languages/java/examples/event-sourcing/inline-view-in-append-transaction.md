```java
// materialisation: inline — the view is written in the same transaction as the append, so it never lags the
// write and read-your-writes costs nothing on this slice. Two things to know before choosing it.
//
// In Java the seam is the framework's: @Transactional. The Postgres store takes Transactions — the
// framework's transaction manager as a port — and asks it, per statement, which connection the current
// transaction is on. So does JdbcTemplate, so does Panache, so does whatever the project's own view
// repository is written with. Annotate the use case and the append and the view write are one transaction,
// with nothing wired between them; roll one back and both are gone. EventStore.inUnitOfWork opens the same
// transaction from code, for a caller that has no annotation to hang it on.
//
// The view must be scoped to the stream being appended. A view folding several streams cannot be kept
// atomic with one append: the row it writes is contended by every other stream's appends, which is a hot
// row and a cross-stream transaction wearing a projection's clothes. That view is async.

/**
 * This project's own view table — an ordinary repository, with nothing about it that knows an event store
 * exists.
 *
 * <p>That is the whole point of letting the framework own transactions: it needs no seam of its own. A
 * {@code JdbcTemplate} or a Panache entity inside an annotated method is already on the transaction's
 * connection, because binding a connection to a transaction is what the framework was doing all along.
 */
public interface BalanceViews {
    Optional<BalanceView> load(String accountId);

    void upsert(BalanceView view);
}

@ApplicationScoped // @Service under Spring Boot
public class DepositMoneyUseCase {

    private final EventStore store;
    private final BalanceViews views;

    // jakarta.transaction.Transactional under Quarkus,
    // org.springframework.transaction.annotation.Transactional under Spring Boot.
    @Transactional
    public DepositOutcome depositMoney(DepositMoney command) {
        List<CommittedEvent> history = store.read(command.accountId());
        Decision decision = accountDecider.decide(command, rehydrate(accountDecider, history));
        if (decision instanceof Decision.Rejected rejected) {
            // Nothing appended, nothing projected — and the transaction the annotation opened rolls back.
            return DepositOutcome.rejected(rejected);
        }

        AppendResult result = store.append(
                command.accountId(), EventStore.currentVersion(history), decision.events());
        if (result instanceof AppendResult.VersionConflict conflict) {
            // Contention, not failure: the caller re-reads and re-decides. Nothing is half-written, which
            // is the one thing inline gives you for free.
            return DepositOutcome.conflict(conflict);
        }

        // The same BalanceView.apply the live and async versions use — the lifecycle decides what
        // maintains the view, never how it is computed. Only the new events are applied: refolding the
        // stream here would put the whole history on the write path, which inline exists to avoid.
        BalanceView view = views.load(command.accountId()).orElseGet(BalanceView::empty);
        List<CommittedEvent> appended = store.read(command.accountId());
        for (CommittedEvent committed : appended.subList(history.size(), appended.size())) {
            view = BalanceView.apply(view, new ProjectionEnvelope(
                    committed.streamId(), committed.globalPosition(), toDomainEvent(committed)));
        }
        views.upsert(view);
        return DepositOutcome.appended(result);
    }
}
```

An inline view is still a derivation, so it still needs the rebuild path: when the fold changes or turns out
to be wrong, the fix is to reset the view and replay `readAll(0)` through the same apply. Inline removes the
checkpoint and the subscription, not the obligation to be rebuildable.
