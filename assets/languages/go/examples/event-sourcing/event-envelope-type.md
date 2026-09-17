```go
package eventsourcing

import "time"

// CorrelationID and CausationID are UUIDs. Go's standard library has no UUID type, so these are
// strings that have been checked — the constructor that parses one is the only way to make one.
// Two types rather than one used twice: they sit side by side below and are both strings
// underneath, so swapping them compiles, and it destroys the one thing they exist for.
type (
	CorrelationID string
	CausationID   string
)

// EventEnvelope wraps a stored domain event with the metadata the store and
// its consumers need but the domain payload itself does not carry.
type EventEnvelope[Data any] struct {
	// ID uniquely identifies this event (a UUID) — used for idempotency,
	// and as a causation target for events it later causes.
	ID string

	// Type is the event's type name, stored as a string so a reader that
	// doesn't yet know about a newer type can still deserialize tolerantly.
	Type string

	// StreamID identifies the aggregate instance this event belongs to.
	StreamID string

	// Version is this event's position within its own stream, used for
	// optimistic concurrency.
	Version int

	// GlobalPosition is this event's position in the store-wide order,
	// used by subscriptions and projections to resume a catch-up read.
	GlobalPosition int64

	// Timestamp is assigned by the store, in UTC.
	Timestamp time.Time

	// Data is the domain payload.
	Data Data

	// Metadata carries cross-cutting, non-domain context.
	Metadata EventMetadata
}

// EventMetadata carries tracing context for an event: which whole business
// transaction it belongs to, and what directly caused it. A real system
// commonly extends this with a user ID, tenant ID, or schema version.
type EventMetadata struct {
	// CorrelationID ties every message in one whole business transaction
	// together.
	CorrelationID CorrelationID

	// CausationID is the ID of the message that directly caused this
	// event, and is empty when nothing did.
	CausationID CausationID
}
```
