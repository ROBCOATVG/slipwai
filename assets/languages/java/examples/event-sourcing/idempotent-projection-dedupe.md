```java
/** A per-account row. `appliedThrough` is what makes a redelivery cost nothing. */
record BalanceRow(long balanceMinorUnits, int appliedThrough) { }

/** Applies an event at a version, ignoring anything at or below what this row has already seen. */
static BalanceRow project(BalanceRow row, AccountEvent.MoneyDeposited event, int version) {
    if (version <= row.appliedThrough()) {
        return row;
    }
    return new BalanceRow(
            Math.addExact(row.balanceMinorUnits(), event.amount().minorUnits()), version);
}

@Test
void doesNotDoubleCountARedeliveredEvent() {
    AccountEvent.MoneyDeposited event = new AccountEvent.MoneyDeposited(money(10_000));

    BalanceRow once = project(new BalanceRow(0, -1), event, 0);
    BalanceRow twice = project(once, event, 0);   // the same event, redelivered at the same version

    assertThat(once.balanceMinorUnits()).isEqualTo(10_000);
    assertThat(twice.balanceMinorUnits()).isEqualTo(10_000);   // not 20_000
}
```
