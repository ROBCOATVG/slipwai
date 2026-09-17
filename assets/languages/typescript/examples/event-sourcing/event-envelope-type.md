```typescript
// Correlation and causation are UUIDs, and branded so the compiler knows it. Two brands rather
// than one alias used twice: they sit side by side below and are both strings underneath, so
// swapping them is invisible at runtime — and it destroys the one thing they exist for.
type CorrelationId = string & { readonly __brand: 'CorrelationId' };
type CausationId = string & { readonly __brand: 'CausationId' };

type EventEnvelope<T extends string, TData> = {
  readonly id: string;             // unique event id (UUID) — idempotency + causation target
  readonly type: T;                // event type name (a string, for tolerant deserialization)
  readonly streamId: string;       // the aggregate instance
  readonly version: number;        // per-stream position (optimistic concurrency)
  readonly globalPosition: bigint;  // store-wide order (subscriptions/projections)
  readonly timestamp: string;      // ISO-8601, assigned by the store
  readonly data: TData;            // the domain payload
  readonly metadata: {
    readonly correlationId: CorrelationId; // ties one whole business transaction together
    readonly causationId?: CausationId;    // the message that directly caused this event
    // + optional: userId, tenantId, schemaVersion
  };
};
```
