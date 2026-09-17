```typescript
// Application-owned repository contract — an inside-owned port when hexagonal architecture is used
interface OccasionRepository {
  readonly findById: (id: OccasionId) => Promise<Occasion | undefined>;
  readonly save: (occasion: Occasion) => Promise<void>;
}

// Concrete implementation belongs with infrastructure/integration;
// in hexagonal architecture it is a driven adapter.
```
