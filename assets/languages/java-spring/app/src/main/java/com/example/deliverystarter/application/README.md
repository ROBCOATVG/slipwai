# The application layer

What this service *does*, said once: the use cases — command handlers, query handlers, projection
definitions — and the ports they are driven through.

Ports go in `ports`, one package each. Where this project was given an event store, two are already
there: `ports.events`, the port every write goes through, and `ports.readmodels`, the checkpoint and
projection port the read side is maintained with. Classes under `..adapters.driven` implement a port;
classes under `..adapters.driving` call a use case. Neither is an import from here.

**What belongs here.** A use case that orchestrates: load what the decision needs through a port, call
the domain, append what it returned. A port is an interface named for what the application needs, never
for what implements it.

**What it may not import**, enforced by `make check-imports`:

- anything under `adapters.`, `composition.`, `infrastructure.` or `delivery.`. An adapter is injected,
  never reached for, and Spring's own context is the composition root that meets the two.

It may import the domain freely: that is the direction the whole rule exists to keep.
