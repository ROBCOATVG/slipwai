# The canonical toolkit

Everything a generated project receives lives here. No starter copy is committed anywhere, so a change in
this tree reaches every combination the moment it is generated.

| Directory | Holds |
|---|---|
| `toolkit/skills/` | The shared delivery and event skills, canonical in their event-modelling form |
| `toolkit/docs/` | Shared methodology documentation: event modeling to code, and the first slice |
| `toolkit/scripts/` | The dependency-free gate scripts a generated repository ships |
| `profiles/standard/` | The rewritten overlays, and the preset, that derive the standard profile |
| `profiles/event-modelling/` | Additions specific to the event profile |
| `languages/<language>/app/` | Each backend's walking skeleton, laid out at the paths it lands on under the service's directory. That is `apps/service/` by default |
| `languages/java/build/` | The Maven wrapper and the analyser configuration that both Java backends share |
| `languages/<language>/event-port/` | The event-store port with no adapter behind it, for a backend whose event-store axis offers nothing yet. Every backend offers the axis today, so this is emitted for none of them. It is kept for the next language, on the day it lands before its stores do |
| `languages/<language>/locks/`, `go/modules/` | Committed dependency locks, one per dependency set the axes can produce |
| `languages/<language>/examples/` | The snippet a `{{example: skill/id}}` marker resolves to, per language. A project written in several languages gets one labelled block per language at each marker |
| `frontends/<frontend>/` | Frontend packs. Currently `react-vite`: the `app/` skeleton, the `features/<feature>/` directories copied into every browser app when a service has that feature (the customer login), and `locks/` per dependency set |
| `backing-services/` | Axis implementations: the event-store, HTTP, staff-identity and customer-identity adapters per backend, the shared `sql/` event-log schema, the Keycloak realms under `keycloak/realms/`, the Compose file, and the pruner shared with generated projects |

The toolkit is canonical in its event-modelling form. That is why `profiles/standard/` is the only profile
directory with rewritten overlays.

## Editing it

Edit the material in place, then run `make verify` from the factory root.

There is no import step and no synchronisation step, and no remote source repository: the factory is
self-contained. Spec Kit itself is not vendored — each generated project's `./init` installs it.

**A generated file's body belongs in this tree, never as a string in the generator.** The `app/` trees here
and under `frontends/` are read as trees. So adding a file to a starter is an edit in this directory and
nothing else.

Code decides content only where the *selection* does: a marked region, a per-feature dependency list, or a
name derived from the project. `tests/test_language_skeletons.py` fails a language module that stops reading
its tree.

Routing and the generated adaptations live in `src/slipwai/`. There is one module per part of the repository
being generated, so the file to open is named after the file you are changing.

See [docs/maintaining.md](../docs/maintaining.md) for the verification and browsing workflow, and
[docs/axes.md](../docs/axes.md) for what each axis answer is expected to deliver.
