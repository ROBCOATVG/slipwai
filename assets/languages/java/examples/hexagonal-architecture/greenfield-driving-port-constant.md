```java
/** The driving port, first. It says what the application does, before anything does it. */
public interface ForCalculatingTaxes {
    Money taxOn(Money amount);
}

/** The first implementation returns a constant — and the test expects the constant. */
@Test
void returnsTheFlatPlaceholderTax() {
    ForCalculatingTaxes calculator = new TaxCalculation();

    assertThat(calculator.taxOn(Money.of(100, Currency.GBP))).isEqualTo(Money.of(0, Currency.GBP));
}
```
