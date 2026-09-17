```go
package eventsourcing

import (
	"errors"
	"reflect"
	"testing"
)

func accountEnvelope(data AccountEvent, globalPosition int64, streamID StreamID) AccountProjectionEnvelope {
	return AccountProjectionEnvelope{StreamID: streamID, GlobalPosition: globalPosition, Data: data}
}

func TestApply(t *testing.T) {
	const accountID StreamID = "acc-1"

	t.Run("reflects net balance from a sequence of account events", func(t *testing.T) {
		envelopes := []AccountProjectionEnvelope{
			accountEnvelope(opened(""), 1, accountID),
			accountEnvelope(deposited(10_000), 2, accountID),
			accountEnvelope(withdrawn(3_000), 3, accountID),
		}

		view := EmptyBalanceView
		for _, envelope := range envelopes {
			var err error
			view, err = Apply(view, envelope)
			if err != nil {
				t.Fatalf("Apply: %v", err)
			}
		}

		want := BalanceView{
			Status:            BalanceViewOpen,
			AccountID:         accountID,
			Currency:          "GBP",
			BalanceMinorUnits: 7_000,
		}
		if !reflect.DeepEqual(view, want) {
			t.Errorf("view = %+v, want %+v", view, want)
		}
	})

	t.Run("surfaces a duplicate account opening as corrupt projection history", func(t *testing.T) {
		envelopes := []AccountProjectionEnvelope{
			accountEnvelope(opened("GBP"), 1, accountID),
			accountEnvelope(opened("EUR"), 2, accountID),
		}

		view := EmptyBalanceView
		var err error
		for _, envelope := range envelopes {
			view, err = Apply(view, envelope)
			if err != nil {
				break
			}
		}

		var corrupt *CorruptProjectionError
		if !errors.As(err, &corrupt) {
			t.Fatalf("Apply() error = %v, want *CorruptProjectionError", err)
		}
	})
}
```
