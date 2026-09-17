# The skill catalogue

A generated project carries the delivery catalogue in `skills/`, owned by the project rather than referenced
from anywhere — and carries **the part of it this project can use**. The catalogue holds 49 skills; a project
gets the ones whose subject it has an answer for, plus the one written for it, so a TypeScript project with a
React frontend and a customer login gets 50 and a Python service with neither gets 41.

- [What is in it](#what-is-in-it)
- [A skill is withheld when its subject is not here](#a-skill-is-withheld-when-its-subject-is-not-here)
- [Examples come in your own languages](#examples-come-in-your-own-languages)
- [The one skill written for your project](#the-one-skill-written-for-your-project)
- [Where they come from, and where to edit them](#where-they-come-from-and-where-to-edit-them)

## What is in it

| Group | Skills |
|---|---|
| **Product and communication** | `specification`, `story-splitting`, `planning`, `expectations`, `acceptance-review`, `find-gaps`, `storyboard`, `diagrams`, `technical-writing`, `evaluate-existing-solutions`, `teach-me`, `wtf`, `double-check`, `find-skills` |
| **Testing** | `tdd`, `testing`, `test-design-reviewer`, `front-end-testing`, `react-testing`, `characterisation-tests`, `finding-seams`, `adversarial-testing`, `mutation-testing` |
| **Architecture and code** | `hexagonal-architecture`, `domain-driven-design`, `ubiquitous-language`, `codebase-design`, `structure-codebase`, `folder-structure`, `api-design`, `bff-design`, `bff-entry-points`, `functional`, `typescript-strict`, `twelve-factor`, `architecture-decisions`, `improve-codebase-architecture`, `reduce-system-complexity`, `refactoring`, `cli-design`, `observability`, `secure-oauth-oidc`, `production-parity-skill-builder` |
| **Event Modeling** *(event profile only)* | `event-modeling`, `event-sourcing`, `global-event-model` |
| **Working** | `debugging`, `ci-debugging`, `stack-pull-requests` |

They are active working guidance rather than reference material: each says when it applies, so an agent
reaches for `finding-seams` when a dependency is untestable and `characterisation-tests` when the code it is
about to change has no tests, without being told to.

Nine of them are about a capability rather than about how work is done, and a project gets each of those only
where it has the capability — the next section is which, and why.

## A skill is withheld when its subject is not here

A **capability** is what an answer gives a project, named for the thing rather than the answer that brought
it: `frontend`, `react`, `typescript`, `event-sourcing`, `auth-keycloak`. `catalog.json` declares them per
profile, per frontend and per axis option; `project.json` records them per deployable, and their union is
what the project can do.

A skill declares in its `SKILL.md` frontmatter which capabilities it serves, and one that declares none
serves every project — which is most of the catalogue, because most of it is about how work is done rather
than about a tool the project either has or has not:

```yaml
---
name: react-testing
description: React component testing patterns …
capabilities: react
---
```

A trailing `*` matches every capability beginning with it, so `secure-oauth-oidc` declares `auth-*, users-*`
and is earned by any identity provider on either axis. One match is enough.

| Skill | Serves | Words it is worth not shipping |
|---|---|---|
| `bff-entry-points` | `frontend` | 12,548 |
| `secure-oauth-oidc` | `auth-*`, `users-*` | 11,613 |
| `bff-design` | `frontend` | 8,585 |
| `front-end-testing` | `frontend` | 6,356 |
| `react-testing` | `react` | 2,341 |
| `typescript-strict` | `typescript` | 1,205 |
| `event-modeling`, `event-sourcing`, `global-event-model` | `event-modelling`, `event-sourcing` | — |

This is not the same question as which language a skill's examples are in. A language-shaped skill still
ships where its language is not the project's, with a pseudocode disclaimer, because the guidance is
language-independent even where the snippet is not. `typescript-strict` is the exception that proves it: in
a Go project it is not guidance in the wrong language, it is guidance about a language the project does not
use, and there is nothing for it to be about.

It is reversible in both directions. `slipwai add-frontend` and `slipwai add-service` regenerate the whole
project twice and write every file whose content the new application changes — which is how the browser
skills arrive with the browser app, without anything here listing them. `slipwai migrate` treats a skill the
project has since earned like any other generated file. And `make check-agents` names a skill that is still
here and no longer justified, so a project that drops its browser app is told.

Answering an axis again is the other direction, and it is the manifest that carries it: `./init --auth none`
prunes the adapter *and* rewrites each deployable's `selection` and `capabilities` in `project.json`, so the
project stops claiming `auth-keycloak` and `check-agents` names `secure-oauth-oidc` on the next run.

## Examples come in your own languages

A skill's code examples are rendered in the languages this project's services are actually written in. Where
a project holds several — a TypeScript service beside a Python one — each example appears as one labelled
block per language, at the same marker.

A skill whose examples have not been translated to any of this project's languages **says so under its
title** and ships anyway, stamped as pseudocode. Withholding it would be worse: the guidance is
language-independent even where the snippet is not.

## The one skill written for your project

Beyond the catalogue, every project gets a generated **`run-the-app`** skill describing its own run path —
which `make` target starts what, on which port, what the app serves before the first slice exists, and how
far to go before opening a browser. It is the answer to an agent's first question in an unfamiliar
repository, written from the project's own answers rather than guessed from its files.

## Where they come from, and where to edit them

`skills/` at the repository root is canonical. `./init` projects it into whichever agent harness you use —
`.cursor/skills/`, `.agents/skills/`, and so on — and `make check-agents` fails inside `make verify` when a
projection has drifted from the root. Edit the root copy and rerun `make agents`. The projections are not
committed: `.gitignore` lists every harness's directory, since a projection is the canonical file again with a
two-line stamp, and the whole catalogue copied into `.claude/skills/` was thirty thousand lines in every
repository, twice. A fresh clone has none until `./init` or `make agents` writes them, and `check-agents` says
so rather than failing; `slipwai migrate` re-derives them after every merge.

Nothing about them is factory-owned once generated: rename, rewrite or delete any of them as the project
grows its own opinions.

In the factory itself they live in `assets/toolkit/skills/`, canonical in their event-modelling form, with
per-language snippets under `assets/languages/<language>/examples/`. See
[The canonical toolkit](../assets/README.md).

Provenance and licensing for the material this catalogue draws on is recorded in the generated
`skills/REFERENCES.md`.
