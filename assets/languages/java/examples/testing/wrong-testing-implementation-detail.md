```java
// Testing HOW rather than WHAT: passes while the behaviour is broken, fails when the call is inlined.
@Test
void callsValidateAmount() {
    Validator validator = spy(new Validator());

    processPayment(payment, validator);

    verify(validator).validateAmount(any());
}

// Reaching past the public API. A package-private method exists so the class can be structured, not
// so a test can pin its structure.
@Test
void validatesCvvFormat() {
    assertThat(new Validator().validateCvv("123")).isTrue();
}

// Asserting internal state, which is the class's business and nobody else's.
@Test
void setsTheValidatedFlag() {
    processor.process(payment);

    assertThat(processor.validated).isTrue();
}
```
