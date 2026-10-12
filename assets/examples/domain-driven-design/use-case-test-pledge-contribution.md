```typescript
describe('pledge contribution', () => {
  it('rejects a pledge from an ineligible contributor', async () => {
    const persistence = createFakePledgePersistence([testOccasion]);
    const eligibilityGateway = createFakeContributorEligibilityGateway([
      getTestContributorEligibility({ contributorId: testContributor.id, mayPledge: false }),
    ]);

    const result = await handlePledge(persistence, eligibilityGateway, {
      pledgeId: createPledgeId('pledge-1'),
      occasionId: testOccasion.id,
      contributorId: testContributor.id,
      amount: createMoney(5_000, 'GBP'),
    });

    expect(result).toEqual({ success: false, reason: 'contributor-ineligible' });
    expect(persistence.savedEntities).toHaveLength(0);
    expect(persistence.outboxEvents).toHaveLength(0);
  });
});
```
