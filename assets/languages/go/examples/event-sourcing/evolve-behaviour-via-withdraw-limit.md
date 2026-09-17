```go
package eventsourcing

import "testing"

// TestEvolve_WithdrawLimit proves Evolve's fold is correct indirectly, by
// checking which withdrawal amounts Decide accepts against the resulting
// state — the running balance is never asserted directly, only the
// behaviour it produces at its boundary.
func TestEvolve_WithdrawLimit(t *testing.T) {
	state := InitialState
	for _, evt := range []AccountEvent{opened(""), deposited(10_000), withdrawn(3_000)} {
		var err error
		state, err = Evolve(state, evt)
		if err != nil {
			t.Fatalf("Evolve: %v", err)
		}
	}

	tests := []struct {
		name         string
		withdrawal   int64
		wantAccepted bool
	}{
		{name: "withdrawing exactly the available balance is accepted", withdrawal: 7_000, wantAccepted: true},
		{name: "withdrawing one minor unit over the available balance is rejected", withdrawal: 7_001, wantAccepted: false},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			got := Decide(WithdrawMoney{Amount: money(tc.withdrawal, "")}, state).Accepted
			if got != tc.wantAccepted {
				t.Errorf("Decide(Withdraw %d).Accepted = %v, want %v", tc.withdrawal, got, tc.wantAccepted)
			}
		})
	}
}
```
