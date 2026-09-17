```java
@Test
void rejectsANegativeAmount() {
    assertThat(validate(aPayment().amountMinorUnits(-100).build())).isNotEmpty();
}

@Test
void rejectsAnAmountOverTheLimit() {
    assertThat(validate(aPayment().amountMinorUnits(1_500_000).build())).isNotEmpty();
}

@Test
void rejectsACvvThatIsTooShort() {
    assertThat(validate(aPayment().cvv("12").build())).isNotEmpty();
}

@Test
void acceptsAValidPayment() {
    assertThat(validate(aPayment().build())).isEmpty();
}
```
