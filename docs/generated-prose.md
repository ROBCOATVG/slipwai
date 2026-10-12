# Generated prose: what may be an asset, and what may not

`src/slipwai/project/` writes every file a generated project receives. Just under half of it, by line, is
English inside string literals that are not docstrings. This page says which of that English may move out to
`assets/`, which must stay generated, and what to do with the paragraph that branches.

Measured on 2026-10-12, by `ast` over the tree rather than by eye: **94 modules, 14,566 lines, 6,996 of them
inside multi-line string literals that are not docstrings — 48%. Thirty-four modules are more than 60% prose
by line, and ten are at or over 300 lines against a 350-line budget.** The budget is a rule about code a
person has to hold in their head, and it is being spent on paragraphs: two modules reached it during a single
day's work in October 2026, and both were at the limit on English.

## The three kinds, and only one of them may leave

**1. Standing text — this moves.** The same words in every project, or the same words with a value
substituted. It becomes a `.md` under `assets/`, with `{{token}}` against a closed set.

**2. Text rendered from a declaration — this must not move.** The delegable-types table built from `STAGES`,
the axis tables from `catalog.json`, a service list from `project.json`. It is generated precisely so it
cannot drift from the declaration, and an asset that hand-wrote it would be a second answer to a question
the declaration already answers. The pilot drew this line first: a brief carries its `description` and is
refused if it writes `name`, `stage`, `writes` or `commands`, because those four are what a harness enforces.

**3. Text that branches — the rule is below.** On the profile, on the rung, on the backend, on the target.

## The branch: a section may move, a sentence may not

Two different things are both called conditional prose, and one `if` in `guidance.py` holds both:

```python
if web:
    base += f"""
## Browser frontend{"s" if len(web) > 1 else ""}

{web_paths} {"are independently built" if len(web) > 1 else "is an independently built"} ...
"""
```

The outer `if web:` decides whether a **whole section** appears. The words inside it are the same words in
every project that has a browser app — that is standing text, case 1, and only its presence is conditional.

The inner `{"s" if len(web) > 1 else ""}` is a **sentence agreeing with a count**. That is not prose a person
edits a paragraph at a time; it is rendered from the declaration, which is case 2.

**So: a whole section moves to the asset behind a marker, and the module selects it. A branch inside a
sentence stays in Python.** The test a contributor applies is the paragraph boundary — *can you point at
where the branch begins and ends, and is it a whole paragraph or more?* If yes, it is a section. If the
branch is inside a sentence, it is rendering and it stays.

**A branch that begins or ends mid-paragraph stays, and the mechanism settles it rather than the test.**
16.3 met the case the question above does not answer: two alternatives, each four lines of whole
sentences, but the branch opening and closing *inside* a bullet rather than around one. The paragraph
boundary gives no clean yes there, and the answer does not need one — `OPEN` and `CLOSE` are anchored to
the start of a line, so a span that begins mid-paragraph cannot be marked as a section at all. The text
stays in Python and the asset carries the frame around it with a token. Said here because two slices met
this shape and the second should not have to re-derive it from the regular expressions.

```markdown
Standing text every project gets.

<!-- section: browser -->
## Browser frontends

The words a project with a browser app gets.
<!-- end section -->
```

The module names what it wants: `prose.render("guidance.md", text, values, wanted=("browser",))`.

**Why a marker and not a template language.** `{% if %}` would make every one of those agreements
expressible in an asset — and then the asset and the declaration would be two places answering "how many
browser apps does this project have", which is the drift case 2 exists to prevent. The marker can express
"this section is here or it is not" and deliberately nothing else. It is an HTML comment because an asset is
copied into a project verbatim before the resolved one is written over it, so a marker that leaked is
invisible in rendered Markdown rather than a stray word in somebody's `AGENTS.md`.

**Why a closed set and not `str.format`.** `format` reads every `{` as a field, which makes a shell `${VAR}`
or a JSON example an escaping question a person writing prose should never have to think about, and answers
a misspelt name with a `KeyError` from the middle of a generation instead of a line naming the file and the
token.

## What is not prose at all

A fourth kind turned up when 16.7 looked at the templates: text that is not English. `init_script.py`
writes shell and `deploy_workflow.py` writes GitHub Actions YAML, and neither is prose a person edits a
paragraph at a time — they are programs, assembled from the answers. **They stay, and the rule above is
not the reason; the rule does not reach them.** This page is about English.

The measure that settled it, taken rather than argued:

| Module | Multi-line literal lines | Of those, interpolating | Largest block |
|---|---:|---:|---|
| `init_script.py` | 167 | 23 | 39 lines, and the rest are shell fragments of 10 to 24 lines chosen per answer |
| `deploy_workflow.py` | 155 | 95 | 25 lines, the workflow's own frame around five strings the target answers |
| `flags.py` | 125 | 109 | **84 lines of English with one substitution in it** |

`init_script.py` looks the most movable on the first number and is the least: its literals are `sh`
fragments — `extension_case`, `extension_expect` — each a few lines selected by whether the project has
extensions. Moving them would put a shell program in a Markdown file to be reassembled by the same
conditionals, which buys a reader nothing and costs them the one file that currently reads top to bottom.
`deploy_workflow.py` is the same answer for the opposite reason: most of it already *is* case 2, and the
frame around it is three strings of YAML keys.

`flags.py` is the one that moved, and it is not a template at all — `release_notes` is the release half of
`docs/deployment.md`, eighty-four lines of English with a single `{{reader-paths}}` in it. Case 1, and the
numbers say so plainly once they are taken per module rather than for the row as a whole.

## What the check refuses

`tests/test_generated_prose.py`, run by `make verify`:

| Refused | Why |
|---|---|
| An asset naming a token nothing provides | It ships `{{make}}` into somebody's repository, where it reads as a typo in the method rather than a bug in the keel — the file is valid markdown either way |
| A value provided that no asset names | A value somebody keeps in step with a path that moved, for no reader at all |
| A rendered file still carrying `{{` after generation | The one the other two cannot make: a token can be provided, named, and still arrive unresolved if a page is copied by a path that does not render it |
| A section opened and never closed, or named twice | Silent and arbitrary otherwise |
| A module selecting a section the asset has not got | A paragraph silently gone from a file somebody receives — the failure the digest gate exists for, caught earlier |

**The third one reads what the keel renders, not every file a project receives**, and that is deliberate.
`{{name}}` is not the keel's spelling alone: a generated project ships `scripts/agents/registry.json` with
`"argPlaceholder": "{{args}}"` and a skill with `{{badges}}`, and both are another system's substitution
that must arrive intact — a harness fills `{{args}}` itself. Scanning everything would refuse those, and the
only way to keep them would be a list of exemptions by name, which goes stale the first time somebody adds a
skill. So `TEMPLATED` in that test names each templated tree and where it lands, and a slice that templates
another adds its row; the rules then hold it without another test being written.

## Not a rewrite of any page

A slice that improves the words while moving them is a slice whose digest gate cannot be run. **Wording
changes go in their own commits, before or after, never inside the move.** Every slice here takes a digest of
every generated file on the commit it is written on, and the new path reproduces it exactly. That gate earned
its place on its first use: rebasing the pilot onto a rename silently reverted a paragraph of the shared
trailer to an older wording, and the digest was the only thing that saw it — lint, the type checker and the
merge all passed.
