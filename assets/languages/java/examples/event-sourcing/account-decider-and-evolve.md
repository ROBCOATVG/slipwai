```java
// domain/account/AccountDecider.java — pure, imports nothing from infrastructure

sealed interface AccountState {
    record Unopened() implements AccountState { }

    record Open(Money balance) implements AccountState { }
}

sealed interface AccountCommand {
    record Open(Currency currency) implements AccountCommand { }

    record Deposit(Money amount) implements AccountCommand { }

    record Withdraw(Money amount) implements AccountCommand { }
}

sealed interface AccountEvent {
    record AccountOpened(Currency currency) implements AccountEvent { }

    record MoneyDeposited(Money amount) implements AccountEvent { }

    record MoneyWithdrawn(Money amount) implements AccountEvent { }
}

/** Minor units as a long, and never a double: a balance is a count of pennies, not a measurement. */
record Money(long minorUnits, Currency currency) {

    Money {
        if (minorUnits < 0) {
            throw new IllegalArgumentException("money cannot be negative: " + minorUnits);
        }
    }

    boolean isPositive() {
        return minorUnits > 0;
    }

    Money plus(Money other) {
        requireSameCurrency(other);
        return new Money(Math.addExact(minorUnits, other.minorUnits), currency);
    }

    Money minus(Money other) {
        requireSameCurrency(other);
        return new Money(Math.subtractExact(minorUnits, other.minorUnits), currency);
    }

    private void requireSameCurrency(Money other) {
        if (currency != other.currency) {
            throw new IllegalArgumentException("currency mismatch: " + currency + " and " + other.currency);
        }
    }
}

final class AccountDecider implements Decider<AccountState, AccountCommand, AccountEvent> {

    @Override
    public AccountState initialState() {
        return new AccountState.Unopened();
    }

    /** What SHOULD happen. Every invariant lives here, and nowhere else. */
    @Override
    public Decision<AccountEvent> decide(AccountCommand command, AccountState state) {
        return switch (command) {
            case AccountCommand.Open open -> state instanceof AccountState.Open
                    ? Decision.reject("already-open")
                    : Decision.accept(new AccountEvent.AccountOpened(open.currency()));
            case AccountCommand.Deposit deposit -> switch (state) {
                case AccountState.Unopened unopened -> Decision.reject("not-open");
                case AccountState.Open open -> {
                    if (!deposit.amount().isPositive()) {
                        yield Decision.reject("invalid-amount");
                    }
                    if (deposit.amount().currency() != open.balance().currency()) {
                        yield Decision.reject("currency-mismatch");
                    }
                    yield Decision.accept(new AccountEvent.MoneyDeposited(deposit.amount()));
                }
            };
            case AccountCommand.Withdraw withdraw -> switch (state) {
                case AccountState.Unopened unopened -> Decision.reject("not-open");
                case AccountState.Open open -> {
                    if (!withdraw.amount().isPositive()) {
                        yield Decision.reject("invalid-amount");
                    }
                    if (withdraw.amount().currency() != open.balance().currency()) {
                        yield Decision.reject("currency-mismatch");
                    }
                    if (withdraw.amount().minorUnits() > open.balance().minorUnits()) {
                        yield Decision.reject("insufficient-funds");
                    }
                    yield Decision.accept(new AccountEvent.MoneyWithdrawn(withdraw.amount()));
                }
            };
        };
    }

    /**
     * Applies facts. A known event that cannot follow this state is corrupt history rather than a no-op:
     * silently ignoring it rebuilds a balance that never existed, and nothing downstream would notice.
     */
    @Override
    public AccountState evolve(AccountState state, AccountEvent event) {
        return switch (event) {
            case AccountEvent.AccountOpened opened -> {
                if (!(state instanceof AccountState.Unopened)) {
                    throw corruptHistory(state, event);
                }
                yield new AccountState.Open(new Money(0, opened.currency()));
            }
            case AccountEvent.MoneyDeposited deposited -> {
                if (!(state instanceof AccountState.Open open) || !deposited.amount().isPositive()) {
                    throw corruptHistory(state, event);
                }
                yield new AccountState.Open(open.balance().plus(deposited.amount()));
            }
            case AccountEvent.MoneyWithdrawn withdrawn -> {
                if (!(state instanceof AccountState.Open open)
                        || !withdrawn.amount().isPositive()
                        || withdrawn.amount().minorUnits() > open.balance().minorUnits()) {
                    throw corruptHistory(state, event);
                }
                yield new AccountState.Open(open.balance().minus(withdrawn.amount()));
            }
        };
    }

    private static IllegalStateException corruptHistory(AccountState state, AccountEvent event) {
        return new IllegalStateException("Corrupt account stream: %s cannot follow %s"
                .formatted(event.getClass().getSimpleName(), state.getClass().getSimpleName()));
    }
}
```
