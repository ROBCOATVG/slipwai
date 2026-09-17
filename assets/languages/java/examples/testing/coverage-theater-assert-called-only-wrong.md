```java
@Test
void processesPayment() {
    Processor processor = mock(Processor.class);

    handlePayment(payment, processor);

    verify(processor).process(payment);  // so what? nothing asserts what came back
}
```
