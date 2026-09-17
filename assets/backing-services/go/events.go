// Package events holds the event-store port and the envelope it carries.
//
// Five capabilities, and a store that cannot offer all five must not be adopted:
//
//  1. append with an expected version (optimistic concurrency, one stream at a time)
//  2. ordered reads of a single stream
//  3. replay from position zero, across all streams
//  4. reads by tag query, which return the store head as well as the events
//  5. append conditional on a tag query — the same guarantee as (1) over a boundary that is not
//     one stream
//
// The last two are the Dynamic Consistency Boundary, and they are additive: a stream and its
// expectedVersion remain the default boundary, and every slice generated so far uses nothing else.
// docs/adr/0001-a-dcb-capable-log.md in the factory that made this project records why the log
// carries both. A tag is the more general of the two — stream-per-aggregate is the case where every
// event carries exactly one tag, "stream:<streamID>", which is what DefaultTagsOf below returns.
//
// Nothing here names Postgres, SQL, or a vendor. Every adapter under adapters/driven
// implements it, and the same contract suite runs against all of them.
package events

import (
	"context"
	"fmt"
	"regexp"
	"slices"
	"strings"
)

// NoStream is the expectedVersion for a stream that must not exist yet, which is how
// first-write races are detected.
const NoStream = -1

// Actor is who or what caused the event. Recorded on every event so the log answers
// "who did this".
type Actor struct {
	Kind string
	ID   string
}

// CorrelationID and CausationID are **UUIDs**, and named types rather than bare strings. They are
// written by one service and read by another, often years later by a tool nobody has written yet,
// so the one thing they must be is unambiguous: a UUID is unique without a registry, parses the
// same everywhere, and cannot quietly become a request path, a customer reference, or an empty
// string that nothing rejects.
//
// Two types rather than one used twice, because they sit side by side in every event below and are
// both strings underneath. Were they one type, swapping them would compile — and it destroys the
// one thing they exist for, leaving a causal tree in which everything appears to have caused
// itself.
//
// Go has no UUID in its standard library, so what these carry is a string that has been checked,
// deliberately without a dependency. A conversion can still make one out of any string; the
// constructors below are where the check lives, and every adapter reads through them.
type (
	CorrelationID string
	CausationID   string
)

var uuidPattern = regexp.MustCompile(
	`^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$`,
)

// asUUID lower-cases on the way through, so one id has one spelling. Postgres hands back the
// canonical form whatever went in, and a store that kept the caller's casing would compare unequal
// to the same id read back from a uuid column.
func asUUID(raw string, what string) (string, error) {
	if !uuidPattern.MatchString(raw) {
		return "", fmt.Errorf("a %s must be a UUID, and %q is not", what, raw)
	}
	return strings.ToLower(raw), nil
}

// NewCorrelationID parses an incoming correlation id — or a freshly generated one, to start a new
// business transaction. Parsing at the edge is what keeps the type honest: a value that arrived as
// text, from a header, a queue message, or a stored row, is checked once, here, rather than trusted
// everywhere.
func NewCorrelationID(raw string) (CorrelationID, error) {
	checked, err := asUUID(raw, "correlation id")
	return CorrelationID(checked), err
}

// NewCausationID parses the id of the message that directly caused an event. The rule, from Greg
// Young: responding to a message, you copy its correlation id as your own and take its id as your
// causation id.
func NewCausationID(raw string) (CausationID, error) {
	checked, err := asUUID(raw, "causation id")
	return CausationID(checked), err
}

// DomainEvent is a fact the domain decided on, before any store has seen it.
type DomainEvent struct {
	Type          string
	SchemaVersion int
	StreamID      string
	Payload       map[string]any

	// OccurredAt is domain time, as an ISO-8601 instant. Taken from a clock at the edge and
	// passed in as a typed input — the domain never reads the clock, which is what makes a
	// decision function testable without freezing global time. Distinct from RecordedAt, and
	// conflating the two is how clock problems become unreconcilable.
	OccurredAt string

	Actor Actor

	// CorrelationID is the whole business transaction this event belongs to.
	CorrelationID CorrelationID
	// CausationID is the message that directly caused this event, and empty when nothing did —
	// the first event of a transaction has no cause to point at, and inventing one would be a lie
	// about the shape of the tree.
	CausationID CausationID
}

// CommittedEvent is what the store gives back: the event plus the facts only the store knows.
type CommittedEvent struct {
	DomainEvent

	Version        int
	GlobalPosition int64
	RecordedAt     string
}

// Outcome distinguishes the two ways an append can end.
type Outcome string

const (
	OutcomeAppended        Outcome = "appended"
	OutcomeVersionConflict Outcome = "version-conflict"
)

// AppendResult reports the outcome of an append.
//
// A version conflict is a **value, not an error**. Contention is expected under load, not
// exceptional: the caller re-reads and re-decides. Returning it as an error would put ordinary
// concurrency on the error path, where the next reader cannot tell it from a broken connection.
type AppendResult struct {
	Outcome Outcome

	// Version is the stream's new head version, when the append succeeded.
	Version int
	// ActualVersion is where the stream really was, when it did not.
	ActualVersion int
}

