package ledger

import "testing"

func TestBalance(t *testing.T) {
	if Balance([]int{1, 2, 3}) != 6 {
		t.Fatal("wrong balance")
	}
}
