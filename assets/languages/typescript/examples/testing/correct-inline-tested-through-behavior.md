```typescript
// load-participant-view.ts
export const loadParticipantView = async (db: Db, eventId: EventId, userId: UserId) => {
  const items = await getItems(db, eventId, userId);
  const yourClaims = items.filter(i => i.isClaimed && i.isClaimedByCurrentUser);
  const available = items.filter(i => !i.isClaimedByCurrentUser);
  return { yourClaims, available };
};

// The behavioral test for loadParticipantView covers the filtering:
it('returns claimed gifts in yourClaims and unclaimed in available', async () => {
  const result = await loadParticipantView(db, eventId, userId);
  expect(result.yourClaims).toHaveLength(1);
  expect(result.available).toHaveLength(2);
});
```
