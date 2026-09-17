```java
/**
 * The clock is an input, not something the domain reads. `at` arrives from the edge, which is what makes
 * every rule that depends on time testable without freezing global state.
 */
record Deposit(Money amount, Instant at) implements AccountCommand { }
```
