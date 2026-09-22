---
name: web-interface-guidelines
description: Review browser UI code against Vercel's Web Interface Guidelines — accessibility, focus, forms, motion, typography, content handling, performance, navigation state, touch, dark mode, locale and hydration — before a screen is demonstrated. Use when a slice adds or changes anything rendered in a browser, when asked to review or audit UI code, or before the demo stop of a slice with a screen. The rules are pinned in this skill; nothing is fetched.
capabilities: frontend
---

# Web Interface Guidelines

A review, not a style: the rules a screen is checked against once it is written, so that what reaches the
demo has a label on every control, a focus ring on every interactive element, an `…` on every loading
state, and none of the anti-patterns that read as unfinished before anybody has used the thing.

The rules are [`references/guidelines.md`](references/guidelines.md) — Vercel's Web Interface Guidelines,
pinned at a commit rather than fetched, because this repository is opened in sandboxes and CI runners
without network and a review that silently fell back to memory would be worse than none. Read that file in
full before the first review in a session; it is short.

## When to run it

- **Before the demo stop of any slice with a screen.** The demo stop already asks whether every screen the
  slice adds or changes is styled; this is the second half of that check, and its findings are recorded
  with the others.
- **When asked to review or audit UI code**, or when `frontend-design` has just produced a screen and the
  build is about to be called done.
- **Not for a screen that does not exist yet.** `frontend-design` is the skill for deciding what to build;
  this one checks what was built.

## How

1. Take the files the slice added or changed under the browser app — components, routes, stylesheets —
   and only those. A review of the whole app is a different job and is not what the demo stop asks for.
2. Read each file against every section of the rules. Do not skip a section because it looks
   inapplicable: the forms section applies to a search box, the locale section to a rendered date.
3. Where the rules and this repository's own design page disagree, `docs/design.md` wins and the finding
   is not raised. The rules are a floor; the page is a decision. The known disagreement is heading case:
   the rules say Title Case, the design page and `frontend-design` say sentence case, and sentence case is
   this repository's.
4. Report in the rules' own output format — grouped by file, `file:line`, one terse finding per line, a
   `✓ pass` for a clean file — and fix what was found before the demo rather than carrying it as a note.

## Where it lands

`docs/design.md` names this review in *Rules a slice follows*, and the demo stop names it in its styled
check. A finding that cannot be fixed in the slice is written into the slice's plan as a stub, in the
actor's vocabulary, so it appears under *Not working yet* on the board rather than being discovered.

Provenance and the exact upstream pin are in [`references/source-notes.md`](references/source-notes.md);
the upstream MIT notice is `LICENSE`.
