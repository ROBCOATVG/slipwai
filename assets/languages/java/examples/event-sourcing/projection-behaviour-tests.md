```java
private static EventEnvelope<AccountEvent> envelope(AccountEvent data, long globalPosition) {
    return new EventEnvelope<>(
            UUID.randomUUID(),
            data.getClass().getSimpleName(),
            ACCOUNT_ID,
            (int) globalPosition - 1,
            globalPosition,
            "2024-01-01T00:00:00Z",
            data,
            new EventEnvelope.Metadata("corr-1", ""));
}

@Test
void reflectsTheNetBalanceOfASequenceOfEvents() {
    BalanceView view = project(List.of(
            envelope(opened(), 1),
            envelope(deposited(10_000), 2),
            envelope(withdrawn(3_000), 3)));

    assertThat(view).isEqualTo(new BalanceView.Open(ACCOUNT_ID, 7_000, GBP));
}

@Test
void surfacesADuplicateAccountOpeningAsCorruptHistory() {
    List<EventEnvelope<AccountEvent>> history = List.of(
            envelope(new AccountEvent.AccountOpened(Currency.GBP), 1),
            envelope(new AccountEvent.AccountOpened(Currency.EUR), 2));

    assertThatThrownBy(() -> project(history))
            .isInstanceOf(IllegalStateException.class)
            .hasMessageContaining("Corrupt balance projection");
}
```
