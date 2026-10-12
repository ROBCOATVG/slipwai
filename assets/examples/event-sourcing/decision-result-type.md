```typescript
type Decision<E, R extends string = string> =
  | { readonly accepted: true; readonly events: readonly E[] }
  | { readonly accepted: false; readonly reason: R };

const accept = <E>(events: readonly E[]): Decision<E, never> => ({ accepted: true, events });
const reject = <R extends string>(reason: R): Decision<never, R> => ({ accepted: false, reason });
```
