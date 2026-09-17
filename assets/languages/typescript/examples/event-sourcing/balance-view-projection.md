```typescript
// A projection is a fold from events → a read-optimised row
type BalanceView =
  | { readonly status: 'unopened' }
  | {
      readonly status: 'open';
      readonly accountId: StreamId;
      readonly balanceMinorUnits: number;
      readonly currency: Currency;
    };

type AccountProjectionEnvelope = {
  readonly streamId: StreamId;
  readonly globalPosition: bigint;
  readonly data: AccountEvent;
};

const emptyBalanceView: BalanceView = { status: 'unopened' };

const corruptBalanceProjection = (view: BalanceView, event: AccountEvent): never => {
  throw new Error(`Corrupt balance projection: ${event.type} cannot follow ${view.status}`);
};

const applyToBalanceView = (
  view: BalanceView,
  envelope: AccountProjectionEnvelope,
): BalanceView => {
  const event = envelope.data;
  switch (event.type) {
    case 'AccountOpened':
      if (view.status !== 'unopened') return corruptBalanceProjection(view, event);
      return {
        status: 'open',
        accountId: envelope.streamId,
        currency: event.currency,
        balanceMinorUnits: 0,
      };
    case 'MoneyDeposited':
      if (
        view.status !== 'open' ||
        view.accountId !== envelope.streamId ||
        !isPositiveMoney(event.amount) ||
        event.amount.currency !== view.currency
      ) return corruptBalanceProjection(view, event);
      return { ...view, balanceMinorUnits: addMinorUnits(view.balanceMinorUnits, event.amount.minorUnits) };
    case 'MoneyWithdrawn':
      if (
        view.status !== 'open' ||
        view.accountId !== envelope.streamId ||
        !isPositiveMoney(event.amount) ||
        event.amount.currency !== view.currency ||
        event.amount.minorUnits > view.balanceMinorUnits
      ) return corruptBalanceProjection(view, event);
      return { ...view, balanceMinorUnits: addMinorUnits(view.balanceMinorUnits, -event.amount.minorUnits) };
    default: { const _: never = event; return _; }
  }
};
```
