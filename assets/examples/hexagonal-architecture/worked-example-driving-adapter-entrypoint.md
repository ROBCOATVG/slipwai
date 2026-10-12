```typescript
// packages/gifting/adapters/driving/http/src/occasions/by-id/pledge/post.ts
const PledgePathSchema = z.object({ id: z.string().trim().min(1) }).strict();

export async function POST(request: Request, { params }: { params: { id: string } }) {
  const { env } = getCloudflareContext();
  const db = createDb(env.DB);

  // The authentication adapter is the only production constructor for this
  // provider-free principal. The request body cannot choose the actor.
  const principal = await authenticatePledger(request);
  if (!principal) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 });
  }

  const parsedPath = PledgePathSchema.safeParse(params);
  if (!parsedPath.success) {
    return NextResponse.json({ error: 'invalid-path' }, { status: 422 });
  }

  let rawBody: unknown;
  try {
    rawBody = await request.json();
  } catch {
    return NextResponse.json({ error: 'malformed-json' }, { status: 400 });
  }
  // Strict schema declares amount only; contributor/tenant fields are rejected.
  const parsedBody = PledgeBodySchema.strict().safeParse(rawBody);
  if (!parsedBody.success) {
    return NextResponse.json({ error: 'invalid-body' }, { status: 422 });
  }

  // Inline composition: this handler is the executable entrypoint and the graph is trivial
  const persistence = createDrizzlePledgePersistence(db);
  const pledging: ForPledgingToOccasions = createPledgingToOccasions(persistence);

  // Call use case
  const result = await pledging.pledgeToOccasion({
    pledgeId: createPledgeId(crypto.randomUUID()),
    occasionId: createOccasionId(parsedPath.data.id),
    principal,
    amount: parsedBody.data.amount,
  });

  // Translate result to HTTP
  if (!result.success) {
    const status = result.reason === 'not-found'
      ? 404
      : result.reason === 'concurrent-change'
        ? 409
        : 422;
    return NextResponse.json({ error: result.reason }, { status });
  }
  return NextResponse.json({ pledged: result.occasion.totalPledged });
}
```
