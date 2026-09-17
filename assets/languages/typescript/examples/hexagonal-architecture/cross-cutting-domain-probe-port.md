```typescript
// Driven port — application-owned because the use case consumes it
interface PledgeInstrumentation {
  readonly pledgeRejected: (reason: PledgeRejectionReason, occasionId: OccasionId) => void;
  readonly pledgeAccepted: (amount: Money, occasionId: OccasionId) => void;
}

// Use case announces domain facts; no log levels, no metric names, no framework types
const createPledgingToOccasions = (
  persistence: PledgePersistence,
  instrumentation: PledgeInstrumentation,
): ForPledgingToOccasions => ({ ... });

// Adapter decides severity, metric names, span attributes — swappable without touching a use case
const createTelemetryPledgeInstrumentation = (logger: Logger): PledgeInstrumentation => ({
  pledgeRejected: (reason, occasionId) => logger.warn('Pledge rejected', { reason, occasionId }),
  pledgeAccepted: (amount, occasionId) => logger.info('Pledge accepted', {
    minorUnits: amount.minorUnits,
    currency: amount.currency,
    occasionId,
  }),
});
```
