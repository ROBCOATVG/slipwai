```typescript
type OrderDecision =
  | { readonly accepted: true; readonly events: readonly OrderEvent[] }
  | { readonly accepted: false; readonly reason: 'order-not-draft' | 'order-not-placed' };

// 1. Decide: command + current state → an explicit acceptance or rejection
const decide = (command: OrderCommand, state: OrderState, now: Date): OrderDecision => {
  switch (command.type) {
    case 'place': {
      if (state.status !== 'draft') return { accepted: false, reason: 'order-not-draft' };
      return { accepted: true, events: [{ type: 'OrderPlaced', items: state.items, placedAt: now }] };
    }
    case 'ship': {
      if (state.status !== 'placed') return { accepted: false, reason: 'order-not-placed' };
      return { accepted: true, events: [{ type: 'OrderShipped', trackingNumber: command.trackingNumber }] };
    }
    default: { const _: never = command; return _; }
  }
};

// 2. Evolve: state + event → new state (pure state transformation).
// OrderState is a discriminated union of lifecycle phases (see "Make Illegal
// States Unrepresentable"), so each case builds the full target variant —
// spreading a draft state into a shipped shape would not type-check.
const evolve = (state: OrderState, event: OrderEvent): OrderState => {
  switch (event.type) {
    case 'OrderPlaced': {
      if (state.status !== 'draft') {
        throw new Error(`Corrupt order history: OrderPlaced cannot follow ${state.status}`);
      }
      return { status: 'placed', items: event.items, placedAt: event.placedAt };
    }
    case 'OrderShipped': {
      if (state.status !== 'placed') {
        throw new Error(`Corrupt order history: OrderShipped cannot follow ${state.status}`);
      }
      return { ...state, status: 'shipped', trackingNumber: event.trackingNumber };
    }
    default: { const _: never = event; return _; }
  }
};

// 3. Initial state
const initialState: OrderState = { status: 'draft', items: [] };
```
