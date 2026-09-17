```typescript
type OrderPlacedV1 = {
  readonly type: 'OrderPlaced'; readonly version: 1;
  readonly orderId: string; readonly totalMinorUnits: number; readonly currency: Currency;
};
type OrderPlacedV2 = {
  readonly type: 'OrderPlaced'; readonly version: 2;
  readonly orderId: string;
  readonly totalAmount: { readonly minorUnits: number; readonly currency: Currency }; // structural change
};
type OrderPlaced = OrderPlacedV2; // the shape the domain uses today

const upcastOrderPlacedV1toV2 = (e: OrderPlacedV1): OrderPlacedV2 => ({
  type: 'OrderPlaced',
  version: 2,
  orderId: e.orderId,
  totalAmount: { minorUnits: e.totalMinorUnits, currency: e.currency },
});

// On read: dispatch on the stored version and upcast forward to the current shape.
// A discriminated union of versions keeps this exhaustive and cast-free.
const upcastOrderPlaced = (raw: OrderPlacedV1 | OrderPlacedV2): OrderPlaced => {
  switch (raw.version) {
    case 1: return upcastOrderPlacedV1toV2(raw);
    case 2: return raw;
    default: { const _: never = raw; return _; }
  }
};
```
