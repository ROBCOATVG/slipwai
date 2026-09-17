```typescript
// Driving adapter: extract and validate auth
export async function POST(request: Request) {
  const principal = await authenticateRequest(request); // sole production constructor
  if (!principal) return NextResponse.json({ error: 'unauthorized' }, { status: 401 });
  const pledging: ForPledgingToOccasions = createPledgingToOccasions(pledgePersistence);
  let rawBody: unknown;
  try {
    rawBody = await request.json();
  } catch {
    return NextResponse.json({ error: 'malformed-json' }, { status: 400 });
  }
  const parsedBody = PledgeBodySchema.strict().safeParse(rawBody);
  if (!parsedBody.success) {
    return NextResponse.json({ error: 'invalid-body' }, { status: 422 });
  }

  // Strict body has no actor/tenant fields; the principal owns attribution.
  const result = await pledging.pledgeToOccasion({
    ...parsedBody.data,
    principal,
  });
  ...
}
```
