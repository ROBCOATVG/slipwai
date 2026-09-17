-- Where each projection has got to, and who is allowed to advance it.
--
-- Unlike `events`, this table is **mutable by design** — a checkpoint is a position that moves, so there is
-- no append-only trigger here and 002's rule does not extend to it. That is the whole distinction the read
-- side rests on: the log is the truth and cannot be rewritten, and everything derived from it can be thrown
-- away and rebuilt.
--
-- `position` is the next global position the projection has NOT applied, so a projection that has consumed
-- nothing is 0 and a rebuild is a write of 0 rather than a delete. It is advanced in the same transaction as
-- the rows it accounts for; a checkpoint committed on its own is a race with a number in it.
--
-- The lease columns are one row's worth of coordination rather than a table of their own: exactly one worker
-- should advance a projection, and the expiry is what makes that survive the worker dying. A lock nothing
-- releases is a projection that never advances again.
CREATE TABLE projection_checkpoints (
  projection        TEXT        PRIMARY KEY,
  position          BIGINT      NOT NULL DEFAULT 0,
  -- Both null when nobody holds the lease. They move together, always, which is why they are not two
  -- separately-defaulted columns.
  lease_owner       TEXT,
  lease_expires_at  TIMESTAMPTZ,
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT projection_checkpoints_position_non_negative CHECK (position >= 0),
  CONSTRAINT projection_checkpoints_lease_is_whole CHECK (
    (lease_owner IS NULL) = (lease_expires_at IS NULL)
  )
);
