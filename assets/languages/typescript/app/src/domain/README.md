# The domain layer

The model and nothing else: entities, value objects, domain event shapes, and the decision functions
that turn a command and a fold of past events into new events or a refusal. This is the part of the
service that survives replacing the transport, the store and the framework, so it is the part that
names none of them.

This directory ships empty because the model is yours to write; the layer exists from day one so that
the first thing written into it lands in the right place and the gate already guards it.

**What belongs here.** Pure `.ts` modules. No I/O, no clock, no randomness — a decision that needs the
time or an id takes it as an argument, which is what lets its test be a table of inputs and expected
events.

**What it may not import**, enforced by `make check-imports`:

- anything under `adapters/`, `infrastructure/` or `delivery/` — those import the domain, never the
  reverse;
- any Node built-in (`node:fs`, `node:crypto`, …), or any package other than `zod`. A schema library is
  not a framework, and domain event shapes are validated schema-first; everything else a decision needs
  is passed in.

The port interfaces a decision is driven through live one directory up, under `../application/ports/`.
