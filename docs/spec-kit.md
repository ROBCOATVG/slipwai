# Bootstrap Spec Kit in a generated repository

Spec Kit files are deliberately absent immediately after generation. From inside a generated repository,
run:

```sh
./init
```

That runs `specify init --here --force` and prompts for an agent integration. Select one explicitly when
automation or repeatability matters:

```sh
./init --integration claude
./init --integration codex --integration-options=--skills
./init --integration cursor-agent
```

Initialization first runs native Spec Kit setup, then projects the project-owned `skills/` and `commands/`
into the selected integration's native locations using the included Spec Kit-derived agent registry. Cursor
receives the full catalogue under `.cursor/skills/` alongside Spec Kit's own `speckit-*` skills; because
Cursor's current Spec Kit integration is skills-native, project commands such as `slice` become invocable
skills there too. Codex uses `.agents/skills/`; other integrations use their own registered locations and
command formats. The root directories remain canonical. Rerun `./init` after changing them to refresh the
projections, or with a different `--integration` to change harness. A rerun is local: in a project deploying
to AWS it finds the committed bootstrap state and leaves the account alone rather than running
`make bootstrap` again ([A path to production](aws-target.md)).

`./init` is also how a generated project answers an axis again — see
[Answering an axis again later](axes.md#answering-an-axis-again-later).

## How Spec Kit itself is obtained

If `specify` is installed, `./init` uses it. Otherwise it uses `uvx` (or `uv tool run`) to run the official
CLI from `github/spec-kit`. If neither is available, it installs the official CLI directly from the Spec Kit
GitHub repository into the ignored project-local `.specify-tools/` directory using Python and pip;
`python3-venv` is not required. Any extra arguments are passed directly to `specify init`.
Use `SPECIFY_SOURCE` for a pinned `uvx` source or `SPECIFY_PACKAGE` for a pinned Python requirement.

## The constitution is gated from both sides

Native Spec Kit treats the constitution prompt as product input; it cannot infer that pasted principles came
from a different foundation. In a `standard` project, keep the constitution architecture-neutral.
If it mandates an event-sourced core or event-store contract, use the `event-modelling` profile instead.
Generated `make verify`/`make check-speckit` detects that mismatch and explains the two valid resolutions.

The same file is checked from the other direction. `make check-constitution` fails when a ratified
`.specify/memory/constitution.md` stops carrying minimum CD ([minimumcd.org](https://minimumcd.org/minimumcd/),
restated in `assets/toolkit/scripts/check-constitution.py`), the practices the shipped skills teach —
strict typing, ubiquitous language and domain types, the hexagonal boundary, acceptance-driven testing,
observability, security, compatibility, ADRs, and a governance clause — or, where `project.json` claims the
event capabilities, the Event Modeling and event-sourcing obligations. `make constitution-requirements`
prints the normative text for whatever applies, and the generated `.specify/extensions.yml` hooks
`/speckit-constitution` on both sides so the drafting session sees that list before writing and the check
runs immediately after. A template is a starting position; this is the floor.

In a repository the method was installed around ([Adopt an existing repository](adopting.md#the-map),
experimental), the floor is a journey: the template is adapted to the convergence map, a principle the map says
is not yet reachable is written as a target under a `journey:` marker, and the gate holds the marker to the map
rather than asking for the principle in full until the rung is reached.

The floor is held from the moment drafting starts, not from `./init`. `specify init` installs the
constitution template — placeholders and all — as `.specify/memory/constitution.md`, and records the hash of
what it installed beside it in `.constitution-template.json`. While the file still hashes to that record
(or, for a Spec Kit that wrote none, still matches a template the repository carries), the gate prints
`nothing drafted yet` and passes: the commit `./init` pushes has to pass `verify`, because under a
production target that push is the first deploy, and a walking skeleton should not wait on a document
nobody has begun. One edited byte and the gate applies in full — a placeholder left behind then is a
constitution drafted and not ratified. It also applies, template or not, as soon as any feature exists under
`specs/`: a plan written against the template is a plan written against nothing, and the `/drive` ladder
sends the session back to the principles stage.
