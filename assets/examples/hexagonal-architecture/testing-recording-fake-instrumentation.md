```typescript
const createRecordingPledgeInstrumentation = (): PledgeInstrumentation & {
  readonly observed: readonly Record<string, unknown>[];
} => {
  const observed: Record<string, unknown>[] = [];
  return {
    pledgeRejected: (reason, occasionId) => { observed.push({ kind: 'pledge-rejected', reason, occasionId }); },
    pledgeAccepted: (amount, occasionId) => { observed.push({ kind: 'pledge-accepted', amount, occasionId }); },
    get observed() { return observed; },
  };
};

it('announces the rejection when funding is closed', async () => {
  const instrumentation = createRecordingPledgeInstrumentation();
  const pledging = createPledgingToOccasions(
    createFakeOccasionRepo({ occasions: [closedOccasion] }),
    createFakeContributorRepo(),
    instrumentation,
  );

  await pledging.pledgeToOccasion(getMockPledge({ occasionId: closedOccasion.id }));

  expect(instrumentation.observed).toContainEqual({
    kind: 'pledge-rejected',
    reason: 'funding-closed',
    occasionId: closedOccasion.id,
  });
});
```
