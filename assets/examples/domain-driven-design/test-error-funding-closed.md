```typescript
it('rejects pledge when funding is closed', async () => {
  const closedOccasion = getTestOccasion({ isFundingClosed: true });
  const occasionRepo = createFakeOccasionRepository([closedOccasion]);
  const contributorRepo = createFakeContributorRepository([testContributor]);

  const result = await handlePledge(occasionRepo, contributorRepo, {
    occasionId: closedOccasion.id,
    contributorId: testContributor.id,
    amount: createMoney(2_500, 'GBP'),
  });

  expect(result).toEqual({ success: false, reason: 'funding-closed' });
  expect(occasionRepo.savedEntities).toHaveLength(0);
});
```
