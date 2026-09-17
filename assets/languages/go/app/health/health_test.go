package health

import "testing"

func TestReportsReady(t *testing.T) {
	if got := Check().Status; got != "ok" {
		t.Fatalf("got %q", got)
	}
}
