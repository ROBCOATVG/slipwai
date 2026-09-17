```go
// materialisation: live — the view is folded per query and nothing is stored. No table, no checkpoint, no
// subscription, no rebuild path, and strongly consistent by construction: it reads the log the command
// just wrote. That is why it is the answer taken by default, and why the slice has to declare the ceiling
// it holds inside. Here the ceiling is asserted rather than assumed.

// MaxEventsFolded is liveBudget.events for this view, and the argument for it belongs beside the number:
// one account stream, which ends at closure, so the ceiling is the busiest account's lifetime and not a
// guess about traffic. Raise it deliberately, or materialise the view — not because a test went red.
const MaxEventsFolded = 40

// ErrViewOutgrewItsBudget reports a stream longer than this view may fold on every query.
var ErrViewOutgrewItsBudget = errors.New("balance view outgrew its live budget")

func ReadBalanceView(ctx context.Context, store events.Store, accountID string) (BalanceView, error) {
	history, err := store.Read(ctx, accountID)
	if err != nil {
		return BalanceView{}, fmt.Errorf("read account %s: %w", accountID, err)
	}
	if len(history) > MaxEventsFolded {
		// Failing is the point. A per-query fold does not degrade visibly — it gets slower by a
		// millisecond a week until a handler times out, and by then the fix is a table, a checkpoint, a
		// backfill and every caller. This turns that into one red test on the day the model changed.
		return BalanceView{}, fmt.Errorf(
			"%w: folded %d events for %s over a budget of %d, so close the stream at a business boundary "+
				"or materialise the view",
			ErrViewOutgrewItsBudget, len(history), accountID, MaxEventsFolded,
		)
	}
	view := EmptyBalanceView()
	for _, committed := range history {
		event, err := ToDomainEvent(committed)
		if err != nil {
			return BalanceView{}, fmt.Errorf("parse stored event at %d: %w", committed.GlobalPosition, err)
		}
		if view, err = ApplyToBalanceView(view, ProjectionEnvelope{
			StreamID:       committed.StreamID,
			GlobalPosition: committed.GlobalPosition,
			Data:           event,
		}); err != nil {
			return BalanceView{}, err
		}
	}
	return view, nil
}
```

```go
// balance_view_budget_test.go — the test that makes the ceiling a fact
func TestAStreamPastTheBudgetFailsRatherThanGettingSlower(t *testing.T) {
	store := eventstorememory.New()
	account := openAccountWithDeposits(t, store, MaxEventsFolded)

	deposit(t, store, account, 1)

	if _, err := ReadBalanceView(context.Background(), store, account); !errors.Is(err, ErrViewOutgrewItsBudget) {
		t.Fatalf("past the budget: got %v, want ErrViewOutgrewItsBudget", err)
	}
}
```
