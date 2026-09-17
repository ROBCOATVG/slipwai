```typescript
// One transaction saves one aggregate and its outbox event.
const handlePledge = async (repos, dto) => {
  const stored = await repos.occasion.findById(dto.occasionId);
  if (!stored) return { success: false, reason: 'not-found' };

  const result = recordPledge(stored.value, dto);
  if (!result.success) return result;

  const saved = await repos.occasion.saveWithOutbox(
    result.occasion,
    result.events,
    stored.version,
  );
  if (!saved.success) return { success: false, reason: 'concurrent-change' };

  return result;
};

// A separate idempotent handler converges the other aggregate.
const handlePledgeRecorded = async (event) => {
  await repos.contributor.applyPledgeOnce(event.id, event.contributorId, event.amount);
};
```
