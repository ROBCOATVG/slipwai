```go
package ddd

// Result (WRONG) — a bare string error tells you nothing. Nothing stops two
// call sites from spelling the same failure two different ways, and the
// compiler can't check that every case has been handled. Use a specific
// reason type instead — see PledgeDecision.
type Result struct {
	Success bool
	Data    any
	Error   string
}
```
