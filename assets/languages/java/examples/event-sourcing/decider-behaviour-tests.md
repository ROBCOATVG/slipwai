```java
// Event factories — complete, valid data, and no wall clock (see the testing skill's factory pattern).
private static final Currency GBP = Currency.GBP;

private static Money money(long minorUnits) {
    return new Money(minorUnits, GBP);
}

private static AccountEvent opened() {
    return new AccountEvent.AccountOpened(GBP);
}

private static AccountEvent deposited(long minorUnits) {
    return new AccountEvent.MoneyDeposited(money(minorUnits));
}

private static AccountEvent withdrawn(long minorUnits) {
    return new AccountEvent.MoneyWithdrawn(money(minorUnits));
}

@Test
void recordsADepositOnAnOpenAccount() {
    AccountState state = rehydrate(decider, List.of(opened()));

    Decision<AccountEvent> decision = decider.decide(new AccountCommand.Deposit(money(5_000)), state);

    assertThat(decision)
            .isEqualTo(Decision.accept(new AccountEvent.MoneyDeposited(money(5_000))));
}

@Test
void refusesAWithdrawalThatExceedsTheBalance() {
    AccountState state = rehydrate(decider, List.of(opened(), deposited(5_000)));

    Decision<AccountEvent> decision = decider.decide(new AccountCommand.Withdraw(money(10_000)), state);

    assertThat(decision).isEqualTo(Decision.reject("insufficient-funds"));
}

@Test
void refusesAnyOperationOnAnAccountThatWasNeverOpened() {
    Decision<AccountEvent> decision =
            decider.decide(new AccountCommand.Deposit(money(5_000)), decider.initialState());

    assertThat(decision).isEqualTo(Decision.reject("not-open"));
}
```
