```typescript
// Driving adapter: log the request/response cycle
export async function POST(request: Request) {
  let rawBody: unknown;
  try {
    rawBody = await request.json();
  } catch {
    return NextResponse.json({ error: 'malformed-json' }, { status: 400 });
  }
  const parsedBody = PledgeSchema.safeParse(rawBody);
  if (!parsedBody.success) {
    return NextResponse.json({ error: 'invalid-body' }, { status: 422 });
  }
  const body = parsedBody.data;
  const pledging: ForPledgingToOccasions = createPledgingToOccasions(pledgePersistence);
  const result = await pledging.pledgeToOccasion(body);

  if (!result.success) {
    logger.warn('Pledge rejected', { reason: result.reason, occasionId: body.occasionId });
  }
  return NextResponse.json(...);
}

// Driven adapter: log infrastructure interactions
const createDrizzleOccasionRepository = (db: Database, logger: Logger): OccasionRepository => ({
  save: async (occasion) => {
    await db.insert(occasions).values(toRow(occasion))...;
    logger.debug('Occasion saved', { id: occasion.id });
  },
});
```
