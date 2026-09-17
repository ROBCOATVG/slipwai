// Package eventstorepostgres holds the Postgres event-store adapter — the only package that
// knows the event log is SQL.
//
// Concurrency is enforced twice over, deliberately:
//
//  1. Each insert carries a WHERE (SELECT MAX(version) ...) = expected guard, which catches a
//     stale expectation — a caller that decided against version 3 while the stream moved to 5.
//  2. The (stream_id, version) unique constraint catches the true race, where two transactions
//     both pass the guard and then try to write the same version.
//
// The guard alone is insufficient (two concurrent transactions see the same MAX under READ
// COMMITTED), and the constraint alone is insufficient (a stale expectation could write a valid
// later version without conflict). Both are needed.
//
// AppendIf can use neither, because there is no version to compare: what it must prove is that
// nothing matching a query arrived since the caller read. It asks Postgres for SERIALIZABLE and
// lets the database prove it. The cost is a real one and it is the caller's: a serialisation
// failure is reported as a conflict, and the caller re-reads and re-decides exactly as it does for
// a stale version.
package eventstorepostgres

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"strings"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
	"github.com/jackc/pgx/v5/pgxpool"

	"example.com/delivery-starter/application/ports/events"
)

// uniqueViolation is Postgres' SQLSTATE for a unique-constraint violation.
const uniqueViolation = "23505"

// serializationFailure is Postgres' SQLSTATE for a SERIALIZABLE transaction that could not be
// ordered against a concurrent one. For a conditional append it means the same thing a broken
// condition does, and asks the same thing of the caller: read again, decide again.
const serializationFailure = "40001"

const insertGuarded = `
  INSERT INTO events (
    stream_id, version, event_type, schema_version, payload, actor,
    correlation_id, causation_id, occurred_at
  )
  SELECT $1, $2, $3, $4, $5::jsonb, $6::jsonb, $7::uuid, $8::uuid, $9::timestamptz
  WHERE (SELECT COALESCE(MAX(version), -1) FROM events WHERE stream_id = $1) = $10
  RETURNING global_position
`

const eventColumns = `
  global_position, stream_id, version, event_type, schema_version, payload, actor,
  -- Cast to text and parsed back into the value type below, the same way every other adapter
  -- reads them. The column is a real uuid; what crosses this boundary is text either way, and
  -- doing it in one place means the driver's UUID mapping is not a thing to know about here.
  correlation_id::text, causation_id::text,
  to_char(occurred_at, 'YYYY-MM-DD"T"HH24:MI:SS.USOF'),
  to_char(recorded_at, 'YYYY-MM-DD"T"HH24:MI:SS.USOF')
`

const currentVersionQuery = `SELECT COALESCE(MAX(version), -1) FROM events WHERE stream_id = $1`

const headQuery = `SELECT COALESCE(MAX(global_position), 0) FROM events`

const insertTag = `
  INSERT INTO event_tags (tag, global_position) VALUES ($1, $2)
  ON CONFLICT DO NOTHING
`

const deleteTags = `DELETE FROM event_tags`

const unindexedEvents = `SELECT ` + eventColumns + `
  FROM events
  WHERE global_position >= $1
    AND NOT EXISTS (SELECT 1 FROM event_tags WHERE global_position = events.global_position)
  ORDER BY global_position ASC
  LIMIT $2
`

// readAllBatchSize keeps a rebuild over a long log from materialising the whole thing in memory.
const readAllBatchSize = 500

// Store is a Postgres-backed events.Store.
//
// It takes a pool rather than a connection, and that is load-bearing: two simultaneous appends
// need two connections to genuinely race, which is what makes the concurrency guarantee
// observable at all.
type Store struct {
	pool   *pgxpool.Pool
	tagsOf events.TagsOf
}

// New binds the adapter to a pool, tagging events by their own stream. Opening the pool belongs to
// the composition root, which is the only place allowed to read configuration.
func New(pool *pgxpool.Pool) *Store {
	return NewTagged(pool, events.DefaultTagsOf)
}

// NewTagged is New with this project's own tagging function — what its events are findable by
// beyond their stream.
func NewTagged(pool *pgxpool.Pool, tagsOf events.TagsOf) *Store {
	return &Store{pool: pool, tagsOf: tagsOf}
}

