```go
package eventsourcing

import (
	"reflect"
	"testing"
)

func TestUpcastOrderPlaced_V1ToV2(t *testing.T) {
	v1 := OrderPlacedV1{
		OrderID:         "o-1",
		TotalMinorUnits: 4_000,
		Currency:        "EUR",
	}

	current, err := UpcastOrderPlaced(v1)
	if err != nil {
		t.Fatalf("UpcastOrderPlaced: %v", err)
	}

	want := OrderPlacedV2{
		OrderID:     "o-1",
		TotalAmount: Money{MinorUnits: 4_000, Currency: "EUR"},
	}
	if !reflect.DeepEqual(current, want) {
		t.Errorf("UpcastOrderPlaced() = %+v, want %+v", current, want)
	}
}
```