// Appended reports a successful append ending at version.
func Appended(version int) AppendResult {
	return AppendResult{Outcome: OutcomeAppended, Version: version}
}

// VersionConflict reports that the stream was not where the caller thought it was.
func VersionConflict(actualVersion int) AppendResult {
	return AppendResult{Outcome: OutcomeVersionConflict, ActualVersion: actualVersion}
}

// ── The other consistency boundary ──────────────────────────────────────────────────────────────
//
// Everything from here to Store is the Dynamic Consistency Boundary. Read it only when a decision
// cannot be guarded by one stream's version — a constraint spanning two entities, where either can
// change under you. Until then Append is the whole port.

// StreamTag is the tag every event carries by default: its own stream, as a tag.
//
// A function rather than an inlined string because it is the one place the correspondence between
// the two boundaries is spelled: a stream id *is* a tag, so a log that indexes tags indexes the
// streams it already had.
func StreamTag(streamID string) string { return "stream:" + streamID }

// TagsOf is how an adapter learns what to index an event by. A plain function, so a project's
// tagging rule is testable without a database.
type TagsOf func(DomainEvent) []string

// DefaultTagsOf is what an event is indexed by, unless this project says otherwise.
//
// Tags are derived, never modelled: nothing in docs/event-model/model.yaml names one, because a
// tag is a technical index over the log and not a fact about the business. A project's own tagging
// function is where it decides what its events are findable by — usually the identifying
// attributes of the payload, alongside the stream:
//
//	func tagsOf(event events.DomainEvent) []string {
//		tags := []string{events.StreamTag(event.StreamID)}
//		if courseID, ok := event.Payload["courseId"].(string); ok {
//			tags = append(tags, "course:"+courseID)
//		}
//		return tags
//	}
//
// Pass it to the adapter's constructor. Changing it later is safe and cheap — the index is
// derived, so Retag rebuilds it from the log — which is the whole reason tags live in an index of
// their own rather than on the event row.
func DefaultTagsOf(event DomainEvent) []string { return []string{StreamTag(event.StreamID)} }

// TagFilter is one conjunction: an event matches when it carries every tag named here and, where
// Types names any, when its type is one of them. A filter naming neither matches nothing — see
// TagQuery.
type TagFilter struct {
	Tags  []string
	Types []string
}

// Matches reports whether one event matches this filter, given the tags it was indexed by.
//
// In the port rather than in each adapter because it is the definition, and an adapter that
// computed it differently in SQL would be a second definition nothing compares. The in-memory
// adapter uses this directly; the SQL adapters translate it, and the contract suite is what holds
// the translation to it.
func (f TagFilter) Matches(event CommittedEvent, tags []string) bool {
	if len(f.Tags) == 0 && len(f.Types) == 0 {
		return false
	}
	if len(f.Types) > 0 && !slices.Contains(f.Types, event.Type) {
		return false
	}
	for _, tag := range f.Tags {
		if !slices.Contains(tags, tag) {
			return false
		}
	}
	return true
}

// TagQuery is which events a decision loads, and — as part of a Condition — which events
// invalidate it.
//
// A disjunction of filters, because the constraint that motivates any of this spans entities:
// deciding whether a student may subscribe to a course needs the course's events *and* that
// student's events, which is two filters and cannot be one. Think of it as the SQL query that
// fetches exactly the events needed to decide.
//
// An empty query matches nothing, never everything. A condition that matched everything would
// refuse every concurrent append in the system, and a read that matched everything would quietly
// become a full replay; both are failures worth being loud about, and neither is what anybody
// meant to write.
type TagQuery struct {
	Filters []TagFilter
}

// Matches reports whether any of the query's filters matches the event.
func (q TagQuery) Matches(event CommittedEvent, tags []string) bool {
	for _, filter := range q.Filters {
		if filter.Matches(event, tags) {
			return true
		}
	}
	return false
}

// TaggedRead is what a decision was made from, and the position it was made at.
//
// Head is the store's last global position at the moment of the read — zero for an empty log. It
// is not a nicety: it is the anchor a Condition is built from, so "these are the facts I decided
// on" and "nothing else has happened since" are one round trip rather than two that can disagree.
//
// It is also read-your-writes made concrete. A caller that appends and then needs a
// subscription-maintained view to have caught up can wait for a specific position instead of
// polling blindly.
type TaggedRead struct {
	Events []CommittedEvent
	Head   int64
}

// Condition is the guard on a conditional append: Query must have matched nothing after After.
//
// After is the Head of the TaggedRead the decision was made from. The pair is the boundary —
// dynamic because the caller draws it per decision, out of tags, rather than inheriting it from
// how streams were laid out months earlier.
type Condition struct {
	Query TagQuery
	After int64
}

// The two ways a conditional append can end.
const (
	OutcomeRecorded          Outcome = "recorded"
	OutcomeConditionConflict Outcome = "condition-conflict"
)

