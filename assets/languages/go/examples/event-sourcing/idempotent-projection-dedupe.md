```go
package eventsourcing

import "testing"

// BalanceRow is a per-account (single-stream) read-model row; Version is
// unique within it.
type BalanceRow struct {
	BalanceMinorUnits int64
	AppliedThrough    int
}

// ProjectRow idempotently applies a deposit to row: any event at or below
// the version already applied is ignored, so a redelivered event cannot
// double-count.
func ProjectRow(row BalanceRow, amount Money, version int) (BalanceRow, error) {
	if version <= row.AppliedThrough {
		return row, nil
	}
	balance, err := addMinorUnits(row.BalanceMinorUnits, amount.MinorUnits)
	if err != nil {
		return row, err
	}
	row.BalanceMinorUnits = balance
	row.AppliedThrough = version
	return row, nil
}

func TestProjectRow_IgnoresRedeliveredEvent(t *testing.T) {
	amount := money(10_000, "")

	once, err := ProjectRow(BalanceRow{}, amount, 1)
	if err != nil {
		t.Fatalf("first ProjectRow: %v", err)
	}
	twice, err := ProjectRow(once, amount, 1) // the same event, redelivered at the same version
	if err != nil {
		t.Fatalf("second ProjectRow: %v", err)
	}

	if once.BalanceMinorUnits != 10_000 {
		t.Errorf("once.BalanceMinorUnits = %d, want 10000", once.BalanceMinorUnits)
	}
	if twice.BalanceMinorUnits != 10_000 {
		t.Errorf("twice.BalanceMinorUnits = %d, want 10000 (not double-counted)", twice.BalanceMinorUnits)
	}
}
```
