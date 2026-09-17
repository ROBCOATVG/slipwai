"""The document that says what each box on the model becomes in a file.

Its own module because it is most of the bytes and none of the behaviour: `event_model.py` computes the
per-backend paths and this renders them, which is the same split `service_layouts.py` is on the other side
of. One page, generated per project, because the paths in it are the project's own.
"""
from __future__ import annotations


def model_to_code(backend: str, service: str, paths: dict[str, str]) -> str:
    """`docs/event-modeling-to-code.md`, with this project's backend and its first service's paths."""
    return f"""# From event model to code

The model describes behavior; the `{backend}` services under `apps/` make it executable. The paths below
name the first service, `{service}`; a slice that belongs to another service lives under that service's
directory in the same shape. Which service that is, is the slice's `service` field in `model.yaml`, decided
against what each service says it owns — the `purpose` on its `project.json` entry, listed under *Bounded
contexts* in `docs/architecture.md`. With one service the field is optional; with two or more,
`make check-model` requires it, because a slice that names no owner lands in the first service by
gravity, not by decision. `<context>` in the paths is the slice's `context` where the service holds
several bounded contexts (its `contexts` in `project.json`; the gate requires the field then too), and the
service's one context otherwise. Names are illustrative—domain names come from modelling.

| Model element | Code responsibility | Initial location |
|---|---|---|
| `ui` | actor-facing surface plus driving adapter | application-specific surface under `{service}` |
| `cmd` | typed intent and application use case | `{paths['usecase']}` |
| `evt` | immutable, versioned fact | `{paths['events']}` |
| `rmo` | pure fold, plus the store its slice's `materialisation` names | application module, plus a driven adapter for anything but `live` |
| `pcr` | processor that reads, decides, and issues a command | `{paths['usecase']}` |
| `stream` | aggregate identity and optimistic-concurrency boundary | domain identity plus event-store port |
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

## Testing by responsibility

- Express agreed examples as observable tests using `{paths['test']}`.
- Test pure decision tables directly only for meaningful combinatorial rules.
- Run every port contract against both its fake and real adapter.
- Test driven integrations against realistic stubs for parsing, timeout, retry, and error translation.
- Test delivery adapters for parsing and outcome mapping; do not duplicate domain rules there.
- Keep Python tests on pytest, Go tests on `testing`, and TypeScript tests on Vitest—the repository gate
  already invokes the canonical stack.

Event names, payloads, stream identity, `reads`, `folds`, tests, and code paths change as one contract. Use
`/validate-code-against-model` to report drift rather than silently changing either side.
"""
