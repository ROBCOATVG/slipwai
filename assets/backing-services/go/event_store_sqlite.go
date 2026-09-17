// Package eventstoresqlite holds the SQLite event-store adapter — a real append-only log in one
// file, with no container to run.
//
// Chosen when durability matters and infrastructure does not: a single-process service, a CLI, a
// long-running worker, or a demo that must survive a restart.
//
// Understand the one thing it cannot do before adopting it: SQLite serialises writers. It proves
// durability and it proves the append-only rule, but it CANNOT prove concurrent behaviour,
// because it never genuinely races. If the never-write-the-same-version-twice guarantee matters
// to your product, prove it on Postgres — `make test-integration` there races two appends at one
// version and requires exactly one winner.
//
// modernc.org/sqlite is a pure-Go translation of SQLite, so this adapter needs no cgo and the
// build stays a plain `go build` on every platform.
//
// Unlike Postgres, the schema ships with the adapter rather than as a migration: an embedded
// database is created by the process that opens it, so there is no separate `make migrate` step
// and nothing to run before the first test. The three tables below are the same three the Postgres
// migrations create — the log, the projection checkpoints, and the derived tag index — because two
// spellings of one schema drift and nothing notices.
package eventstoresqlite

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"strings"

	// Registers the "sqlite" driver with database/sql. Blank-imported because nothing in this
	// file names the driver's own types — that is the whole point of database/sql.
	_ "modernc.org/sqlite"

	"example.com/delivery-starter/application/ports/events"
)

// GlobalPosition is INTEGER PRIMARY KEY, which in SQLite aliases the monotonic rowid — the
// ReadAll ordering the port promises. The append-only guarantee is enforced in the database
// rather than in this file, because a rule the application enforces is a rule the next process
// to open the file will not.
const schema = `
  CREATE TABLE IF NOT EXISTS events (
    global_position INTEGER PRIMARY KEY,
    stream_id       TEXT    NOT NULL,
    version         INTEGER NOT NULL,
    event_type      TEXT    NOT NULL,
    schema_version  INTEGER NOT NULL,
    payload         TEXT    NOT NULL,
    actor           TEXT    NOT NULL,
    -- SQLite has no UUID type, so the canonical text form is what is stored. Postgres uses a real
    -- uuid column; both round-trip through the same value type, and the adapter is where that
    -- difference stops.
    correlation_id  TEXT    NOT NULL,
    causation_id    TEXT,
    occurred_at     TEXT    NOT NULL,
    recorded_at     TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    CONSTRAINT events_stream_version_unique UNIQUE (stream_id, version),
    CONSTRAINT events_version_non_negative CHECK (version >= 0)
  );

  CREATE INDEX IF NOT EXISTS events_stream_id_version ON events (stream_id, version);

  CREATE TRIGGER IF NOT EXISTS events_reject_update
  BEFORE UPDATE ON events
  BEGIN
    SELECT RAISE(ABORT, 'events is append-only: UPDATE is rejected');
  END;

  CREATE TRIGGER IF NOT EXISTS events_reject_delete
  BEFORE DELETE ON events
  BEGIN
    SELECT RAISE(ABORT, 'events is append-only: DELETE is rejected');
  END;

  -- Where each projection has got to. Mutable by design, and deliberately with no trigger: a
  -- checkpoint is a position that moves, and everything derived from the log can be thrown away
  -- and rebuilt. The lease columns are how exactly one worker advances it, with an expiry so that
  -- survives the worker dying.
  CREATE TABLE IF NOT EXISTS projection_checkpoints (
    projection        TEXT    PRIMARY KEY,
    position          INTEGER NOT NULL DEFAULT 0,
    lease_owner       TEXT,
    lease_expires_at  TEXT,
    updated_at        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    CONSTRAINT projection_checkpoints_position_non_negative CHECK (position >= 0),
    CONSTRAINT projection_checkpoints_lease_is_whole CHECK (
      (lease_owner IS NULL) = (lease_expires_at IS NULL)
    )
  );

  -- The tag index — the Dynamic Consistency Boundary's half of the log. Derived from the events by
  -- this project's tagging function, written inside the append's own transaction, and rebuildable
  -- at any time, which is what lets a running project adopt tags without rewriting a log it is
  -- forbidden to rewrite.
  CREATE TABLE IF NOT EXISTS event_tags (
    tag             TEXT    NOT NULL,
    global_position INTEGER NOT NULL REFERENCES events (global_position),
    PRIMARY KEY (tag, global_position)
  );

  CREATE INDEX IF NOT EXISTS event_tags_global_position ON event_tags (global_position);
`

