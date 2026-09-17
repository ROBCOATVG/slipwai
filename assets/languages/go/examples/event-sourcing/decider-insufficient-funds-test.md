```go
package eventsourcing

import (
	"reflect"
	"testing"
)

// openAccount, money and deposited are small factories: complete, valid
// data with overrides, per the testing skill's factory pattern.
func openAccount(currency Currency) AccountEvent {
	if currency == "" {
		currency = "GBP"
	}
	return AccountOpened{Currency: currency}
}

func money(minorUnits int64, currency Currency) Money {
	if currency == "" {
		currency = "GBP"
	}
	return Money{MinorUnits: minorUnits, Currency: currency}
}

func deposited(minorUnits int64) AccountEvent {
	return MoneyDeposited{Amount: money(minorUnits, "")}
}

// TestDecide exercises Decide through its public API only — the returned
// events, or rejection, are the observable behaviour of the decider.
func TestDecide(t *testing.T) {
	tests := []struct {
		name    string
		history []AccountEvent
		command AccountCommand
		want    Decision
	}{
		{
			name:    "rejects a withdrawal that exceeds the balance",
			history: []AccountEvent{openAccount(""), deposited(5_000)},
			command: WithdrawMoney{Amount: money(10_000, "")},
			want:    Decision{Accepted: false, Reason: ReasonInsufficientFunds},
		},
		{
			name:    "records a deposit as a MoneyDeposited event on an open account",
			history: []AccountEvent{openAccount("")},
			command: DepositMoney{Amount: money(5_000, "")},
			want: Decision{
				Accepted: true,
				Events:   []AccountEvent{MoneyDeposited{Amount: money(5_000, "")}},
			},
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			state := InitialState
			for _, evt := range tc.history {
				var err error
				state, err = Evolve(state, evt)
				if err != nil {
					t.Fatalf("Evolve: %v", err)
				}
			}

			got := Decide(tc.command, state)

			if !reflect.DeepEqual(got, tc.want) {
				t.Errorf("Decide() = %+v, want %+v", got, tc.want)
			}
		})
	}
}
```
