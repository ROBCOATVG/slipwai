-- The event log. Append-only, and the (stream_id, version) unique constraint IS the optimistic
-- concurrency control — the store's third capability, and the one an in-memory fake cannot provide.
--
-- There is deliberately no down migration here. A file applied by migrations/apply.py is executed whole,
-- so a rollback kept in the same file would run in the same breath as the migration that created the
-- table. Reversing an event-log schema change is a reviewed operation, not a flag.
CREATE TABLE events (
  global_position BIGSERIAL PRIMARY KEY,
  stream_id       TEXT        NOT NULL,
  version         INTEGER     NOT NULL,
  event_type      TEXT        NOT NULL,
  schema_version  INTEGER     NOT NULL,
  payload         JSONB       NOT NULL,
  actor           JSONB       NOT NULL,
  -- Correlation and causation are UUIDs, and the column type says so. Postgres then rejects a
  -- malformed one at the door rather than storing it for a reader to trip over years later, and
  -- stores each in 16 bytes instead of 36 characters.
  correlation_id  UUID        NOT NULL,
  -- Nullable, because the first event of a business transaction has no cause to point at.
  causation_id    UUID,
  -- occurred_at is domain time, passed in as a typed input; recorded_at is storage time.
  -- Conflating them is how clock problems become unreconcilable.
  occurred_at     TIMESTAMPTZ NOT NULL,
  recorded_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT events_stream_version_unique UNIQUE (stream_id, version),
  CONSTRAINT events_version_non_negative CHECK (version >= 0)
);

CREATE INDEX events_stream_id_version_idx ON events (stream_id, version);