const insertGuarded = `
  INSERT INTO events (
    stream_id, version, event_type, schema_version, payload, actor,
    correlation_id, causation_id, occurred_at
  )
  SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?
  WHERE (SELECT COALESCE(MAX(version), -1) FROM events WHERE stream_id = ?) = ?
`

const eventColumns = `
  global_position, stream_id, version, event_type, schema_version, payload, actor,
  correlation_id, causation_id, occurred_at, recorded_at
`

const currentVersionQuery = `SELECT COALESCE(MAX(version), -1) FROM events WHERE stream_id = ?`

const headQuery = `SELECT COALESCE(MAX(global_position), 0) FROM events`

const insertTag = `INSERT OR IGNORE INTO event_tags (tag, global_position) VALUES (?, ?)`

const deleteTags = `DELETE FROM event_tags`

const unindexedEvents = `SELECT ` + eventColumns + `
  FROM events
  WHERE global_position >= ?
    AND NOT EXISTS (SELECT 1 FROM event_tags WHERE global_position = events.global_position)
  ORDER BY global_position ASC
`

// readAllBatchSize keeps a rebuild over a long log from materialising the whole thing in memory.
const readAllBatchSize = 500

// Store is a SQLite-backed events.Store.
type Store struct {
	db     *sql.DB
	tagsOf events.TagsOf
}

// Executor is somewhere to run SQL: the database, or the transaction a unit of work opened.
//
// Exported because the checkpoint adapter is built from this store and has to run its statements
// on whatever this store's current transaction is. With one connection — which this adapter
// deliberately keeps — a statement sent to the database while a transaction holds that connection
// would wait for a transaction that is waiting for it.
type Executor interface {
	ExecContext(ctx context.Context, query string, args ...any) (sql.Result, error)
	QueryContext(ctx context.Context, query string, args ...any) (*sql.Rows, error)
	QueryRowContext(ctx context.Context, query string, args ...any) *sql.Row
}

// unitOfWork is the open transaction, carried in the context rather than in the Store, so
// concurrent callers cannot end up inside each other's transactions.
type unitOfWork struct {
	tx    *sql.Tx
	depth int
}

type unitOfWorkKey struct{}

// Executor returns the transaction this context is inside, or the database when it is inside none.
func (s *Store) Executor(ctx context.Context) Executor {
	if open, ok := ctx.Value(unitOfWorkKey{}).(unitOfWork); ok {
		return open.tx
	}
	return s.db
}

// InUnitOfWork runs work in one transaction, which an append and somebody else's write share.
//
// Nesting uses a SAVEPOINT rather than a counter that shrugs: an inner block that fails has to
// undo its own writes and no more, and the alternative — leaving them in the outer transaction —
// would let a refused append pollute a transaction that goes on to commit.
func (s *Store) InUnitOfWork(ctx context.Context, work func(context.Context) error) error {
	if open, ok := ctx.Value(unitOfWorkKey{}).(unitOfWork); ok {
		name := fmt.Sprintf("uow_%d", open.depth+1)
		if _, err := open.tx.ExecContext(ctx, "SAVEPOINT "+name); err != nil {
			return fmt.Errorf("open savepoint %s: %w", name, err)
		}
		inside := context.WithValue(ctx, unitOfWorkKey{}, unitOfWork{tx: open.tx, depth: open.depth + 1})
		if err := work(inside); err != nil {
			_, _ = open.tx.ExecContext(ctx, "ROLLBACK TO SAVEPOINT "+name)
			return err
		}
		if _, err := open.tx.ExecContext(ctx, "RELEASE SAVEPOINT "+name); err != nil {
			return fmt.Errorf("release savepoint %s: %w", name, err)
		}
		return nil
	}

	transaction, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("begin a unit of work: %w", err)
	}
	if err := work(context.WithValue(ctx, unitOfWorkKey{}, unitOfWork{tx: transaction, depth: 1})); err != nil {
		_ = transaction.Rollback()
		return err
	}
	if err := transaction.Commit(); err != nil {
		return fmt.Errorf("commit a unit of work: %w", err)
	}
	return nil
}

// Open opens (or creates) a SQLite-backed event store, tagging events by their own stream.
//
// location is a file path, or ":memory:" for a store that exists only as long as the process —
// which is what the contract suite uses, so the same SQL runs in `make verify` with nothing
// installed.
func Open(location string) (*Store, error) {
	return OpenTagged(location, events.DefaultTagsOf)
}

