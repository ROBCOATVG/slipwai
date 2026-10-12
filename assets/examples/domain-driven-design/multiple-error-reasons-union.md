```typescript
type CreateOrderResult =
  | { readonly success: true; readonly order: Order }
  | { readonly success: false; readonly reason:
      | 'empty-cart'
      | 'item-out-of-stock'
      | 'payment-declined'
      | 'address-invalid'
      | 'daily-limit-exceeded'
    };
```
