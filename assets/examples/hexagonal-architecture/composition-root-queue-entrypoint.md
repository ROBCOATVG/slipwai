```typescript
// Queue deployment entrypoint = inline composition + driving adapter
const handlePledgeMessage = async (message: SQSMessage, env: Env) => {
  const db = createDb(env.DB);
  const occasionRepo = createDrizzleOccasionRepository(db);
  const contributorRepo = createDrizzleContributorRepository(db);
  const pledging: ForPledgingToOccasions = createPledgingToOccasions(occasionRepo, contributorRepo);

  const dto = PledgeSchema.parse(JSON.parse(message.body));
  await pledging.pledgeToOccasion({
    ...dto,
    pledgeId: createPledgeId(message.messageId),
  });
};
```
