---
description: Assess one idea handed to /sail, and specify it only after a yes and a go
argument-hint: [slug]
---

# Assess

One idea already captured under `docs/intake/<slug>/`. This does not capture it — `/sail` did — and it does
not chart, split or implement. It decides whether the idea deserves a specification, and writes that
specification only when the decision is `go`.

**Typed by a person**, run `python3 scripts/agents/assess.py <slug>` — `{{make}} assess SLUG=<slug>`. The
script refuses a slug with no `brief.md`, and a slug with no `confirmed` file.

**In a session that script dispatched** (`SLIPWAI_STAGE=assess`), this file is the rules. The argument is
the slug:

1. Read `docs/intake/<slug>/brief.md` and every other file in that directory. Read `confirmed`: the first
   line is `yes` and the second is who answered. If `confirmed` is missing, stop and say that a person, or
   the skipper under `/cruise`, has to agree this is a new feature. Write nothing.
2. If `.specify/assessments/<slug>/decision.md` has no verdict yet, install the extension when the assess
   commands are missing (`specify extension add assess`) and run `/speckit-assess-intake`,
   `/speckit-assess-research`, `/speckit-assess-define`, `/speckit-assess-shape` and
   `/speckit-assess-decide` for this slug, with the brief as the idea. Leave the artifacts in
   `.specify/assessments/<slug>/`.
3. Read the verdict. `needs-clarification` and `kill` stop here. Say the verdict and the reason the
   decision gives. Do not specify.
4. A `go` runs `/speckit-specify` with the whole brief and the documents beside it — the documents, not a
   summary — then `/gaps`. Spec Kit specifies it on the profile `project.json` already names —
   `event-modelling` or `standard` — and on the one preset `.specify/presets/.registry` enables for it.
   Do not enable the other preset, do not change `project.json`, and do not scaffold again. Write
   `docs/intake/<slug>/specified.json` as `{"feature": "specs/...", "digest": "<sha256>"}`. The digest is
   sha256 over each file in that directory except `specified.json` and `confirmed`, sorted by relative
   path, each path, a NUL, the bytes, and a NUL. The feature is the directory Spec Kit created and recorded
   in `.specify/feature.json`.
5. Commit on the current branch as `Assess <slug>`. Say the verdict, and the feature directory when one
   was written. End the session.
