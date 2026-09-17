```java
@Test
void reflectsDepositsAndWithdrawalsInWhatIsAvailableToWithdraw() {
    AccountState state = rehydrate(decider, List.of(opened(), deposited(10_000), withdrawn(3_000)));

    // The behaviour, not the field: £70 may be taken out and £70.01 may not. Nothing here reads the
    // balance directly, so evolve stays free to change how it represents one.
    assertThat(decider.decide(new AccountCommand.Withdraw(money(7_000)), state))
            .isInstanceOf(Decision.Accepted.class);
    assertThat(decider.decide(new AccountCommand.Withdraw(money(7_001)), state))
            .isEqualTo(Decision.reject("insufficient-funds"));
}
```
