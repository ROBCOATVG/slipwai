```java
@Test
void rejectsAPaymentWithANegativeAmount() {
    List<String> problems = validate(aPayment().amountMinorUnits(-100).build());

    assertThat(problems).containsExactly("amount must be positive");
}
```
