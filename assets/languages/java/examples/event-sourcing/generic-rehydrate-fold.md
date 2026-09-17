```java
/**
 * A left fold over the stream, for any decider. `reduce` would need the accumulator and the element to be
 * the same type, and they are not — state and event are deliberately different — so this is a plain loop.
 */
static <S, C, E> S rehydrate(Decider<S, C, E> decider, List<E> events) {
    S state = decider.initialState();
    for (E event : events) {
        state = decider.evolve(state, event);
    }
    return state;
}
```
