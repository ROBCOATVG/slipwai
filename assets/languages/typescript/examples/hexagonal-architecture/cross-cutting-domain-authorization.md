```typescript
// Domain: "only the organizer can close funding" is a business rule
const closeFunding = (occasion: Occasion, requesterId: ContributorId): CloseResult => {
  if (occasion.organizerId !== requesterId) {
    return { success: false, reason: 'not-organizer' };
  }
  return { success: true, occasion: { ...occasion, isFundingClosed: true } };
};
```
