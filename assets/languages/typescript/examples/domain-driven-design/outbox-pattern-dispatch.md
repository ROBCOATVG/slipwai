```typescript
// The application contract requires one atomic aggregate + outbox operation.
const handlePlaceOrder = async (
  persistence: PlaceOrderPersistence,
  command: PlaceOrderCommand,
  now: Date,
): Promise<PlaceOrderResult> => {
  const stored = await persistence.findOrderById(command.orderId);
  if (!stored) return { success: false, reason: 'not-found' };

  const decision = decide(command, stored.state, now);
  if (!decision.accepted) return { success: false, reason: decision.reason };
  const events = decision.events;
  const newState = events.reduce(evolve, stored.state);

  // One compare-and-save operation persists aggregate + outbox or neither.
  const saved = await persistence.saveWithOutbox(newState, events, {
    expectedVersion: stored.version,
  });
  if (saved === 'conflict') return { success: false, reason: 'concurrent-change' };

  return { success: true, order: newState };
};

// Application-owned persistence contract — a driven port when hexagonal architecture is used.
interface PlaceOrderPersistence {
  readonly findOrderById: (id: OrderId) => Promise<StoredOrder | undefined>;
  readonly saveWithOutbox: (
    state: OrderState,
    events: readonly OrderEvent[],
    options: { readonly expectedVersion: number },
  ) => Promise<'saved' | 'conflict'>;
}
```
