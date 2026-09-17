```go
package eventsourcing

// Outcome is the result of a Decide function: either accepted, carrying
// the events to append, or rejected, carrying a reason of type R.
type Outcome[E any, R any] struct {
	Accepted bool
	Events   []E
	Reason   R
}

// Accept builds an accepted Outcome carrying the given events.
func Accept[E any, R any](events []E) Outcome[E, R] {
	return Outcome[E, R]{Accepted: true, Events: events}
}

// Reject builds a rejected Outcome carrying the given reason.
func Reject[E any, R any](reason R) Outcome[E, R] {
	return Outcome[E, R]{Accepted: false, Reason: reason}
}
```
