```java
@Test
void rejectsANegativeAmount() {
    PaymentResult result = processPayment(aPayment().amountMinorUnits(-100).build());

    assertThat(result).isInstanceOf(PaymentResult.Rejected.class);
    assertThat(((PaymentResult.Rejected) result).reason()).contains("must be positive");
}

@Test
void rejectsACvvThatIsTooShort() {
    PaymentResult result = processPayment(aPayment().cvv("12").build());

    assertThat(result).isInstanceOf(PaymentResult.Rejected.class);
    assertThat(((PaymentResult.Rejected) result).reason()).contains("CVV");
}

@Test
void processesAValidPayment() {
    PaymentResult result = processPayment(aPayment().amountMinorUnits(10_000).cvv("123").build());

    assertThat(result).isInstanceOf(PaymentResult.Settled.class);
    assertThat(((PaymentResult.Settled) result).transactionId()).isNotBlank();
}
```
