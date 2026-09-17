```go
package eventsourcing

// ToDomainEvent is the read-time pipeline: validate the raw stored JSON
// against the shape that was actually persisted (possibly an old version),
// then upcast it to the current shape. Validate first, then upcast — never
// let unvalidated data reach the upcaster.
//
// validateStoredAccountEvent is a tolerant reader over the union of every
// explicitly persisted version: unknown fields may be ignored, and only
// fields that were always optional (or have a proven, context-invariant
// default) may be absent. It returns an error on genuinely corrupt data — a
// bug, not a business case — which the caller must handle.
//
// upcastAccountEvent then maps whatever validated, possibly-old shape came
// back onto the current AccountEvent shape (see the OrderPlaced upcaster
// example for what one such step looks like in full).
func ToDomainEvent(raw []byte) (AccountEvent, error) {
	stored, err := validateStoredAccountEvent(raw)
	if err != nil {
		return nil, err
	}
	return upcastAccountEvent(stored)
}
```
