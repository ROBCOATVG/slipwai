```typescript
// domain/account/account.ts — pure, no infrastructure imports

type AccountState =
  | { readonly status: 'unopened' }
  | { readonly status: 'open'; readonly balance: Money };

type Money = { readonly minorUnits: number; readonly currency: Currency };

type AccountCommand =
  | { readonly type: 'Open'; readonly currency: Currency }
  | { readonly type: 'Deposit'; readonly amount: Money }
  | { readonly type: 'Withdraw'; readonly amount: Money };

type AccountEvent =
  | { readonly type: 'AccountOpened'; readonly currency: Currency }
  | { readonly type: 'MoneyDeposited'; readonly amount: Money }
  | { readonly type: 'MoneyWithdrawn'; readonly amount: Money };

const initialState: AccountState = { status: 'unopened' };
const isPositiveMoney = (money: Money): boolean =>
  Number.isSafeInteger(money.minorUnits) && money.minorUnits > 0;

// decide: what SHOULD happen? Returns events (or a rejection). Enforces invariants.
const decide = (command: AccountCommand, state: AccountState): Decision<AccountEvent> => {
  switch (command.type) {
    case 'Open':
      if (state.status === 'open') return reject('already-open');
      return accept([{ type: 'AccountOpened', currency: command.currency }]);
    case 'Deposit':
      if (state.status !== 'open') return reject('not-open');
      if (!isPositiveMoney(command.amount)) return reject('invalid-amount');
      if (command.amount.currency !== state.balance.currency) return reject('currency-mismatch');
      if (!Number.isSafeInteger(state.balance.minorUnits + command.amount.minorUnits)) {
        return reject('balance-overflow');
      }
      return accept([{ type: 'MoneyDeposited', amount: command.amount }]);
    case 'Withdraw':
      if (state.status !== 'open') return reject('not-open');
      if (!isPositiveMoney(command.amount)) return reject('invalid-amount');
      if (command.amount.currency !== state.balance.currency) return reject('currency-mismatch');
      if (command.amount.minorUnits > state.balance.minorUnits) return reject('insufficient-funds');
      return accept([{ type: 'MoneyWithdrawn', amount: command.amount }]);
    default: { const _: never = command; return _; }
  }
};

const corruptHistory = (state: AccountState, event: AccountEvent): never => {
  throw new Error(`Corrupt account stream: ${event.type} cannot follow ${state.status}`);
};

const addMinorUnits = (left: number, right: number): number => {
  if (!Number.isSafeInteger(left) || !Number.isSafeInteger(right)) {
    throw new Error('Corrupt account stream: unsafe minor-unit operand');
  }
  const minorUnits = left + right;
  if (!Number.isSafeInteger(minorUnits) || minorUnits < 0) {
    throw new Error('Corrupt account stream: invalid resulting balance');
  }
  return minorUnits;
};

const applyDelta = (balance: Money, deltaMinorUnits: number): Money =>
  ({ ...balance, minorUnits: addMinorUnits(balance.minorUnits, deltaMinorUnits) });

// evolve applies facts; an impossible known transition is corrupt history, not a no-op.
const evolve = (state: AccountState, event: AccountEvent): AccountState => {
  switch (event.type) {
    case 'AccountOpened': {
      if (state.status !== 'unopened') return corruptHistory(state, event);
      return { status: 'open', balance: { minorUnits: 0, currency: event.currency } };
    }
    case 'MoneyDeposited':
      if (
        state.status !== 'open' ||
        !isPositiveMoney(event.amount) ||
        event.amount.currency !== state.balance.currency
      ) return corruptHistory(state, event);
      return { ...state, balance: applyDelta(state.balance, event.amount.minorUnits) };
    case 'MoneyWithdrawn':
      if (
        state.status !== 'open' ||
        !isPositiveMoney(event.amount) ||
        event.amount.currency !== state.balance.currency ||
        event.amount.minorUnits > state.balance.minorUnits
      ) return corruptHistory(state, event);
      return { ...state, balance: applyDelta(state.balance, -event.amount.minorUnits) };
    default: { const _: never = event; return _; }
  }
};
```