// ConditionalAppendResult reports the outcome of a conditional append. Head is the store head as
// found, so a caller that retries reads from there.
//
// A conflict is a value here for the same reason a version conflict is one, and this is where the
// two boundaries agree: contention is ordinary, and a caller re-reads and re-decides.
type ConditionalAppendResult struct {
	Outcome Outcome
	Head    int64
}

// Recorded reports a conditional append that held.
func Recorded(head int64) ConditionalAppendResult {
	return ConditionalAppendResult{Outcome: OutcomeRecorded, Head: head}
}

// ConditionConflict reports that something matching the condition arrived since the caller read.
func ConditionConflict(head int64) ConditionalAppendResult {
	return ConditionalAppendResult{Outcome: OutcomeConditionConflict, Head: head}
}

// Store is the port. Errors are for genuine failures — a lost connection, a corrupt row — never
// for a version conflict.
type Store interface {
	Read(ctx context.Context, streamID string) ([]CommittedEvent, error)

	Append(
		ctx context.Context,
		streamID string,
		expectedVersion int,
		events []DomainEvent,
	) (AppendResult, error)

	// ReadAll replays across all streams from a global position, calling visit for each event in
	// order and stopping if it returns an error.
	//
	// This exists so read models can be rebuilt from zero — without it they are not disposable,
	// and a projection bug becomes unfixable. A visitor rather than a returned slice, so a
	// rebuild over a long log does not materialise the whole thing in memory.
	ReadAll(ctx context.Context, fromPosition int64, visit func(CommittedEvent) error) error

	// InUnitOfWork runs work in one transaction, which an append and somebody else's write share.
	//
	// Inside work, Append and AppendIf do not commit: returning nil commits everything once, and
	// returning an error rolls all of it back. Outside it they commit themselves, exactly as they
	// always have, so nothing already written needs to know this exists.
	//
	// The transaction travels in the context work is given, which is why work takes one: pass
	// that context to every call that must be part of it, and a call given the outer context is
	// not. Two things need this, and they are the same need. A read model materialised inline is
	// written here, so a query can never see an event whose view row is missing — and a failed
	// view write takes the append down with it. A projection maintained asynchronously records
	// its checkpoint here, in the same transaction as the rows it derived, which is what makes it
	// exactly-once rather than approximately-once. A checkpoint committed separately from the
	// view it describes is not a checkpoint; it is a race with a number in it.
	//
	// Nesting is allowed: the outermost call owns the commit.
	InUnitOfWork(ctx context.Context, work func(context.Context) error) error

	// Head is the last global position in the log, or zero when it is empty.
	//
	// The boundary a decision is made against, taken once and then handed to every read that
	// decision needs. A command that reads twice and uses the second read's head has promised
	// something it never checked: an event matching the first query could have arrived between the
	// two reads, before that head, and the conditional append would not look for it. Pin it here,
	// pass it as until, and that mistake has nowhere to happen:
	//
	//	boundary, err := store.Head(ctx)
	//	course, err := store.ReadTagged(ctx, byCourse, 0, boundary)
	//	student, err := store.ReadTagged(ctx, byStudent, 0, boundary)
	//	result, err := store.AppendIf(ctx, events.Condition{Query: both, After: boundary}, batch)
	Head(ctx context.Context) (int64, error)

	// ReadTagged returns the events matching query in (after, until], and the position they are as
	// of.
	//
	// This is the DCB read: what a decision loads. after is for resuming a long read, not for the
	// guard. until is the ceiling — zero for none, which is every position, since the log starts at
	// one — and it is what a decision reading twice pins first, so both reads see the same log. The
	// Head handed back is what the facts are as of: until when it is given, the store's head when it
	// is not, and either way it is what a Condition is built from.
	ReadTagged(ctx context.Context, query TagQuery, after int64, until int64) (TaggedRead, error)

	// AppendIf appends only if nothing matching condition.Query was recorded after
	// condition.After.
	//
	// The events still name their streams and still land at gapless per-stream versions — the
	// store assigns each one the next version of the stream it names — so Read, folds and every
	// slice written against Append keep working unchanged. What differs is only what the write is
	// guarded by.
	AppendIf(
		ctx context.Context,
		condition Condition,
		events []DomainEvent,
	) (ConditionalAppendResult, error)

	// ReindexTags indexes events this store's tagging function has not indexed yet, and reports
	// how many.
	//
	// The verb an already-running project needs: applying the migration creates an empty index,
	// and this is what fills it from the history that is already there. Idempotent, so running it
	// twice indexes nothing the second time and a run that died halfway is resumed by running it
	// again.
	ReindexTags(ctx context.Context, fromPosition int64) (int, error)

	// Retag adopts a new tagging function and rebuilds the whole index under it, reporting how
	// many events were indexed.
	//
	// Because the index is derived, what a project tags is a decision it can change — unlike the
	// events themselves. Both halves happen together on purpose: an index rebuilt under one
	// function while appends carry on under another is an index that disagrees with itself.
	Retag(ctx context.Context, tagsOf TagsOf) (int, error)
}

// CurrentVersion is the expected version to pass when appending to a stream just read.
func CurrentVersion(events []CommittedEvent) int {
	if len(events) == 0 {
		return NoStream
	}
	return events[len(events)-1].Version
}
