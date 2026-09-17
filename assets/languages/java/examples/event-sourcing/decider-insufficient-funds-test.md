```java
// An ordinary behaviour test through the public decider. The returned events *are* the observable
// behaviour of decide(), so nothing here reaches for a mock or a spy.
@Test
void refusesAWithdrawalThatExceedsTheBalance() {
    AccountState state = rehydrate(decider, List.of(opened(), deposited(5_000)));

    Decision<AccountEvent> decision = decider.decide(new AccountCommand.Withdraw(money(10_000)), state);

    assertThat(decision).isEqualTo(Decision.reject("insufficient-funds"));
}

@Test
void recordsADepositAsAMoneyDepositedEvent() {
    AccountState state = rehydrate(decider, List.of(opened()));

    Decision<AccountEvent> decision = decider.decide(new AccountCommand.Deposit(money(5_000)), state);

    assertThat(decision).isEqualTo(Decision.accept(new AccountEvent.MoneyDeposited(money(5_000))));
}
```
