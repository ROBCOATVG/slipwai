-- Append-only enforcement for the event log. Events are immutable facts; a store that permits an UPDATE
-- permits rewriting history, and every projection built from that log becomes unreproducible.
--
-- REVOKE alone does not achieve this here: the application role OWNS the table, and in Postgres a table
-- owner retains its privileges regardless of REVOKE. A statement-level trigger refuses the operation
-- whatever the role, so the guarantee holds for this single-role local setup and for a production setup
-- with a separate owner. REVOKE is issued as well, so it still holds once ownership is separated.
--
-- DROP TABLE is deliberately still permitted — migrations and test teardown need it, and a schema change
-- is a reviewed event, not a silent row rewrite.
CREATE OR REPLACE FUNCTION events_reject_mutation() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'events is append-only: % is not permitted on this table', TG_OP
    USING ERRCODE = 'insufficient_privilege';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER events_no_update
  BEFORE UPDATE ON events
  EXECUTE FUNCTION events_reject_mutation();

CREATE TRIGGER events_no_delete
  BEFORE DELETE ON events
  EXECUTE FUNCTION events_reject_mutation();

CREATE TRIGGER events_no_truncate
  BEFORE TRUNCATE ON events
  EXECUTE FUNCTION events_reject_mutation();

REVOKE UPDATE, DELETE, TRUNCATE ON events FROM PUBLIC;
