```typescript
// packages/billing/hexagon/application/src/deduct-user-balance.ts — driving port + use case
type DeductUserBalanceResult =
  | DeductResult
  | { readonly success: false; readonly reason: 'not-found' | 'concurrent-change' };

declare const authenticatedPrincipal: unique symbol;
type AuthenticatedPrincipal = {
  readonly [authenticatedPrincipal]: true;
  readonly userId: UserId;
};

interface ForDeductingUserBalances {
  readonly deductUserBalance: (
    dto: { readonly principal: AuthenticatedPrincipal; readonly amount: Money },
  ) => Promise<DeductUserBalanceResult>;
}

const createUserBalanceDeduction = (
  userRepo: UserRepository,
): ForDeductingUserBalances => ({
  deductUserBalance: async (dto) => {
    const stored = await userRepo.findById(dto.principal.userId);
    if (!stored) return { success: false, reason: 'not-found' };
    const result = deductBalance(stored.value, dto.amount);
    if (!result.success) return result;
    const saved = await userRepo.save(result.user, stored.version);
    return saved === 'saved' ? result : { success: false, reason: 'concurrent-change' };
  },
});
```
