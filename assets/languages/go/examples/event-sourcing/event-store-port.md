```go
package eventsourcing

import (
	"context"
	"errors"
)

// StreamID identifies one aggregate instance's event stream.
type StreamID string

// ErrVersionConflict is returned by Append when the stream's actual version
// no longer matches expectedVersion — another writer appended to the same
// stream first. Callers check for it with errors.Is rather than comparing
// strings.
var ErrVersionConflict = errors.New("event store: version conflict")

// EventStore is the port (application layer) owned by the command handler
// that consumes it. It is typed to one aggregate's event family, like a
// repository — the underlying adapter can hold many streams, and parses
// stored JSON into AccountEvent on read.
type EventStore interface {
	// Read returns a stream's events in order, together with its current
	// version (the number of events recorded for it so far).
	Read(ctx context.Context, streamID StreamID) (events []AccountEvent, version int, err error)

	// Append writes events to a stream, asserting that the stream is still
	// at expectedVersion. It returns ErrVersionConflict if the stream has
	// moved on since the caller last read it.
	Append(ctx context.Context, streamID StreamID, events []AccountEvent, expectedVersion int) error
}
```