// Executor is somewhere to run SQL: the pool, or the transaction a unit of work opened. Both
// pgxpool.Pool and pgx.Tx satisfy it.
//
// Exported because the checkpoint adapter is built from this store and has to run its statements
// on whatever this store's current transaction is — a second connection would be a second
// transaction, and a checkpoint in its own transaction is a race with a number in it.
type Executor interface {
	Exec(ctx context.Context, sql string, args ...any) (pgconn.CommandTag, error)
	Query(ctx context.Context, sql string, args ...any) (pgx.Rows, error)
	QueryRow(ctx context.Context, sql string, args ...any) pgx.Row
}

type unitOfWorkKey struct{}

// Executor returns the transaction this context is inside, or the pool when it is inside none.
func (s *Store) Executor(ctx context.Context) Executor {
	if open, ok := ctx.Value(unitOfWorkKey{}).(pgx.Tx); ok {
		return open
	}
	return s.pool
}

// InUnitOfWork runs work in one transaction, which an append and somebody else's write share.
//
// The transaction travels in the context work is given, rather than in this Store, because two
// appends on one store do run concurrently — the integration suite races eight of them — and a
// field would have the second one's statements land inside the first one's transaction.
//
// Nesting uses pgx's own nested transaction, which is a SAVEPOINT: an inner block that fails has to
// undo its own writes and no more. In Postgres it also has to, and not merely ought to — a failed
// statement poisons the whole transaction until something rolls back to a savepoint, so without
// this an inner failure would take the outer commit with it.
func (s *Store) InUnitOfWork(ctx context.Context, work func(context.Context) error) error {
	return s.inUnitOfWork(ctx, pgx.TxOptions{}, work)
}

func (s *Store) inUnitOfWork(
	ctx context.Context,
	options pgx.TxOptions,
	work func(context.Context) error,
) error {
	if open, ok := ctx.Value(unitOfWorkKey{}).(pgx.Tx); ok {
		nested, err := open.Begin(ctx)
		if err != nil {
			return fmt.Errorf("open a savepoint: %w", err)
		}
		if err := work(context.WithValue(ctx, unitOfWorkKey{}, nested)); err != nil {
			_ = nested.Rollback(ctx)
			return err
		}
		if err := nested.Commit(ctx); err != nil {
			return fmt.Errorf("release a savepoint: %w", err)
		}
		return nil
	}

	// One connection for the whole unit of work. Reaching back into the pool from inside it is
	// what deadlocks under contention: every in-flight caller would hold one connection and wait
	// for a second.
	connection, err := s.pool.Acquire(ctx)
	if err != nil {
		return fmt.Errorf("acquire connection: %w", err)
	}
	defer connection.Release()

	transaction, err := connection.BeginTx(ctx, options)
	if err != nil {
		return fmt.Errorf("begin a unit of work: %w", err)
	}
	if err := work(context.WithValue(ctx, unitOfWorkKey{}, transaction)); err != nil {
		_ = transaction.Rollback(ctx)
		return err
	}
	if err := transaction.Commit(ctx); err != nil {
		return fmt.Errorf("commit a unit of work: %w", err)
	}
	return nil
}

func (s *Store) currentVersion(ctx context.Context, streamID string) (int, error) {
	var version int
	row := s.Executor(ctx).QueryRow(ctx, currentVersionQuery, streamID)
	if err := row.Scan(&version); err != nil {
		return 0, fmt.Errorf("read current version of %s: %w", streamID, err)
	}
	return version, nil
}

// eventsLock is the log's own advisory lock, which is how a reader learns that a position is
// settled.
//
// A global position is assigned when a row is inserted and becomes visible when its transaction
// commits, and those are not the same moment: two appends overlapping can take 5 and 6 and commit 6
// first. A reader that sees 6 and records "next is 7" has skipped 5 for good, because 5 arrives
// behind a checkpoint that has already passed it. Nothing in the log is wrong afterwards, and the
// view is missing a row nothing will ever put back.
//
// So an append takes this lock in shared mode before its first insert, which costs nothing because
// shared holders do not block each other, and ReadAll takes it exclusively for one
// MAX(global_position) query. Acquiring it exclusively means no append is between its insert and its
// commit, so every position at or below that maximum is final: committed and visible, or aborted and
// gone for good. Reading no further than that is what makes a single number a safe place for a
// projection to resume from.
//
// The number is arbitrary and only has to be the same in every adapter that opens this log. It must
// not be reused for anything else in the same database, which is why it lives here.
const eventsLock = 8317231

