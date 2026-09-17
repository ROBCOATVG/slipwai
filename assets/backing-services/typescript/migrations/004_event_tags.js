/**
 * The tag index: what makes a Dynamic Consistency Boundary expressible over this log.
 *
 * A tag is a `kind:value` string — `stream:order-42`, `course:c1` — and an event carries as many as the
 * project's own tagging function returns for it. `stream:<streamId>` is what it returns by default, which
 * is the same sentence as "stream-per-aggregate is the case where every event carries exactly one tag".
 *
 * Three things about this table are deliberate, and each is a decision recorded in the factory's
 * `docs/adr/0001-a-dcb-capable-log.md`:
 *
 *   1. **It is derived, not authoritative.** The tags of an event are a function of the event, so this
 *      table can be emptied and rebuilt at any time — `retag` in the adapter does exactly that. Nothing
 *      here is a fact; the facts are all in `events`.
 *   2. **`events` is not altered.** No column is added to the log and no history is rewritten, which is
 *      what lets a project that is already in production adopt tags at all: 002 installs a trigger that
 *      refuses an UPDATE on `events`, so a tag column on the event row could never be backfilled. This
 *      table is filled by replaying the log — one INSERT per event, which the trigger has no opinion
 *      about.
 *   3. **It is written inside the append's transaction.** Never after it. An index that lags the log it
 *      indexes would let a conditional append miss the very event that should have refused it, which is
 *      the one failure that would make this feature worse than not having it.
 */
export const up = (pgm) => {
  pgm.sql(`
    CREATE TABLE event_tags (
      tag             TEXT   NOT NULL,
      -- The foreign key is what keeps the index honest: a tag row cannot name an event that does not
      -- exist, and because \`events\` refuses DELETE it cannot come to name one later either.
      global_position BIGINT NOT NULL REFERENCES events (global_position),
      PRIMARY KEY (tag, global_position)
    );

    -- The primary key answers "which events carry this tag", which is the read path. This index answers
    -- "which tags does this event carry", which is what a resumable reindex needs to know what it has
    -- already done.
    CREATE INDEX event_tags_global_position_idx ON event_tags (global_position);
  `);
};

export const down = (pgm) => {
  pgm.sql('DROP TABLE event_tags;');
};
