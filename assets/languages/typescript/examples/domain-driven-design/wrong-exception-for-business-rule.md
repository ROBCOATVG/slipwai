```typescript
// WRONG — invisible failure mode, caller must remember to catch
const pledgeContribution = (...): Occasion => {
  if (occasion.isFundingClosed) throw new FundingClosedError();
  ...
};
```
