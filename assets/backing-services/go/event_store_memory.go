// Package eventstorememory holds the in-memory event-store adapter.
//
// For a quickstart with no infrastructure, and for tests that do not need to prove concurrency.
// `make verify` runs the shared contract suite against this one, which is why the repository
// gate needs no Docker.
//
// It satisfies the port's contract, but understand what it cannot do: it serialises every call
// behind one mutex, so it CANNOT prove that two concurrent appends at the same version produce
// exactly one winner — nor that two conditional appends against one boundary do. Those guarantees
// live in a real store's unique constraint and isolation level, and `make test-integration` is
// where they are proved. Ship on Postgres, demo on memory.
//
// Data is lost when the process ends, which for an event-sourced system means the entire truth
// is lost. Never production.
package eventstorememory

import (
	"context"
	"maps"
	"slices"
	"sync"
	"time"

	"example.com/delivery-starter/application/ports/events"
)

// LeaseRow is one row of the leases a Database holds — the storage shape of a projection's lease,
// without the policy that decides whether it may be taken. That policy is the checkpoint adapter's.
type LeaseRow struct {
	Owner     string
	ExpiresAt time.Time
}

// Database is what a connection is, when there is no database.
//
// It exists so the in-memory adapters can do the one thing the real ones do that matters most to
// the read side: put an append, a view write and a checkpoint in one transaction. Build the event
// store and the checkpoint store from the same Database — which is what
// checkpointstorememory.New(store) does — and InUnitOfWork covers all of it.
//
// Rollback is a restore from a shallow copy taken on entry. That is honest for what this is for: it
// proves the semantics a test needs (a failed batch changes nothing) without pretending to be a
// transaction manager. What it does not survive is two goroutines in overlapping units of work,
// which is one more thing only a real store can do — and `make test-integration` is where that is
// proved.
type Database struct {
	mutex              sync.Mutex
	log                []events.CommittedEvent
	tags               map[int64][]string
	checkpoints        map[string]int64
	leases             map[string]LeaseRow
	nextGlobalPosition int64
}

// NewDatabase returns an empty in-memory database, ready for both adapters to be built from.
func NewDatabase() *Database {
	return &Database{
		tags:               map[int64][]string{},
		checkpoints:        map[string]int64{},
		leases:             map[string]LeaseRow{},
		nextGlobalPosition: 1,
	}
}

// InUnitOfWork runs work, undoing everything it changed if it fails.
//
// The mutex is deliberately not held across work: it is not re-entrant, and work calls back into
// methods that take it. Nesting therefore needs no counter — the mutation happens in place, so a
// rollback is a restore, and an inner block restoring its own snapshot leaves the outer one's
// intact.
func (d *Database) InUnitOfWork(ctx context.Context, work func(context.Context) error) error {
	d.mutex.Lock()
	snapshot := Database{
		log:                slices.Clone(d.log),
		tags:               maps.Clone(d.tags),
		checkpoints:        maps.Clone(d.checkpoints),
		leases:             maps.Clone(d.leases),
		nextGlobalPosition: d.nextGlobalPosition,
	}
	d.mutex.Unlock()

	if err := work(ctx); err != nil {
		d.mutex.Lock()
		d.log, d.tags = snapshot.log, snapshot.tags
		d.checkpoints, d.leases = snapshot.checkpoints, snapshot.leases
		d.nextGlobalPosition = snapshot.nextGlobalPosition
		d.mutex.Unlock()
		return err
	}
	return nil
}

// PositionOf, RecordPosition, Lease, SetLease and DeleteLease are the primitives the checkpoint
// adapter is built from: storage, under this Database's lock, with none of the policy that decides
// whether a lease may be taken.

// PositionOf reads a projection's recorded position, and 0 for one nothing has recorded.
func (d *Database) PositionOf(projection string) int64 {
	d.mutex.Lock()
	defer d.mutex.Unlock()
	return d.checkpoints[projection]
}

// RecordPosition writes a projection's position.
func (d *Database) RecordPosition(projection string, position int64) {
	d.mutex.Lock()
	defer d.mutex.Unlock()
	d.checkpoints[projection] = position
}

