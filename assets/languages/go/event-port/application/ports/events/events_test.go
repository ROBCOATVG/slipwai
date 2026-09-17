package events

import "testing"

func TestVersionConflictIsAValue(t *testing.T) {
	result := AppendResult{Outcome: "version-conflict", Version: 2}
	if result.Outcome != "version-conflict" {
		t.Fatal(result)
	}
}
