MINOR

**A standard project has a database: the standard profile asks `persistence` like the modelled one, and defaults
to Postgres.** A standard service was already on the state rung, the one that keeps current state, and every
language answers that rung with a repository port and memory, SQLite and PostgreSQL adapters — but the axis was
the modelled profile's alone, so a standard project could not have a store at all, and `--persistence postgres`
with `--profile standard` was refused. It is asked now, with Postgres preselected; `make verify` still needs no
Docker. And a quickstart answer for an axis your chosen profile does not ask is left out and said, rather than
ending the run on a refusal of a question nobody was asked.

**Catch-up:** nothing for an existing project: `migrate` replays the answers `project.json` recorded, and a
standard service recorded without one stays storeless. `/add-service` or a new project gets the question.
