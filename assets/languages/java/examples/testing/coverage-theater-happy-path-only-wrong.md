```java
@Test
void validatesPayment() {
    assertThat(validate(aPayment().build())).isEmpty();  // only the happy path
}
// Missing: negative amounts, an amount over the limit, a short CVV, an absent currency.
```
