```typescript
type WithdrawRejection = 'not-open' | 'insufficient-funds' | 'invalid-amount' | 'currency-mismatch';

const decideWithdraw = (command: Withdraw, state: AccountState): Decision<AccountEvent, WithdrawRejection> => {
  if (state.status !== 'open') return reject('not-open');
  if (!Number.isSafeInteger(command.amount.minorUnits) || command.amount.minorUnits <= 0) {
    return reject('invalid-amount');
  }
  if (command.amount.currency !== state.balance.currency) return reject('currency-mismatch');
  if (command.amount.minorUnits > state.balance.minorUnits) return reject('insufficient-funds');
  return accept([{ type: 'MoneyWithdrawn', amount: command.amount }]);
};
```