// lockShared takes the log's lock in shared mode, so appends never block each other.
const lockShared = `SELECT pg_advisory_xact_lock_shared($1)`

// lockExclusive takes it exclusively, which waits for every append in flight to finish.
const lockExclusive = `SELECT pg_advisory_xact_lock($1)`

// holdTheLog holds the log in shared mode until this transaction ends — see eventsLock.
//
// Before the first insert, always, and re-entrant: taking it twice in one transaction is free.
// Shared, so two appends never wait for each other; what waits is a reader asking whether a position
// has settled.
func (s *Store) holdTheLog(ctx context.Context) error {
	if _, err := s.Executor(ctx).Exec(ctx, lockShared, eventsLock); err != nil {
		return fmt.Errorf("hold the log: %w", err)
	}
	return nil
}

// settledPosition is the highest position nothing earlier can still be committed behind.
//
// Its own transaction, so the exclusive hold lasts microseconds: long enough to prove nothing is in
// flight, short enough that the appends queueing behind it barely notice. Two statements rather than
// one, because the order in which Postgres evaluates a lock function beside an aggregate is not
// something to rely on.
func (s *Store) settledPosition(ctx context.Context) (int64, error) {
	var settled int64
	err := s.InUnitOfWork(ctx, func(inside context.Context) error {
		if _, err := s.Executor(inside).Exec(inside, lockExclusive, eventsLock); err != nil {
			return fmt.Errorf("wait for the log to settle: %w", err)
		}
		var err error
		settled, err = s.head(inside)
		return err
	})
	return settled, err
}

func (s *Store) head(ctx context.Context) (int64, error) {
	var head int64
	if err := s.Executor(ctx).QueryRow(ctx, headQuery).Scan(&head); err != nil {
		return 0, fmt.Errorf("read the store head: %w", err)
	}
	return head, nil
}

