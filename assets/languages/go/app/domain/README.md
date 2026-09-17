# The domain layer

The model and nothing else: the types, the domain event shapes, and the decision functions that turn a
command and a fold of past events into new events or a refusal. This is the part of the service that
survives replacing the transport, the store and the framework, so it is the part that names none of them.

This directory ships with no package in it because the model is yours to write; the layer exists from day
one so that the first thing written into it lands in the right place and the gate already guards it. Add
`domain/<thing>/<thing>.go` and the package is a package.

**What belongs here.** Plain structs, plain functions, and their `*_test.go` files. No I/O, no `time.Now`,
no `rand`: a decision that needs the time or an id takes it as an argument, which is what lets its test be
a table of inputs and expected events.

**What it may not import**, enforced by `make check-imports`:

- anything under `adapters/`, `infrastructure/` or `delivery/` — those import the domain, never the
  reverse.

Keeping drivers and frameworks out (`database/sql`, `net/http`, `github.com/jackc/...`) is the house rule
the review holds you to; the import gate checks the layer direction, not the package list, for Go.

The port interfaces a decision is driven through live under `../application/ports/`.
