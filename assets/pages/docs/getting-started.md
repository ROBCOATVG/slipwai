# Getting started

`{{project-name}}` was scaffolded with the `{{profile}}` foundation, {{language}} backend services, and the `{{frontend}}` frontend.
Bootstrap Spec Kit interactively
with `./init`, or select an
integration explicitly, for example `./init --integration claude` or
`./init --integration cursor-agent`. All additional arguments pass through to
`specify init --here --force`.

{{first-slice}}{{browser-paths}} Run `make verify`
before and after each increment; it is the same gate CI runs.

Use `/sail` for the complete delivery loop and `/where-are-we` for the progress board at any point; both read
artifacts on disk rather than memory, so one resumes safely and the other changes nothing. See `commands/`, `skills/` and `agents/`.
`/cruise` runs the loop with nobody at the wheel — it decides product questions as the owner and runs each demo
as the actor, and stops only for a person; it ships switched off, and `commands/cruise.md` says how to start it.
<!-- section: event-contract -->

Before implementation, update `docs/event-model/model.yaml`; commands, events, stream identity, and schemas are one contract.
<!-- end section -->
<!-- section: standard-boundary -->

When ratifying a constitution, do not paste an Event Modeling or event-sourcing mandate into this
standard profile; `make check-speckit` checks that boundary. `make check-constitution` checks the
other direction — that minimum CD and the practices the skills teach are still in there.
<!-- end section -->
