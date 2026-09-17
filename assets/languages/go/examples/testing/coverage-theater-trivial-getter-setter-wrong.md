```go
func TestWorker_SetRetryLimit(t *testing.T) {
	w := &Worker{}

	w.SetRetryLimit(3)

	if w.RetryLimit() != 3 { // trivial
		t.Fatalf("RetryLimit() = %d, want 3", w.RetryLimit())
	}
}
```
