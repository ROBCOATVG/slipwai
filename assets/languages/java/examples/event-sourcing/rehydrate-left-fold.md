```java
AccountState rehydrate(List<AccountEvent> events) {
    AccountState state = decider.initialState();
    for (AccountEvent event : events) {
        state = decider.evolve(state, event);
    }
    return state;
}
```
