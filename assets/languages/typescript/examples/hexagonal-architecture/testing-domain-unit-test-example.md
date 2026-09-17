```typescript
it('rejects contribution exceeding available balance', () => {
  const result = pledgeContribution(occasion, poorContributor, largePledge);
  expect(result.success).toBe(false);
});
```
