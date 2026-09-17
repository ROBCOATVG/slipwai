```typescript
type Order =
  | { readonly status: 'draft'; readonly items: ReadonlyArray<OrderItem> }
  | { readonly status: 'placed'; readonly items: ReadonlyArray<OrderItem>; readonly placedAt: Date }
  | { readonly status: 'shipped'; readonly items: ReadonlyArray<OrderItem>; readonly placedAt: Date; readonly shippedAt: Date; readonly trackingNumber: string };
```
