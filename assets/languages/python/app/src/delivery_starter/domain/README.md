# The domain layer

The model and nothing else: entities, value objects, domain event shapes, and the decision functions
that turn a command and a fold of past events into new events or a refusal. This is the part of the
service that survives replacing the transport, the store and the framework, so it is the part that
names none of them.

This directory ships empty because the model is yours to write; the layer exists from day one so that
the first thing written into it lands in the right place and the gate already guards it.

**What belongs here.** Plain modules — dataclasses, enums, functions. No I/O, no clock, no randomness: a
decision that needs the time or an id takes it as an argument, which is what lets its test be a table of
inputs and expected events.

**What it may not import**, enforced by `make check-imports`:

- anything under `adapters/`, `infrastructure/` or `delivery/` — those import the domain, never the
  reverse.

Keeping frameworks and drivers out (`fastapi`, `psycopg`, `sqlite3`, `httpx`) is the house rule the
review holds you to; the import gate checks the layer direction, not the package list, for Python.

The port protocols a decision is driven through live one directory up, under `../application/ports/`.
