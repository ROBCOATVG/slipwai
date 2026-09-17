```java
@Test
void settlesAPaymentAndReportsTheTransaction() {
    PaymentResult result = handlePayment(aPayment().build());

    assertThat(result).isInstanceOf(PaymentResult.Settled.class);
    assertThat(((PaymentResult.Settled) result).transactionId()).isNotBlank();
}
```
