```typescript
// Serverless executable entrypoint = inline composition + driving adapter
// Valid only while this object graph remains trivial and unshared.
export async function POST(request: Request) {
  const { env } = getCloudflareContext();
  const db = createDb(env.DB);

  // Wire adapters
  const repo = createDrizzleOrderRepository(db);
  const gateway = createStripeGateway(env.STRIPE_KEY);
  const orderPlacement: ForPlacingOrders = createOrderPlacement(repo, gateway);

  // Translate transport syntax separately from request-schema validation.
  let rawBody: unknown;
  try {
    rawBody = await request.json();
  } catch {
    return NextResponse.json({ error: 'malformed-json' }, { status: 400 });
  }
  const parsedBody = CreateOrderSchema.safeParse(rawBody);
  if (!parsedBody.success) {
    return NextResponse.json({ error: 'invalid-body' }, { status: 422 });
  }

  // Call use case
  const result = await orderPlacement.placeOrder(parsedBody.data);
  return NextResponse.json(result);
}
```
