```typescript
// BEFORE — everything in the route handler
export async function POST(request: Request) {
  const principal = await authenticateRequest(request);
  if (!principal) return NextResponse.json({ error: 'unauthorized' }, { status: 401 });
  let rawBody: unknown;
  try {
    rawBody = await request.json();
  } catch {
    return NextResponse.json({ error: 'malformed-json' }, { status: 400 });
  }
  const parsedBody = DeductBodySchema.strict().safeParse(rawBody);
  if (!parsedBody.success) {
    return NextResponse.json({ error: 'invalid-body' }, { status: 422 });
  }
  const body = parsedBody.data;
  const user = await db.select().from(users).where(eq(users.id, principal.userId)).get();
  if (!user) return NextResponse.json({ error: 'not found' }, { status: 404 });
  if (!Number.isSafeInteger(body.amountMinorUnits) || body.amountMinorUnits <= 0) {
    return NextResponse.json({ error: 'invalid amount' }, { status: 422 });
  }
  if (body.currency !== user.currency) return NextResponse.json({ error: 'currency mismatch' }, { status: 422 });
  if (user.balanceMinorUnits < body.amountMinorUnits) return NextResponse.json({ error: 'insufficient' }, { status: 422 });
  const balanceMinorUnits = user.balanceMinorUnits - body.amountMinorUnits;
  await db.update(users).set({ balanceMinorUnits }).where(eq(users.id, user.id));
  return NextResponse.json({ balanceMinorUnits, currency: user.currency });
}
```
