```typescript
const createFakeOrderRepo = (): OrderRepository & { readonly savedEntities: readonly Order[] } => {
  const saved: Order[] = [];
  const store = new Map<string, Order>();
  return {
    findById: async (id) => store.get(id),
    save: async (order) => { store.set(order.id, order); saved.push(order); },
    get savedEntities() { return saved; },
  };
};
```
