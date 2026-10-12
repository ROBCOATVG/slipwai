# From event model to code

The model describes behavior; the services under `apps/` make it executable.
{{placing}}
`<context>` in the paths below is the slice's `context` where the service holds several bounded contexts
(its `contexts` in `project.json`; the gate requires the field then too), and the service's one context
otherwise. Names are illustrative—domain names come from modelling.

{{write-models}}
## Testing by responsibility

{{examples}}
- Test pure decision tables directly only for meaningful combinatorial rules.
- Run every port contract against both its fake and real adapter.
- Test driven integrations against realistic stubs for parsing, timeout, retry, and error translation.
- Test delivery adapters for parsing and outcome mapping; do not duplicate domain rules there.
- Keep Python tests on pytest, Go tests on `testing`, and TypeScript tests on Vitest—the repository gate
  already invokes the canonical stack.

Event names, payloads, the identity each write is made against, `reads`, tests, and code paths change as one
contract. Use `/validate-code-against-model` to report drift rather than silently changing either side.
