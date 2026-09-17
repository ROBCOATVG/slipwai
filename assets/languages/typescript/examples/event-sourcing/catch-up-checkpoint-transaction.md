```typescript
// one event, applied and checkpointed atomically
await db.transaction(async (tx) => {
  await acquireExclusiveProjectionLease(tx, projectionName);
  const appliedThrough = await loadCheckpoint(tx, projectionName) ?? 0n;
  if (envelope.globalPosition <= appliedThrough) return; // exact redelivery
  if (envelope.globalPosition !== appliedThrough + 1n) {
    throw new Error('Projection gap: retry after the missing position');
  }
  const current = await loadBalanceView(tx, envelope.streamId) ?? emptyBalanceView;
  await upsertBalanceView(tx, apply(current, envelope));
  await saveCheckpoint(tx, projectionName, envelope.globalPosition); // same transaction
});
```
