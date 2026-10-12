```typescript
const describeOrder = (order: Order): string => {
  switch (order.status) {
    case 'draft': return `Draft with ${order.items.length} items`;
    case 'placed': return `Placed at ${order.placedAt.toISOString()}`;
    case 'shipped': return `Shipped: ${order.trackingNumber}`;
    default: { const _exhaustive: never = order; return _exhaustive; }
  }
};
```
