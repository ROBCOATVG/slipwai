```java
// Every validation branch exercised through processPayment, with no test naming the validator.
@Test
void rejectsANegativeAmount() {
    assertThat(processPayment(aPayment().amountMinorUnits(-100).build()))
            .isInstanceOf(PaymentResult.Rejected.class);
}

@Test
void rejectsAnAmountOverTheLimit() {
    assertThat(processPayment(aPayment().amountMinorUnits(1_500_000).build()))
            .isInstanceOf(PaymentResult.Rejected.class);
}

@Test
void rejectsACvvThatIsTooShort() {
    assertThat(processPayment(aPayment().cvv("12").build()))
            .isInstanceOf(PaymentResult.Rejected.class);
}

@Test
void settlesAValidPayment() {
    assertThat(processPayment(aPayment().build())).isInstanceOf(PaymentResult.Settled.class);
}
```
