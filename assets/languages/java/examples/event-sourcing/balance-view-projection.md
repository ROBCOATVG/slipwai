```java
// A projection is a fold from events to a read-optimised row.
sealed interface BalanceView {
    record Unopened() implements BalanceView { }

    record Open(String accountId, long balanceMinorUnits, Currency currency) implements BalanceView { }
}

static final BalanceView EMPTY = new BalanceView.Unopened();

/**
 * Applies one envelope. A known event that cannot follow this view is corrupt history — throwing stops the
 * projection at the event it cannot explain, which is recoverable; carrying on produces a balance that was
 * never true, which is not.
 */
static BalanceView applyToBalanceView(BalanceView view, EventEnvelope<AccountEvent> envelope) {
    return switch (envelope.data()) {
        case AccountEvent.AccountOpened opened -> {
            if (!(view instanceof BalanceView.Unopened)) {
                throw corruptProjection(view, envelope);
            }
            yield new BalanceView.Open(envelope.streamId(), 0, opened.currency());
        }
        case AccountEvent.MoneyDeposited deposited -> {
            BalanceView.Open open = requireOpen(view, envelope, deposited.amount());
            yield new BalanceView.Open(
                    open.accountId(),
                    Math.addExact(open.balanceMinorUnits(), deposited.amount().minorUnits()),
                    open.currency());
        }
        case AccountEvent.MoneyWithdrawn withdrawn -> {
            BalanceView.Open open = requireOpen(view, envelope, withdrawn.amount());
            if (withdrawn.amount().minorUnits() > open.balanceMinorUnits()) {
                throw corruptProjection(view, envelope);
            }
            yield new BalanceView.Open(
                    open.accountId(),
                    open.balanceMinorUnits() - withdrawn.amount().minorUnits(),
                    open.currency());
        }
    };
}

/** The checks every money event shares: the right view, the right stream, a usable amount. */
private static BalanceView.Open requireOpen(
        BalanceView view, EventEnvelope<AccountEvent> envelope, Money amount) {
    if (!(view instanceof BalanceView.Open open)
            || !open.accountId().equals(envelope.streamId())
            || !amount.isPositive()
            || amount.currency() != open.currency()) {
        throw corruptProjection(view, envelope);
    }
    return open;
}

private static IllegalStateException corruptProjection(
        BalanceView view, EventEnvelope<AccountEvent> envelope) {
    return new IllegalStateException("Corrupt balance projection: %s cannot follow %s at position %d"
            .formatted(envelope.type(), view.getClass().getSimpleName(), envelope.globalPosition()));
}
```
