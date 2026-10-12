```typescript
// Domain returns: { success: false, reason: 'funding-closed' }
// Route handler translates:
const toHttpResponse = (result: PledgeResult): NextResponse => {
  if (result.success) {
    return NextResponse.json({ pledged: result.occasion.totalPledged }, { status: 200 });
  }
  const statusMap: Record<Extract<PledgeResult, { success: false }>['reason'], number> = {
    'not-found': 404,
    'concurrent-change': 409,
    'non-positive-amount': 422,
    'currency-mismatch': 422,
    'exceeds-budget': 422,
    'funding-closed': 422,
  };
  return NextResponse.json({ error: result.reason }, { status: statusMap[result.reason] });
};
```
