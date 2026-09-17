```java
/**
 * What a decision produced: facts, or a refusal naming the rule. A sealed interface, so a caller that
 * handles only one case does not compile.
 */
public sealed interface Decision<E> {

    record Accepted<E>(List<E> events) implements Decision<E> { }

    record Rejected<E>(String reason) implements Decision<E> { }

    static <E> Decision<E> accept(List<E> events) {
        return new Accepted<>(List.copyOf(events));
    }

    static <E> Decision<E> accept(E event) {
        return new Accepted<>(List.of(event));
    }

    static <E> Decision<E> reject(String reason) {
        return new Rejected<>(reason);
    }
}
```