func (s *Store) Read(ctx context.Context, streamID string) ([]events.CommittedEvent, error) {
	query := `SELECT ` + eventColumns + ` FROM events WHERE stream_id = $1 ORDER BY version ASC`
	rows, err := s.Executor(ctx).Query(ctx, query, streamID)
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
		if err := s.holdTheLog(inside); err != nil {
			return err
		}
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

	var pgErr *pgconn.PgError
	switch {
	case errors.Is(err, errStale),
		errors.As(err, &pgErr) && pgErr.Code == uniqueViolation:
		// A conflict is a value rather than an error, because contention is expected under load,
		// not exceptional. The guard catches a stale expectation; the unique constraint catches
		// the true race, where two transactions both passed the guard.
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
// into conflict values immediately outside it. Returning nil from inside would commit the
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
	var position int64
	err = executor.QueryRow(ctx, insertGuarded,
		streamID, version, event.Type, event.SchemaVersion, payload, actor,
		string(event.CorrelationID), nullable(string(event.CausationID)), event.OccurredAt,
		guardAgainst,
	).Scan(&position)
	if errors.Is(err, pgx.ErrNoRows) {
		// The guard failed: the stream is not where the caller thought it was.
		return errStale
	}
	if err != nil {
		return err
	}
	event.StreamID = streamID
	for _, tag := range s.tagsOf(event) {
		if _, err := executor.Exec(ctx, insertTag, tag, position); err != nil {
			return err
		}
	}
	return nil
}

// tagQuerySQL is a TagQuery as a SQL predicate over `e`, plus its arguments, numbered from next.
//
// TagFilter.Matches in the port is the definition; this is its translation, and the contract suite
// is what holds the two to each other. Every SQL adapter carries its own copy of this translation,
// in whatever placeholder syntax its driver wants, deliberately duplicated rather than shared: an
// adapter that imports another adapter is two adapters that cannot be pruned apart.
//
//   - a filter's tags are a conjunction — the number of its tags found against the event must equal
//     how many it named, because = ANY on its own is an "any of" and a much weaker guard than the
//     caller asked for;
//   - its types narrow within that filter only;
//   - a filter naming neither, and a query with no filters at all, match nothing: `1 = 0` rather
//     than a missing predicate, because an absent guard matches everything and a conditional
//     append that matched everything would refuse every write in the system.
func tagQuerySQL(query events.TagQuery, next int) (string, []any) {
	if len(query.Filters) == 0 {
		return "1 = 0", nil
	}
	var (
		predicates []string
		arguments  []any
	)
	placeholder := func(value any) string {
		arguments = append(arguments, value)
		return fmt.Sprintf("$%d", next+len(arguments)-1)
	}
	for _, filter := range query.Filters {
		if len(filter.Tags) == 0 && len(filter.Types) == 0 {
			predicates = append(predicates, "1 = 0")
			continue
		}
		var parts []string
		if len(filter.Tags) > 0 {
			tagsAt := placeholder(filter.Tags)
			countAt := placeholder(len(distinct(filter.Tags)))
			parts = append(parts, `(SELECT COUNT(*) FROM event_tags t`+
				` WHERE t.global_position = e.global_position`+
				` AND t.tag = ANY(`+tagsAt+`)) = `+countAt)
		}
		if len(filter.Types) > 0 {
			parts = append(parts, `e.event_type = ANY(`+placeholder(filter.Types)+`)`)
		}
		predicates = append(predicates, "("+strings.Join(parts, " AND ")+")")
	}
	return "(" + strings.Join(predicates, " OR ") + ")", arguments
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

// Head is the last settled position, which is the only kind a decision may be guarded at.
//
// The same protocol ReadAll uses, and for a reason that took a reproduction to see: a boundary past
// an event still in flight is a boundary the guard cannot check. Two appends take 5 and 6, 6 commits
// first, a decision reads a head of 6 while 5 is invisible — and AppendIf then looks for anything
// matching *after* 6 and never sees 5, because 5 sits below its own boundary. The append is allowed
// and the constraint it was meant to hold is broken, with a correct-looking log to show for it.
//
// Waiting for the appends in flight fixes it twice over: the boundary is one nothing can arrive
// behind, and the read that follows sees the very events the decision has to know about.
//
// Inside a unit of work, the answer is that transaction's own view instead — a caller reading its own
// writes rather than drawing a boundary, which is what an inline read model does. Asking for the
// settled position there would wait on a lock the transaction is itself holding.
func (s *Store) Head(ctx context.Context) (int64, error) {
	if _, inside := ctx.Value(unitOfWorkKey{}).(pgx.Tx); inside {
		return s.head(ctx)
	}
	return s.settledPosition(ctx)
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
	predicate, arguments := tagQuerySQL(query, 3)
	statement := `SELECT ` + eventColumns + ` FROM events e` +
		` WHERE e.global_position > $1 AND e.global_position <= $2 AND ` + predicate +
		` ORDER BY e.global_position ASC`
	rows, err := s.Executor(ctx).Query(ctx, statement, append([]any{after, ceiling}, arguments...)...)
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
	return s.Head(ctx)
}

func (s *Store) anythingMatching(ctx context.Context, condition events.Condition) (bool, error) {
	predicate, arguments := tagQuerySQL(condition.Query, 2)
	statement := `SELECT 1 FROM events e WHERE e.global_position > $1 AND ` + predicate + ` LIMIT 1`
	rows, err := s.Executor(ctx).Query(
		ctx, statement, append([]any{condition.After}, arguments...)...,
	)
	if err != nil {
		return false, fmt.Errorf("check a condition: %w", err)
	}
	defer rows.Close()
	return rows.Next(), rows.Err()
}

// AppendIf appends only if nothing matching the condition arrived since the caller read.
//
// SERIALIZABLE, not a clever WHERE NOT EXISTS: the guard is the absence of rows, and absence is
// what no lock in a row-locking database can hold. Postgres detects the conflict at commit and
// raises a serialisation failure, which is reported here as a conflict — because for the caller it
// is the same fact and the same next move, re-read and re-decide.
//
// A conditional append inside somebody else's unit of work runs at that transaction's isolation
// level, because an isolation level can only be set as a transaction opens.
func (s *Store) AppendIf(
	ctx context.Context,
	condition events.Condition,
	batch []events.DomainEvent,
) (events.ConditionalAppendResult, error) {
	err := s.inUnitOfWork(ctx, pgx.TxOptions{IsoLevel: pgx.Serializable}, func(inside context.Context) error {
		if err := s.holdTheLog(inside); err != nil {
			return err
		}
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
	var pgErr *pgconn.PgError
	switch {
	case errors.Is(err, errConditionBroken),
		errors.As(err, &pgErr) && pgErr.Code == serializationFailure:
		return events.ConditionConflict(head), nil
	case err != nil:
		return events.ConditionalAppendResult{}, fmt.Errorf("conditional append: %w", err)
	}
	return events.Recorded(head), nil
}

// ReindexTags indexes what this store's tagging function has not indexed yet, a batch at a time.
//
// Resumable on purpose: a project adopting tags runs this over a log that may be very long, and a
// run that dies halfway is continued by running it again rather than started over.
func (s *Store) ReindexTags(ctx context.Context, fromPosition int64) (int, error) {
	indexed := 0
	position := fromPosition
	for {
		done := false
		err := s.InUnitOfWork(ctx, func(inside context.Context) error {
			rows, err := s.Executor(inside).Query(inside, unindexedEvents, position, readAllBatchSize)
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

			if len(unindexed) == 0 {
				done = true
				return nil
			}
			executor := s.Executor(inside)
			for _, event := range unindexed {
				tags := s.tagsOf(event.DomainEvent)
				if len(tags) == 0 {
					// Counted only when it made the event findable. An event with no tags is re-read
					// by every later run, which is a scan and not a rewrite, and the alternative is a
					// count that never reaches zero.
					continue
				}
				for _, tag := range tags {
					if _, err := executor.Exec(inside, insertTag, tag, event.GlobalPosition); err != nil {
						return err
					}
				}
				indexed++
			}
			position = unindexed[len(unindexed)-1].GlobalPosition + 1
			return nil
		})
		if err != nil {
			return indexed, fmt.Errorf("reindex tags: %w", err)
		}
		if done {
			return indexed, nil
		}
	}
}

func (s *Store) Retag(ctx context.Context, tagsOf events.TagsOf) (int, error) {
	indexed := 0
	err := s.InUnitOfWork(ctx, func(inside context.Context) error {
		s.tagsOf = tagsOf
		if _, err := s.Executor(inside).Exec(inside, deleteTags); err != nil {
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

func (s *Store) ReadAll(
	ctx context.Context,
	fromPosition int64,
	visit func(events.CommittedEvent) error,
) error {
	query := `SELECT ` + eventColumns + `
	  FROM events WHERE global_position >= $1 AND global_position <= $2
	  ORDER BY global_position ASC LIMIT $3`
	// The ceiling is taken once, at the start: an event appended while a long replay is running
	// belongs to the next pass, and a checkpoint that stopped short of it loses nothing.
	settled, err := s.settledPosition(ctx)
	if err != nil {
		return err
	}
	position := fromPosition
	for position <= settled {
		rows, err := s.Executor(ctx).Query(ctx, query, position, settled, readAllBatchSize)
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
	return nil
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

// scanEvent parses a stored row back into a CommittedEvent.
//
// Events are validated on read as well as on write, because stored events outlive the code that
// wrote them. A tolerant reader on purpose: unknown payload fields written by a newer version
// are carried through rather than rejected, which is what makes a rolling deploy possible. Only
// the envelope itself is required — and its ids are parsed as UUIDs here rather than passed
// through as text, so a row written by something that was not this adapter cannot enter the
// domain as an identifier nothing can correlate.
func scanEvent(row pgx.Rows) (events.CommittedEvent, error) {
	var (
		event         events.CommittedEvent
		payload       []byte
		actor         []byte
		correlationID string
		causationID   *string
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
	if err := json.Unmarshal(payload, &event.Payload); err != nil {
		return events.CommittedEvent{}, fmt.Errorf(
			"event at global_position %d has an unreadable payload: %w", event.GlobalPosition, err)
	}
	var decoded map[string]string
	if err := json.Unmarshal(actor, &decoded); err != nil || decoded["kind"] == "" {
		return events.CommittedEvent{}, fmt.Errorf(
			"event at global_position %d has no usable actor", event.GlobalPosition)
	}
	event.Actor = events.Actor{Kind: decoded["kind"], ID: decoded["id"]}
	event.CorrelationID, err = events.NewCorrelationID(correlationID)
	if err != nil {
		return events.CommittedEvent{}, fmt.Errorf(
			"event at global_position %d: %w", event.GlobalPosition, err)
	}
	if causationID != nil {
		event.CausationID, err = events.NewCausationID(*causationID)
		if err != nil {
			return events.CommittedEvent{}, fmt.Errorf(
				"event at global_position %d: %w", event.GlobalPosition, err)
		}
	}
	return event, nil
}