// OpenTagged is Open with this project's own tagging function — what its events are findable by
// beyond their stream.
func OpenTagged(location string, tagsOf events.TagsOf) (*Store, error) {
	db, err := sql.Open("sqlite", location)
	if err != nil {
		return nil, fmt.Errorf("open sqlite at %s: %w", location, err)
	}
	// One connection, deliberately. SQLite serialises writers anyway, and for ":memory:" a second
	// connection would open a second, empty database — which reads as data loss.
	db.SetMaxOpenConns(1)

	// WAL lets readers run while a writer holds the write lock, and is a no-op for ":memory:".
	// FULL synchronous is the default and is what makes a committed append survive a power loss;
	// anything weaker trades the D in ACID for throughput, which an event log cannot afford.
	for _, pragma := range []string{"PRAGMA journal_mode = WAL", "PRAGMA foreign_keys = ON"} {
		if _, err := db.Exec(pragma); err != nil {
			db.Close()
			return nil, fmt.Errorf("%s: %w", pragma, err)
		}
	}
	if _, err := db.Exec(schema); err != nil {
		db.Close()
		return nil, fmt.Errorf("apply sqlite schema: %w", err)
	}
	return &Store{db: db, tagsOf: tagsOf}, nil
}

// Close releases the underlying database handle.
func (s *Store) Close() error { return s.db.Close() }

func (s *Store) currentVersion(ctx context.Context, streamID string) (int, error) {
	var version int
	row := s.Executor(ctx).QueryRowContext(ctx, currentVersionQuery, streamID)
	if err := row.Scan(&version); err != nil {
		return 0, fmt.Errorf("read current version of %s: %w", streamID, err)
	}
	return version, nil
}

func (s *Store) head(ctx context.Context) (int64, error) {
	var head int64
	if err := s.Executor(ctx).QueryRowContext(ctx, headQuery).Scan(&head); err != nil {
		return 0, fmt.Errorf("read the store head: %w", err)
	}
	return head, nil
}

func (s *Store) Read(ctx context.Context, streamID string) ([]events.CommittedEvent, error) {
	query := `SELECT ` + eventColumns + ` FROM events WHERE stream_id = ? ORDER BY version ASC`
	rows, err := s.Executor(ctx).QueryContext(ctx, query, streamID)
	if err != nil {
		return nil, fmt.Errorf("read stream %s: %w", streamID, err)
	}
	defer rows.Close()

	var stream []events.CommittedEvent
	for rows.Next() {
		event, err := scanEvent(rows)
		if err != nil {
			return nil, err
		}
		stream = append(stream, event)
	}
	return stream, rows.Err()
}

func (s *Store) Append(
	ctx context.Context,
	streamID string,
	expectedVersion int,
	batch []events.DomainEvent,
) (events.AppendResult, error) {
	if len(batch) == 0 {
		return events.Appended(expectedVersion), nil
	}

	version := expectedVersion
	err := s.InUnitOfWork(ctx, func(inside context.Context) error {
		version = expectedVersion
		for _, event := range batch {
			guardAgainst := version
			version++
			if err := s.insert(inside, event, streamID, version, guardAgainst); err != nil {
				return err
			}
		}
		return nil
	})

	switch {
	case errors.Is(err, errStale), err != nil && isConstraintViolation(err):
		// A conflict is a value rather than an error, because contention is expected under load,
		// not exceptional. The guard catches a stale expectation; the unique constraint catches
		// what the guard could not, which on SQLite is close to unreachable — one writer at a
		// time — but is reported the way Postgres reports it so that moving is a change of
		// adapter rather than of caller.
		actualVersion, readErr := s.currentVersion(ctx, streamID)
		if readErr != nil {
			return events.AppendResult{}, readErr
		}
		return events.VersionConflict(actualVersion), nil
	case err != nil:
		return events.AppendResult{}, fmt.Errorf("append to %s: %w", streamID, err)
	}
	return events.Appended(version), nil
}

// errStale and errConditionBroken travel out of a unit of work so it unwinds, and are turned back
// into conflict *values* immediately outside it. Returning nil from inside would commit the
// half-written append being refused.
var (
	errStale           = errors.New("the stream is not where the caller thought it was")
	errConditionBroken = errors.New("the condition no longer holds")
)

