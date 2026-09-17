package events

type DomainEvent struct {
	Type          string
	SchemaVersion int
	StreamID      string
	Payload       map[string]any
}

type AppendResult struct {
	Outcome string
	Version int
}

type Store interface {
	Read(streamID string) []DomainEvent
	Append(streamID string, expectedVersion int, events []DomainEvent) AppendResult
}
