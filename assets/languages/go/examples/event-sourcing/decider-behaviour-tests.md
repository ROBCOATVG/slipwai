```go
package eventsourcing

import (
	"reflect"
	"testing"
)

// opened, money, deposited and withdrawn are event and money factories:
// complete, valid data with overrides, per the testing skill's factory
// pattern.
func opened(currency Currency) AccountEvent {
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

func withdrawn(minorUnits int64) AccountEvent {
	return MoneyWithdrawn{Amount: money(minorUnits, "")}
}

func TestDecide(t *testing.T) {
	tests := []struct {
		name    string
		history []AccountEvent
		command AccountCommand
		want    Decision
	}{
		{
			name:    "records a deposit as MoneyDeposited on an open account",
			history: []AccountEvent{opened("")},
			command: DepositMoney{Amount: money(5_000, "")},
			want: Decision{
				Accepted: true,
				Events:   []AccountEvent{MoneyDeposited{Amount: money(5_000, "")}},
			},
		},
		{
			name:    "rejects a withdrawal that exceeds the balance",
			history: []AccountEvent{opened(""), deposited(5_000)},
			command: WithdrawMoney{Amount: money(10_000, "")},
			want:    Decision{Accepted: false, Reason: ReasonInsufficientFunds},
		},
		{
			name:    "rejects any operation on an account that was never opened",
			history: nil,
			command: DepositMoney{Amount: money(5_000, "")},
			want:    Decision{Accepted: false, Reason: ReasonNotOpen},
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