// insert writes one event, plus its tags, inside whatever transaction is open.
//
// The tags go in here rather than in a pass of their own, which is the whole design: an index
// written after the append could be missing when the next conditional append checks it, and that
// append would then be guarded by a boundary with a hole in it.
func (s *Store) insert(
	ctx context.Context,
	event events.DomainEvent,
	streamID string,
	version int,
	guardAgainst int,
) error {
	payload, actor, err := encode(event)
	if err != nil {
		return err
	}
	executor := s.Executor(ctx)
	result, err := executor.ExecContext(ctx, insertGuarded,
		streamID, version, event.Type, event.SchemaVersion, payload, actor,
		string(event.CorrelationID), nullable(string(event.CausationID)), event.OccurredAt,
		streamID, guardAgainst,
	)
	if err != nil {
		return err
	}
	affected, err := result.RowsAffected()
	if err != nil {
		return err
	}
	if affected == 0 {
		return errStale
	}
	position, err := result.LastInsertId()
	if err != nil {
		return err
	}
	event.StreamID = streamID
	for _, tag := range s.tagsOf(event) {
		if _, err := executor.ExecContext(ctx, insertTag, tag, position); err != nil {
			return err
		}
	}
	return nil
}

func (s *Store) ReadAll(
	ctx context.Context,
	fromPosition int64,
	visit func(events.CommittedEvent) error,
) error {
	query := `SELECT ` + eventColumns + `
	  FROM events WHERE global_position >= ? ORDER BY global_position ASC LIMIT ?`
	position := fromPosition
	for {
		rows, err := s.Executor(ctx).QueryContext(ctx, query, position, readAllBatchSize)
		if err != nil {
			return fmt.Errorf("replay from %d: %w", position, err)
		}
		var batch []events.CommittedEvent
		for rows.Next() {
			event, err := scanEvent(rows)
			if err != nil {
				rows.Close()
				return err
			}
			batch = append(batch, event)
		}
		if err := rows.Err(); err != nil {
			rows.Close()
			return err
		}
		rows.Close()

		if len(batch) == 0 {
			return nil
		}
		for _, event := range batch {
			if err := visit(event); err != nil {
				return err
			}
		}
		position = batch[len(batch)-1].GlobalPosition + 1
	}
}

// tagQuerySQL is a TagQuery as a SQL predicate over `e`, plus its arguments.
//
// TagFilter.Matches in the port is the definition; this is a translation of it, and the contract
// suite is what holds the two to each other. Every branch here has a case there:
//
//   - a filter's tags are a conjunction, so the count of its tags found against the event must
//     equal how many it named — IN alone would be an "any of", which is a different and much
//     weaker guard;
//   - a filter's types narrow within that filter, never across the query;
//   - a filter naming neither matches nothing, and a query with no filters matches nothing. `1 = 0`
//     rather than an omitted predicate, because an absent guard would match everything and a
//     conditional append that matched everything would refuse every write in the system.
func tagQuerySQL(query events.TagQuery) (string, []any) {
	if len(query.Filters) == 0 {
		return "1 = 0", nil
	}
	var (
		predicates []string
		arguments  []any
	)
	for _, filter := range query.Filters {
		if len(filter.Tags) == 0 && len(filter.Types) == 0 {
			predicates = append(predicates, "1 = 0")
			continue
		}
		var parts []string
		if len(filter.Tags) > 0 {
			parts = append(parts, `(SELECT COUNT(*) FROM event_tags t`+
				` WHERE t.global_position = e.global_position`+
				` AND t.tag IN (`+placeholders(len(filter.Tags))+`)) = ?`)
			for _, tag := range filter.Tags {
				arguments = append(arguments, tag)
			}
			arguments = append(arguments, len(distinct(filter.Tags)))
		}
		if len(filter.Types) > 0 {
			parts = append(parts, `e.event_type IN (`+placeholders(len(filter.Types))+`)`)
			for _, eventType := range filter.Types {
				arguments = append(arguments, eventType)
			}
		}
		predicates = append(predicates, "("+strings.Join(parts, " AND ")+")")
	}
	return "(" + strings.Join(predicates, " OR ") + ")", arguments
}

func placeholders(count int) string {
	return strings.TrimSuffix(strings.Repeat("?, ", count), ", ")
}

func distinct(values []string) []string {
	seen := make(map[string]struct{}, len(values))
	var unique []string
	for _, value := range values {
		if _, already := seen[value]; already {
			continue
		}
		seen[value] = struct{}{}
		unique = append(unique, value)
	}
	return unique
}

func (s *Store) Head(ctx context.Context) (int64, error) {
	return s.head(ctx)
}

