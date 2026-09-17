```go
// materialisation: inline — the view is written in the same transaction as the append, so it never lags the
// write and read-your-writes costs nothing on this slice. Two things to know before choosing it.
//
// The seam this needs is events.Store.InUnitOfWork, which the store you were given already has: it hands
// the work a context carrying the transaction, and inside it Append does not commit — so a view write on
// that same context commits with the events it derives from, or neither happens. Pass the inner context to
// everything that must be part of it; a call given the outer one is not.
//
// The view must be scoped to the stream being appended. A view folding several streams cannot be kept
// atomic with one append: the row it writes is contended by every other stream's appends, which is a hot
// row and a cross-stream transaction wearing a projection's clothes. That view is async.

// BalanceViews is this project's own view table, built from the event store — NewBalanceViews(store) — for
// the same reason the checkpoint store is: a write on a second connection is a second transaction, and then
// "inline" is a word rather than a guarantee.
type BalanceViews interface {
	Load(ctx context.Context, accountID string) (BalanceView, bool, error)
	Upsert(ctx context.Context, view BalanceView) error
}

func DepositMoney(
	ctx context.Context,
	store events.Store,
	views BalanceViews,
	command DepositMoney,
) (Outcome, error) {
	var outcome Outcome
	err := store.InUnitOfWork(ctx, func(inside context.Context) error {
		history, err := store.Read(inside, command.AccountID)
		if err != nil {
			return err
		}
		state, err := Rehydrate(history)
		if err != nil {
			return err
		}
		decision := Decide(command, state)
		if decision.Rejected() {
			outcome = decision // nothing appended, nothing projected; returning nil commits nothing
			return nil
		}
		result, err := store.Append(inside, command.AccountID, events.CurrentVersion(history), decision.Events)
		if err != nil {
			return err
		}
		if result.Conflict {
			// Contention, not failure: the caller re-reads and re-decides. Nothing is half-written, which
			// is the one thing inline gives you for free.
			outcome = Outcome{Conflict: true, ActualVersion: result.ActualVersion}
			return nil
		}
		// The same ApplyToBalanceView the live and async versions use — the lifecycle decides what
		// maintains the view, never how it is computed. Only the new events are applied: refolding the
		// stream here would put the whole history on the write path, which inline exists to avoid.
		view, _, err := views.Load(inside, command.AccountID)
		if err != nil {
			return err
		}
		appended, err := store.Read(inside, command.AccountID)
		if err != nil {
			return err
		}
		for _, committed := range appended[len(history):] {
			event, err := ToDomainEvent(committed)
			if err != nil {
				return err
			}
			if view, err = ApplyToBalanceView(view, ProjectionEnvelope{
				StreamID:       committed.StreamID,
				GlobalPosition: committed.GlobalPosition,
				Data:           event,
			}); err != nil {
				return err
			}
		}
		outcome = Outcome{Version: result.Version}
		return views.Upsert(inside, view)
	})
	return outcome, err
}
```

An inline view is still a derivation, so it still needs the rebuild path: when the fold changes or turns out
to be wrong, the fix is to reset the view and replay `ReadAll(ctx, 0)` through the same apply. Inline removes
the checkpoint and the subscription, not the obligation to be rebuildable.
