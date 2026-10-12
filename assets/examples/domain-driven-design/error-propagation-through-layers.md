```typescript
// Domain: returns result with business reason
const pledgeContribution = (...): PledgeDecision => {
  if (occasion.isFundingClosed) return { success: false, reason: 'funding-closed' };
  ...
};

// Use case: propagates result, controls save
const handlePledge = async (repos, dto): Promise<PledgeResult> => {
  const stored = await repos.occasion.findById(dto.occasionId);
  const eligibility = await repos.eligibility.findFor(dto.contributorId);
  if (!stored || !eligibility) return { success: false, reason: 'not-found' };

  const result = pledgeContribution(stored.value, eligibility, {
    id: dto.pledgeId,
    amount: dto.amount,
  });
  if (result.success) {
    const saved = await repos.occasion.saveWithOutbox(
      result.occasion,
      result.events,
      stored.version,
    );
    if (saved === 'conflict') return { success: false, reason: 'concurrent-change' };
  }
  return result;
};

// Route handler: translates to HTTP
const status = result.success ? 200
  : result.reason === 'not-found' ? 404
  : result.reason === 'concurrent-change' ? 409
  : 422;
return NextResponse.json(
  result.success ? { pledged: result.occasion.totalPledged } : { error: result.reason },
  { status },
);
```