// Lease reads the lease row a projection currently has, if any.
func (d *Database) Lease(projection string) (LeaseRow, bool) {
	d.mutex.Lock()
	defer d.mutex.Unlock()
	row, held := d.leases[projection]
	return row, held
}

// SetLease writes a projection's lease row.
func (d *Database) SetLease(projection string, row LeaseRow) {
	d.mutex.Lock()
	defer d.mutex.Unlock()
	d.leases[projection] = row
}

// DeleteLease removes a projection's lease row, if owner still holds it.
func (d *Database) DeleteLease(projection string, owner string) {
	d.mutex.Lock()
	defer d.mutex.Unlock()
	if row, held := d.leases[projection]; held && row.Owner == owner {
		delete(d.leases, projection)
	}
}

// Store is an in-memory events.Store.
type Store struct {
	database *Database
	tagsOf   events.TagsOf
}

// New returns an empty in-memory store, tagging events by their own stream.
func New() *Store {
	return NewTagged(events.DefaultTagsOf, NewDatabase())
}

// NewTagged returns a store over database, indexing each event by what tagsOf returns for it.
//
// Both arguments matter to the read side: tagsOf is what this project's events are findable by,
// and passing the same Database to checkpointstorememory.New is what puts a checkpoint in the same
// unit of work as the events it accounts for.
func NewTagged(tagsOf events.TagsOf, database *Database) *Store {
	return &Store{database: database, tagsOf: tagsOf}
}

// Database is the store's own database, for a sibling adapter to be built from — the equivalent of
// two SQL adapters sharing one connection.
func (s *Store) Database() *Database { return s.database }

func (s *Store) streamLocked(streamID string) []events.CommittedEvent {
	var stream []events.CommittedEvent
	for _, event := range s.database.log {
		if event.StreamID == streamID {
			stream = append(stream, event)
		}
	}
	return stream
}

// recordLocked appends one event and indexes it, with the mutex already held.
//
// The tags go in here rather than in a pass of their own, which is the whole design: an index
// written after the append could be missing when the next conditional append checks it, and that
// append would then be guarded by a boundary with a hole in it.
func (s *Store) recordLocked(event events.DomainEvent, streamID string, version int) {
	event.StreamID = streamID
	payload := make(map[string]any, len(event.Payload))
	for key, value := range event.Payload {
		payload[key] = value
	}
	event.Payload = payload
	position := s.database.nextGlobalPosition
	s.database.log = append(s.database.log, events.CommittedEvent{
		DomainEvent:    event,
		Version:        version,
		GlobalPosition: position,
		RecordedAt:     time.Now().UTC().Format(time.RFC3339Nano),
	})
	// No entry at all when the tagging function returns nothing, rather than an empty one: the SQL
	// adapters give such an event no rows, and "indexed" has to mean the same thing in every adapter
	// or ReindexTags answers differently depending on the store.
	if tags := s.tagsOf(event); len(tags) > 0 {
		s.database.tags[position] = slices.Clone(tags)
	}
	s.database.nextGlobalPosition++
}

func (s *Store) Read(_ context.Context, streamID string) ([]events.CommittedEvent, error) {
	s.database.mutex.Lock()
	defer s.database.mutex.Unlock()
	return s.streamLocked(streamID), nil
}

func (s *Store) Append(
	_ context.Context,
	streamID string,
	expectedVersion int,
	batch []events.DomainEvent,
) (events.AppendResult, error) {
	s.database.mutex.Lock()
	defer s.database.mutex.Unlock()

	stream := s.streamLocked(streamID)
	actualVersion := events.CurrentVersion(stream)
	if actualVersion != expectedVersion {
		return events.VersionConflict(actualVersion), nil
	}

	version := actualVersion
	for _, event := range batch {
		version++
		s.recordLocked(event, streamID, version)
	}
	return events.Appended(version), nil
}

func (s *Store) ReadAll(
	_ context.Context,
	fromPosition int64,
	visit func(events.CommittedEvent) error,
) error {
	s.database.mutex.Lock()
	snapshot := slices.Clone(s.database.log)
	s.database.mutex.Unlock()

	for _, event := range snapshot {
		if event.GlobalPosition < fromPosition {
			continue
		}
		if err := visit(event); err != nil {
			return err
		}
	}
	return nil
}

