```typescript
type StoredOrder = {
  readonly state: OrderState;
  readonly version: number;
};

interface OrderRepository {
  readonly findById: (id: OrderId) => Promise<StoredOrder | undefined>;
  readonly save: (
    state: OrderState,
    options: { readonly expectedVersion: number },
  ) => Promise<'saved' | 'conflict'>;
}

const handlePlaceOrder = async (
  orderRepo: OrderRepository,
  notifier: OrderNotifier,
  command: PlaceOrderCommand,
  now: Date,
): Promise<PlaceOrderResult> => {
  const stored = await orderRepo.findById(command.orderId);
  if (!stored) return { success: false, reason: 'not-found' };

  const decision = decide(command, stored.state, now);
  if (!decision.accepted) return { success: false, reason: decision.reason };
  const events = decision.events;
  const newState = events.reduce(evolve, stored.state);
  const saved = await orderRepo.save(newState, { expectedVersion: stored.version });
  if (saved === 'conflict') return { success: false, reason: 'concurrent-change' };

  // Dispatch in-process — simple but non-durable
  for (const event of events) {
    await notifier.notify(event);
  }
  return { success: true, order: newState };
};
```
