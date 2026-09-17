```typescript
// AFTER — serverless executable entrypoint; inline composition is still trivial
export async function POST(request: Request) {
  // Authentication owns the provider-free principal; the body cannot select a user.
  const principal = await authenticateRequest(request);
  if (!principal) return NextResponse.json({ error: 'unauthorized' }, { status: 401 });
  const db = createDb(env.DB);
  const userRepo = createDrizzleUserRepository(db);
  const balanceDeduction: ForDeductingUserBalances = createUserBalanceDeduction(userRepo);
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
  const result = await balanceDeduction.deductUserBalance({
    principal,
    amount: createMoney(body.amountMinorUnits, body.currency),
  });
  if (!result.success) {
    const status = result.reason === 'not-found' ? 404 : result.reason === 'concurrent-change' ? 409 : 422;
    return NextResponse.json({ error: result.reason }, { status });
  }
  return NextResponse.json({ balance: result.user.balance });
}
```
