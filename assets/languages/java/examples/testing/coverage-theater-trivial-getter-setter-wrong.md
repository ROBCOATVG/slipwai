```java
@Test
void setsTheRetryLimit() {
    worker.setRetryLimit(3);

    assertThat(worker.getRetryLimit()).isEqualTo(3);  // asserts that a field holds what was put in it
}
```
