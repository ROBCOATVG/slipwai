```java
// A field on the test class, mutated by one case and read by another.
private final Order order = anOrder().build();

@Test
void one() {
    order.addItem(anItem().build());   // mutates state the next test reads
}

@Test
void two() {
    assertThat(order.items()).hasSize(1);   // passes or fails depending on execution order
}
```
