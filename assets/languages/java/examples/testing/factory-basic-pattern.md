```java
static PaymentBuilder aPayment() {
    return new PaymentBuilder()
            .id(new PaymentId("pay-123"))
            .amountMinorUnits(10_000)
            .currency(Currency.GBP)
            .cvv("123");
}

@Test
void settlesAPaymentInAnotherCurrency() {
    PaymentResult result = processPayment(aPayment().currency(Currency.EUR).build());

    assertThat(result).isInstanceOf(PaymentResult.Settled.class);
}
```
