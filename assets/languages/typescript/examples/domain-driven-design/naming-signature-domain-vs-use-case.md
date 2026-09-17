```typescript
// Use case — takes application-owned collaboration contracts when needed
const placeOrder = async (repo: OrderRepository, gateway: PaymentGateway, order: NewOrder) => ...

// Domain service — takes only domain types
const pledgeContribution = (
  occasion: Occasion,
  eligibility: ContributorEligibility,
  pledge: { readonly id: PledgeId; readonly amount: Money },
) => ...
```
