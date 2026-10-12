<!-- section: event-sourced -->
## `{{path}}` — the log is the truth

This service answers `write-model: events`: current state is a fold of what happened, and a write is an
append made at an expected version of a stream.

| Model element | Code responsibility | Initial location |
|---|---|---|
| `ui` | actor-facing surface plus driving adapter | application-specific surface under `{{path}}` |
| `cmd` | typed intent and application use case | `{{usecase}}` |
| `evt` | immutable, versioned fact, appended to its stream | `{{events}}` |
| the decision | a Decider: `evolve` folds the stream into state, `decide` returns new events or an explicit rejection | `{{domain}}` |
| `rmo` | pure fold, plus the store its slice's `materialisation` names | application module, plus a driven adapter for anything but `live` |
| `pcr` | processor that reads, decides, and issues a command | `{{usecase}}` |
| `stream` | aggregate identity and optimistic-concurrency boundary | domain identity plus the event-store port |
| `guard` | the other boundary: a tag query and the position it was read at, which `appendIf` is refused by | the project's tagging function, plus the conditional append at the use case |
| `evt`'s `attributes` | the payload's fields; the ones marked `identifies:` become the event's tags | the event, plus the tagging function the store is built with |

Keep decision logic pure: rehydrate state by folding events, decide from state plus a command, and return
new events or an explicit rejection. The application layer loads history, invokes the decision, and appends
with an expected version. Infrastructure implements ports; it does not enter domain code.

A read model is a pure fold in all three cases, and `materialisation` on the slice says what maintains it:
`live` folds it per query and stores nothing, `inline` writes it in the append's own transaction, `async`
maintains it from a catch-up subscription whose checkpoint advances in the same transaction as the view.
`make check-model` requires the field from `planned` for the same reason it requires a guard — the event
store ships with `read`, `append` and a replay from position zero and nothing else, so a per-query fold is
the only read path that is already there, and a slice never asked ships with every query paying for the
whole log. A `live` view names `liveBudget` too: the ceiling one query may fold, and why that ceiling holds
in terms of the stream's own lifetime.
<!-- end section -->
<!-- section: state-stored -->
## `{{path}}` — current state is the truth

This service answers `write-model: state`: it keeps the current state of what it owns, and the events the
model names are contracts raised once a write has committed and never replayed.

| Model element | Code responsibility | Initial location |
|---|---|---|
| `ui` | actor-facing surface plus driving adapter | application-specific surface under `{{path}}` |
| `cmd` | typed intent and application use case | `{{usecase}}` |
| `evt` | immutable, versioned fact, raised by the use case once the write has committed. **Modelled always, published only where something reads it** — another service's `reads`, or an `async` read model | `{{events}}` |
| the decision | a load through the repository port, a pure decide over current state, and a save at the version that was read | `{{domain}}`, loading and saving through `{{repository}}` |
| `rmo` | pure fold, plus the store its slice's `materialisation` names | application module, plus a driven adapter for anything but `live` |
| `pcr` | processor that reads, decides, and issues a command — here a call the use case makes, not a subscription: there is no stream to subscribe to, so two slices in this service are linked by the processor itself | `{{usecase}}` |
| `stream` | the row or aggregate one transaction locks, and the version it is saved at | domain identity plus `{{repository}}` |
| `guard` | refused on this rung by name: a tag query reads a log, and this service keeps none | — |
| `folds` | refused for the same reason — there is no history here to fold | — |
| `evt`'s `attributes` | the payload's fields; the ones marked `identifies:` name what the fact is about | the event the use case raises |

Keep decision logic pure: load current state through the repository port, decide from that state plus a
command, and return the new state together with the events the slice says the write raises. The application
layer saves at the version it read — a save at a version somebody else has already moved past is the
rejection, and it is the whole of the concurrency control here — and raises the events after the save
commits. Infrastructure implements ports; it does not enter domain code.

Nothing in this service is rebuilt from its past, and that is the trade this rung makes: a write is one row
and one version, and how that row came to hold what it holds is not recorded. So an event raised here is
true from the moment it is raised and claims nothing about what came before it — never write one that
asserts a fact the service did not observe at the time.

A read model is a pure fold in all three cases, and `materialisation` on the slice says what maintains it:
`live` is a query over the write tables themselves, `inline` is written in the write's own transaction, and
`async` is maintained from the outbox the raised events are published through. `make check-model` requires
the field from `planned`, and asks no `liveBudget` on this rung — a `live` view reads current state rather
than folding a log, so there is no ceiling of events for it to name.

**An event here is on the timeline because it is how the slice was found, and that is reason enough for it
to exist.** It needs a publisher only where there is a subscriber: a `reads` from another service, or an
`async` read model. Until then the use case raises it in process, and what happens next in this service is
a call the use case makes — the `pcr` row above. An outbox built for nobody is the machinery this rung
exists to avoid, and the first cross-service reader is what makes it required rather than optional. Where
this project already publishes somehow — an outbox, a bus, change data capture — that is the mechanism to
use, recorded as the decision it is rather than joined by a second one.
<!-- end section -->
