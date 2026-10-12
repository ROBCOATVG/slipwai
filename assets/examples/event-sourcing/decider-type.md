```typescript
type Decider<State, C extends { readonly type: string }, E extends { readonly type: string }> = {
  readonly initialState: State;
  readonly decide: (command: C, state: State) => Decision<E>;
  readonly evolve: (state: State, event: E) => State;
  readonly isTerminal?: (state: State) => boolean;
};
```
