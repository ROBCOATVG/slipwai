```go
package eventsourcing

import (
	"context"
	"errors"
)

// StreamID identifies one aggregate instance's event stream.
type StreamID string

// ErrVersionConflict distinguishes an optimistic-concurrency conflict from
// any other Append failure, so callers can react to it (retry, surface a
// 409, ...) with errors.Is instead of comparing strings.
var ErrVersionConflict = errors.New("event store: version conflict")

// EventStore is the port the application layer owns and the command
// handler consumes — it is typed to one aggregate's event family, like a
// repository. A single physical store commonly holds many stream types;
// the adapter behind this interface parses stored JSON into AccountEvent on
// read, so this typed view only ever exposes streams of that one family.
type EventStore interface {
	// Read returns every event recorded for streamID, in order, together
	// with the stream's current version.
	Read(ctx context.Context, streamID StreamID) (events []AccountEvent, version int, err error)

	// Append writes events to streamID if, and only if, the stream is
	// still at expectedVersion. It returns ErrVersionConflict if another
	// writer appended to the stream first.
	Append(ctx context.Context, streamID StreamID, events []AccountEvent, expectedVersion int) error
}
```