func (s *Store) ReadTagged(
	ctx context.Context,
	query events.TagQuery,
	after int64,
	until int64,
) (events.TaggedRead, error) {
	ceiling, err := s.ceiling(ctx, until)
	if err != nil {
		return events.TaggedRead{}, err
	}
	predicate, arguments := tagQuerySQL(query)
	statement := `SELECT ` + eventColumns + ` FROM events e` +
		` WHERE e.global_position > ? AND e.global_position <= ? AND ` + predicate +
		` ORDER BY e.global_position ASC`
	rows, err := s.Executor(ctx).QueryContext(
		ctx, statement, append([]any{after, ceiling}, arguments...)...)
	if err != nil {
		return events.TaggedRead{}, fmt.Errorf("read by tag query: %w", err)
	}
	defer rows.Close()

	var found []events.CommittedEvent
	for rows.Next() {
		event, err := scanEvent(rows)
		if err != nil {
			return events.TaggedRead{}, err
		}
		found = append(found, event)
	}
	if err := rows.Err(); err != nil {
		return events.TaggedRead{}, err
	}
	return events.TaggedRead{Events: found, Head: ceiling}, nil
}

// ceiling is the position a tagged read stops at: the one the caller pinned, or the store's head
// when it pinned none. Zero means none, which is every position, since the log starts at one.
func (s *Store) ceiling(ctx context.Context, until int64) (int64, error) {
	if until != 0 {
		return until, nil
	}
	return s.head(ctx)
}

func (s *Store) anythingMatching(ctx context.Context, condition events.Condition) (bool, error) {
	predicate, arguments := tagQuerySQL(condition.Query)
	statement := `SELECT 1 FROM events e WHERE e.global_position > ? AND ` + predicate + ` LIMIT 1`
	rows, err := s.Executor(ctx).QueryContext(
		ctx, statement, append([]any{condition.After}, arguments...)...,
	)
	if err != nil {
		return false, fmt.Errorf("check a condition: %w", err)
	}
	defer rows.Close()
	return rows.Next(), rows.Err()
}

// AppendIf is the conditional append. SQLite gives the isolation for free.
//
// BeginTx takes the write lock before the condition is checked and holds it through the inserts,
// and SQLite has one writer at a time, so the check and the write cannot be split by another
// transaction. Postgres has to ask for SERIALIZABLE to get the same thing, and pays for it with a
// retry path; here there is nothing to retry.
func (s *Store) AppendIf(
	ctx context.Context,
	condition events.Condition,
	batch []events.DomainEvent,
) (events.ConditionalAppendResult, error) {
	err := s.InUnitOfWork(ctx, func(inside context.Context) error {
		matching, err := s.anythingMatching(inside, condition)
		if err != nil {
			return err
		}
		if matching {
			return errConditionBroken
		}
		for _, event := range batch {
			// Each event still lands at the next version of the stream it names, so everything
			// written against Read and Append keeps working: what the condition replaced is the
			// guard, not the shape of the log.
			at, err := s.currentVersion(inside, event.StreamID)
			if err != nil {
				return err
			}
			if err := s.insert(inside, event, event.StreamID, at+1, at); err != nil {
				return err
			}
		}
		return nil
	})

	head, headErr := s.head(ctx)
	if headErr != nil {
		return events.ConditionalAppendResult{}, headErr
	}
	if errors.Is(err, errConditionBroken) {
		return events.ConditionConflict(head), nil
	}
	if err != nil {
		return events.ConditionalAppendResult{}, fmt.Errorf("conditional append: %w", err)
	}
	return events.Recorded(head), nil
}

func (s *Store) ReindexTags(ctx context.Context, fromPosition int64) (int, error) {
	indexed := 0
	err := s.InUnitOfWork(ctx, func(inside context.Context) error {
		rows, err := s.Executor(inside).QueryContext(inside, unindexedEvents, fromPosition)
		if err != nil {
			return err
		}
		var unindexed []events.CommittedEvent
		for rows.Next() {
			event, err := scanEvent(rows)
			if err != nil {
				rows.Close()
				return err
			}
			unindexed = append(unindexed, event)
		}
		if err := rows.Err(); err != nil {
			rows.Close()
			return err
		}
		rows.Close()

		executor := s.Executor(inside)
		for _, event := range unindexed {
			tags := s.tagsOf(event.DomainEvent)
			if len(tags) == 0 {
				// Counted only when it made the event findable. An event this project's tagging
				// function has nothing to say about stays unindexed for good, so a run that counted
				// it would promise an index with nothing in it and never settle at zero.
				continue
			}
			for _, tag := range tags {
				if _, err := executor.ExecContext(inside, insertTag, tag, event.GlobalPosition); err != nil {
					return err
				}
			}
			indexed++
		}
		return nil
	})
	if err != nil {
		return 0, fmt.Errorf("reindex tags: %w", err)
	}
	return indexed, nil
}

