```java
@Test
void callsTheValidator() {
    Validator validator = mock(Validator.class);

    validator.validate(payment);

    verify(validator).validate(payment);  // asserts that the test called its own mock
}
```
