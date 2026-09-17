```typescript
type GiftPurchasePhase =
  | { readonly step: 'awaiting-payment'; readonly occasionId: OccasionId }
  | { readonly step: 'awaiting-shipment'; readonly paymentId: string }
  | { readonly step: 'complete'; readonly trackingNumber: string }
  | { readonly step: 'failed'; readonly reason: string };

type GiftPurchaseProcess = {
  readonly phase: GiftPurchasePhase;
  readonly processedEventIds: readonly string[];
};

type ProcessReaction =
  | {
      readonly outcome: 'applied';
      readonly newState: GiftPurchaseProcess;
      readonly commands: readonly GiftPurchaseCommand[];
    }
  | {
      readonly outcome: 'duplicate' | 'out-of-order';
      readonly newState: GiftPurchaseProcess;
      readonly commands: readonly [];
    };

// Apply each event once and only in the phase that can consume it.
const advanceGiftPurchase = (
  state: GiftPurchaseProcess,
  event: GiftPurchaseEvent & { readonly id: string },
): ProcessReaction => {
  if (state.processedEventIds.includes(event.id)) {
    return { outcome: 'duplicate', newState: state, commands: [] };
  }

  const processedEventIds = [...state.processedEventIds, event.id];
  switch (event.type) {
    case 'PaymentSucceeded': {
      if (state.phase.step !== 'awaiting-payment') {
        return { outcome: 'out-of-order', newState: state, commands: [] };
      }
      return {
        outcome: 'applied',
        newState: {
          phase: { step: 'awaiting-shipment', paymentId: event.paymentId },
          processedEventIds,
        },
        commands: [{ type: 'ShipGift', paymentId: event.paymentId, idempotencyKey: event.id }],
      };
    }
    case 'PaymentFailed': {
      if (state.phase.step !== 'awaiting-payment') {
        return { outcome: 'out-of-order', newState: state, commands: [] };
      }
      return {
        outcome: 'applied',
        newState: {
          phase: { step: 'failed', reason: 'payment-declined' },
          processedEventIds,
        },
        commands: [{
          type: 'ReleaseBudgetHold',
          occasionId: state.phase.occasionId,
          idempotencyKey: event.id,
        }],
      };
    }
    case 'GiftShipped': {
      if (state.phase.step !== 'awaiting-shipment') {
        return { outcome: 'out-of-order', newState: state, commands: [] };
      }
      return {
        outcome: 'applied',
        newState: {
          phase: { step: 'complete', trackingNumber: event.trackingNumber },
          processedEventIds,
        },
        commands: [],
      };
    }
    default: { const _: never = event; return _; }
  }
};
```