func (s *Store) Retag(ctx context.Context, tagsOf events.TagsOf) (int, error) {
	indexed := 0
	err := s.InUnitOfWork(ctx, func(inside context.Context) error {
		s.tagsOf = tagsOf
		if _, err := s.Executor(inside).ExecContext(inside, deleteTags); err != nil {
			return err
		}
		var err error
		// Inside this unit of work, so the old index is never visible as gone: either the whole
		// re-index commits or the old one stands.
		indexed, err = s.ReindexTags(inside, 0)
		return err
	})
	if err != nil {
		return 0, fmt.Errorf("retag: %w", err)
	}
	return indexed, nil
}

func isConstraintViolation(err error) bool {
	// Matched on the driver's message rather than a typed code: modernc.org/sqlite reports a
	// constraint failure as a plain error, and the alternative is importing its internal error
	// package into an adapter that has no other reason to know which driver it is using.
	return strings.Contains(err.Error(), "constraint failed")
}

func nullable(value string) any {
	if value == "" {
		return nil
	}
	return value
}

func encode(event events.DomainEvent) (string, string, error) {
	payload, err := json.Marshal(event.Payload)
	if err != nil {
		return "", "", fmt.Errorf("encode payload of %s: %w", event.Type, err)
	}
	actor, err := json.Marshal(map[string]string{"kind": event.Actor.Kind, "id": event.Actor.ID})
	if err != nil {
		return "", "", fmt.Errorf("encode actor of %s: %w", event.Type, err)
	}
	return string(payload), string(actor), nil
}

type scannable interface {
	Scan(dest ...any) error
}

// scanEvent parses a stored row back into a CommittedEvent.
//
// Events are validated on read as well as on write, because stored events outlive the code that
// wrote them — a compile-time type says nothing about a row written eighteen months ago. This is
// a tolerant reader on purpose: unknown payload fields written by a newer version are carried
// through rather than rejected, which is what makes a rolling deploy possible. Only the envelope
// itself is required — and its ids are parsed as UUIDs here rather than passed through as text, so
// a row that SQLite was happy to store cannot enter the domain as an identifier nothing can
// correlate.
func scanEvent(row scannable) (events.CommittedEvent, error) {
	var (
		event         events.CommittedEvent
		payload       string
		actor         string
		correlationID string
		causationID   sql.NullString
	)
	err := row.Scan(
		&event.GlobalPosition, &event.StreamID, &event.Version, &event.Type,
		&event.SchemaVersion, &payload, &actor, &correlationID, &causationID,
		&event.OccurredAt, &event.RecordedAt,
	)
	if err != nil {
		return events.CommittedEvent{}, fmt.Errorf("scan event: %w", err)
	}
	if event.SchemaVersion != 1 {
		return events.CommittedEvent{}, fmt.Errorf(
			"event at global_position %d is schema version %d; add an upcaster for it before "+
				"reading it as version 1", event.GlobalPosition, event.SchemaVersion)
	}
	if err := json.Unmarshal([]byte(payload), &event.Payload); err != nil {
		return events.CommittedEvent{}, fmt.Errorf(
			"event at global_position %d has an unreadable payload: %w", event.GlobalPosition, err)
	}
	var decoded map[string]string
	if err := json.Unmarshal([]byte(actor), &decoded); err != nil || decoded["kind"] == "" {
		return events.CommittedEvent{}, fmt.Errorf(
			"event at global_position %d has no usable actor", event.GlobalPosition)
	}
	event.Actor = events.Actor{Kind: decoded["kind"], ID: decoded["id"]}
	event.CorrelationID, err = events.NewCorrelationID(correlationID)
	if err != nil {
		return events.CommittedEvent{}, fmt.Errorf(
			"event at global_position %d: %w", event.GlobalPosition, err)
	}
	if causationID.Valid {
		event.CausationID, err = events.NewCausationID(causationID.String)
		if err != nil {
			return events.CommittedEvent{}, fmt.Errorf(
				"event at global_position %d: %w", event.GlobalPosition, err)
		}
	}
	return event, nil
}
