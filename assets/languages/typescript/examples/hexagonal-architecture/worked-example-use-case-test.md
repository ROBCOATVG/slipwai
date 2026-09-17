```typescript
// packages/gifting/hexagon/application/src/pledge-contribution.test.ts
describe('pledge contribution', () => {
  const testOccasion = getTestOccasion({ totalPledged: createMoney(0, 'GBP') });
  const testPledgeId = createPledgeId('pledge-1');
  const testContributorId = createContributorId('contributor-1');
  const testPrincipal = getTestAuthenticatedPledger(testContributorId);

  it('updates one aggregate and records its outbox event', async () => {
    const persistence = createFakePledgePersistence([testOccasion]);
    const pledging = createPledgingToOccasions(persistence);

    const result = await pledging.pledgeToOccasion({
      pledgeId: testPledgeId,
      occasionId: testOccasion.id,
      principal: testPrincipal,
      amount: createMoney(2_500, 'GBP'),
    });

    expect(result).toMatchObject({
      success: true,
      occasion: expect.objectContaining({ totalPledged: createMoney(2_500, 'GBP') }),
    });
    expect(persistence.savedEntities).toHaveLength(1);
    expect(persistence.outboxEvents).toEqual([{
      type: 'PledgeRecorded',
      id: testPledgeId,
      occasionId: testOccasion.id,
      contributorId: testContributorId,
      amount: createMoney(2_500, 'GBP'),
    }]);
  });

  it('rejects a pledge that would exceed the occasion budget', async () => {
    const nearlyFunded = getTestOccasion({
      budget: createMoney(10_000, 'GBP'),
      totalPledged: createMoney(9_000, 'GBP'),
    });
    const persistence = createFakePledgePersistence([nearlyFunded]);
    const pledging = createPledgingToOccasions(persistence);

    const result = await pledging.pledgeToOccasion({
      pledgeId: testPledgeId,
      occasionId: nearlyFunded.id,
      principal: testPrincipal,
      amount: createMoney(2_500, 'GBP'),
    });

    expect(result).toEqual({ success: false, reason: 'exceeds-budget' });
    expect(persistence.savedEntities).toHaveLength(0);
    expect(persistence.outboxEvents).toHaveLength(0);
  });

  it('rejects a pledge in a different currency', async () => {
    const persistence = createFakePledgePersistence([testOccasion]);
    const pledging = createPledgingToOccasions(persistence);

    const result = await pledging.pledgeToOccasion({
      pledgeId: testPledgeId,
      occasionId: testOccasion.id,
      principal: testPrincipal,
      amount: createMoney(2_500, 'USD'),
    });

    expect(result).toEqual({ success: false, reason: 'currency-mismatch' });
    expect(persistence.savedEntities).toHaveLength(0);
    expect(persistence.outboxEvents).toHaveLength(0);
  });

  it('rejects one of two concurrent writes from the same version', async () => {
    const persistence = createFakePledgePersistence([testOccasion]);
    const pledging = createPledgingToOccasions(persistence);

    const results = await Promise.all([
      pledging.pledgeToOccasion({
        pledgeId: createPledgeId('pledge-1'),
        occasionId: testOccasion.id,
        principal: testPrincipal,
        amount: createMoney(2_500, 'GBP'),
      }),
      pledging.pledgeToOccasion({
        pledgeId: createPledgeId('pledge-2'),
        occasionId: testOccasion.id,
        principal: testPrincipal,
        amount: createMoney(3_000, 'GBP'),
      }),
    ]);

    expect(results.filter(result => result.success)).toHaveLength(1);
    expect(results.filter(result => !result.success)).toEqual([
      { success: false, reason: 'concurrent-change' },
    ]);
    expect(persistence.savedEntities).toHaveLength(1);
    expect(persistence.outboxEvents).toHaveLength(1);
  });

  it('rejects pledge when funding is closed', async () => {
    const closedOccasion = getTestOccasion({ isFundingClosed: true });
    const persistence = createFakePledgePersistence([closedOccasion]);
    const pledging = createPledgingToOccasions(persistence);

    const result = await pledging.pledgeToOccasion({
      pledgeId: testPledgeId,
      occasionId: closedOccasion.id,
      principal: testPrincipal,
      amount: createMoney(2_500, 'GBP'),
    });

    expect(result).toEqual({ success: false, reason: 'funding-closed' });
  });

  it('handles a redelivered PledgeRecorded event once', async () => {
    const projection = createFakePledgeProjection();
    const event: PledgeRecorded = {
      type: 'PledgeRecorded',
      id: testPledgeId,
      occasionId: testOccasion.id,
      contributorId: testContributorId,
      amount: createMoney(2_500, 'GBP'),
    };

    await handlePledgeRecorded(projection, event);
    await handlePledgeRecorded(projection, event);

    expect(projection.records).toEqual([event]);
  });
});
```
