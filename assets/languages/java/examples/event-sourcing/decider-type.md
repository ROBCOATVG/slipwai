```java
/**
 * A decider: the initial state, what should happen, and what a fact does to state. Three pure functions
 * and no infrastructure type in sight, which is what makes the whole thing testable in memory.
 */
public interface Decider<S, C, E> {

    S initialState();

    /** What SHOULD happen? Enforces the invariants. Never touches a clock, a store or a network. */
    Decision<E> decide(C command, S state);

    /** Applies a fact that has already happened. Cannot reject: history is not up for debate. */
    S evolve(S state, E event);

    /** Optional: a state after which no command is accepted. */
    default boolean isTerminal(S state) {
        return false;
    }
}
```
