---
description: Draft the constitution and the first specification from a product requirements document, then stop so a person can read it
argument-hint: [docs/prd.md]
---

# Draft

A project started from a PRD has its first specification drafted rather than typed: this reads the document,
ratifies the constitution from it and writes the first `specs/<feature>/spec.md` — and stops there, so that
what runs unattended afterwards (`/launch`, which charts and splits the feature and casts off) runs from a
specification a person has had in front of them. Nothing here builds anything.

**Typed by a person**, run `python3 scripts/agents/draft.py <document>` — `{{make}} draft`, or `PRD=<path>
{{make}} draft` for a document somewhere else — and repeat what it printed. The script starts one headless
session of the installed harness with this page as its rules and reports how it ended. The board runs the
same script after `./init` where a PRD was given when the project was generated.

**In a session that script dispatched** (`SLIPWAI_STAGE=draft` in the environment), this file is the rules:

1. **Read the document the argument names** — `docs/prd.md` where none was given — end to end, and
   `AGENTS.md`. Say in one line what the product is and who it is for, read off the document and nothing
   else.
2. **Ratify the constitution.** Run Spec Kit's constitution command as this harness projects it
   (`speckit.constitution`), exactly as written, with the document as the input a person would have typed.
   The principles are the ones the document states or plainly assumes; where it is silent, the template's own
   guidance stands. A principle the document does not support is not invented, and `{{make}}
   check-constitution` has to pass once the specification below exists.
3. **Write the first specification.** Run Spec Kit's specify command (`speckit.specify`) with the whole
   document as the feature description — the document, not a summary of it — so that every requirement and
   acceptance criterion it states is in `specs/<feature>/spec.md`. Where Spec Kit asks for a clarification,
   answer it from the document. Where the document does not answer, decide as the skipper protocol in
   `commands/cruise.md` decides — recommended first, and written down — and record each such decision in
   the specification under its own `## Assumptions` heading, so that a person reading the specification sees
   what was decided for them before anything is built on it.
4. **Run the gates the drafts answer to** — `{{make}} check-speckit` and `{{make}} check-constitution` — and
   fix what they refuse.
5. **Commit on the current branch**, as `Draft the constitution and the first specification from
   docs/prd.md`. Then say: the feature directory, how many requirements and criteria it holds, every
   assumption made, and that `/launch` — the board's **Continue the build** — is the next step. End the
   session. Do not chart, split, plan, mock up or implement: those are the launch's, after a person has read
   this.
6. **A further feature is not this command.** Hand it to `/sail`. That session captures it, asks whether
   it is a new feature, and assesses it. `{{make}} assess SLUG=<slug>` is the headless half, and it runs
   only after `docs/intake/<slug>/confirmed` exists.