// InUnitOfWork runs work in one transaction, which an append and somebody else's write share.
func (s *Store) InUnitOfWork(ctx context.Context, work func(context.Context) error) error {
	return s.database.InUnitOfWork(ctx, work)
}

func (s *Store) headLocked() int64 {
	if len(s.database.log) == 0 {
		return 0
	}
	return s.database.log[len(s.database.log)-1].GlobalPosition
}

func (s *Store) Head(_ context.Context) (int64, error) {
	s.database.mutex.Lock()
	defer s.database.mutex.Unlock()
	return s.headLocked(), nil
}

func (s *Store) ReadTagged(
	_ context.Context,
	query events.TagQuery,
	after int64,
	until int64,
) (events.TaggedRead, error) {
	s.database.mutex.Lock()
	defer s.database.mutex.Unlock()
	return s.readTaggedLocked(query, after, until), nil
}

func (s *Store) readTaggedLocked(query events.TagQuery, after int64, until int64) events.TaggedRead {
	ceiling := until
	if ceiling == 0 {
		ceiling = s.headLocked()
	}
	var found []events.CommittedEvent
	for _, event := range s.database.log {
		if event.GlobalPosition <= after || event.GlobalPosition > ceiling {
			continue
		}
		if query.Matches(event, s.database.tags[event.GlobalPosition]) {
			found = append(found, event)
		}
	}
	return events.TaggedRead{Events: found, Head: ceiling}
}

func (s *Store) AppendIf(
	ctx context.Context,
	condition events.Condition,
	batch []events.DomainEvent,
) (events.ConditionalAppendResult, error) {
	err := s.database.InUnitOfWork(ctx, func(context.Context) error {
		s.database.mutex.Lock()
		defer s.database.mutex.Unlock()

		if len(s.readTaggedLocked(condition.Query, condition.After, 0).Events) > 0 {
			return errConditionBroken
		}
		for _, event := range batch {
			// Each event still lands at the next version of the stream it names, so a
			// conditionally appended event is readable by everything written against Read and
			// Append. The boundary changed; the log did not.
			stream := s.streamLocked(event.StreamID)
			s.recordLocked(event, event.StreamID, events.CurrentVersion(stream)+1)
		}
		return nil
	})

	s.database.mutex.Lock()
	head := s.headLocked()
	s.database.mutex.Unlock()

	if err == errConditionBroken {
		return events.ConditionConflict(head), nil
	}
	if err != nil {
		return events.ConditionalAppendResult{}, err
	}
	return events.Recorded(head), nil
}

// errConditionBroken travels out of the unit of work so it unwinds, and is turned back into a
// conflict value immediately outside. Returning nil from inside would commit the append it is
// refusing.
var errConditionBroken = errBroken{}

type errBroken struct{}

func (errBroken) Error() string { return "the condition no longer holds" }

func (s *Store) ReindexTags(ctx context.Context, fromPosition int64) (int, error) {
	indexed := 0
	err := s.database.InUnitOfWork(ctx, func(context.Context) error {
		s.database.mutex.Lock()
		defer s.database.mutex.Unlock()
		for _, event := range s.database.log {
			if event.GlobalPosition < fromPosition {
				continue
			}
			if _, already := s.database.tags[event.GlobalPosition]; already {
				continue
			}
			tags := s.tagsOf(event.DomainEvent)
			if len(tags) == 0 {
				continue
			}
			s.database.tags[event.GlobalPosition] = slices.Clone(tags)
			indexed++
		}
		return nil
	})
	return indexed, err
}

func (s *Store) Retag(ctx context.Context, tagsOf events.TagsOf) (int, error) {
	indexed := 0
	err := s.database.InUnitOfWork(ctx, func(inside context.Context) error {
		s.database.mutex.Lock()
		s.tagsOf = tagsOf
		s.database.tags = map[int64][]string{}
		s.database.mutex.Unlock()

		var err error
		indexed, err = s.ReindexTags(inside, 0)
		return err
	})
	return indexed, err
}
