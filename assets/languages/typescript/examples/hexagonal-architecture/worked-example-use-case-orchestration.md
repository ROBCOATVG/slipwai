```typescript
// packages/gifting/hexagon/application/src/pledge-to-occasion.ts — use case
const createPledgingToOccasions = (
  persistence: PledgePersistence,
): ForPledgingToOccasions => ({
  pledgeToOccasion: async (dto) => {
    const stored = await persistence.findOccasionById(dto.occasionId);
    if (!stored) return { success: false, reason: 'not-found' };

    const result = recordPledge(stored.value, {
      id: dto.pledgeId,
      contributorId: dto.principal.contributorId,
      amount: dto.amount,
    });
    if (result.success) {
      const saved = await persistence.saveWithOutbox(
        result.occasion,
        result.events,
        stored.version,
      );
      if (saved === 'conflict') {
        return { success: false, reason: 'concurrent-change' };
      }
    }
    return result;
  },
});

// packages/gifting/hexagon/application/src/pledge-recorded-handler.ts
const handlePledgeRecorded = async (
  projection: PledgeProjection,
  event: PledgeRecorded,
): Promise<void> => {
  await projection.recordFrom(event);
};
```
