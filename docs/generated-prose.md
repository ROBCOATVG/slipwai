# Generated prose: what may be an asset, and what may not

`src/slipwai/project/` writes every file that a generated project receives. Just under half of that code,
by line, is English inside string literals that are not docstrings. This page says three things:

- which of that English can move out to `assets/`
- which English must stay generated
- what to do with a paragraph that branches

These numbers were measured on 2026-10-12 with `ast` over the tree, not estimated by eye:

- **94 modules, 14,566 lines.**
- **6,996 of those lines are inside multi-line string literals that are not docstrings. That is 48%.**
- **Thirty-four modules are more than 60% prose by line.**
- **Ten modules are at or over 300 lines, and the budget is 350 lines.**

The line budget is a rule about code that a person must hold in their head. Paragraphs of English were
using it up. During one day's work in October 2026, two modules reached the budget, and English was what
filled both of them.

## The three kinds, and only one of them may leave

**1. Standing text. This kind moves.** These are the same words in every project, or the same words with
a value substituted. Standing text becomes a `.md` file under `assets/`. Each `{{token}}` in it must come
from a closed set.

**2. Text rendered from a declaration. This kind must not move.** Examples are the delegable-types table
built from `STAGES`, the axis tables from `catalog.json`, and a service list from `project.json`. This
text is generated so that it cannot drift from the declaration. If an asset wrote it by hand, the asset
would be a second answer to a question that the declaration already answers.

The pilot drew this line first. A brief carries its `description`. A brief is refused if it writes
`name`, `stage`, `writes` or `commands`, because a harness enforces those four.

**3. Text that branches. The rule for this kind is below.** The branch can depend on the profile, the
rung, the backend or the target.

## The branch: a section may move, a sentence may not

People call two different things "conditional prose". One `if` in `guidance.py` contains both:

```python
if web:
    base += f"""
## Browser frontend{"s" if len(web) > 1 else ""}

{web_paths} {"are independently built" if len(web) > 1 else "is an independently built"} ...
"""
```

- The outer `if web:` decides whether a **whole section** appears. Every project that has a browser app
  gets the same words inside it. So the words are standing text (kind 1). Only the presence of the
  section is conditional.
- The inner `{"s" if len(web) > 1 else ""}` makes a **sentence agree with a count**. A person does not
  edit that one paragraph at a time. It is rendered from the declaration, so it is kind 2.

**The rule: a whole section moves to the asset, behind a marker, and the module selects it. A branch
inside a sentence stays in Python.**

To apply the rule, look at the paragraph boundary. Ask: *can you point at where the branch begins and
ends, and is it a whole paragraph or more?* If the answer is yes, the branch is a section. If the branch
is inside a sentence, it is rendering, and it stays in Python.

**If a branch begins or ends in the middle of a paragraph, it stays in Python. The mechanism decides this
case, not the question.** Slice 16.3 found a case that the question does not answer. There were two
alternatives, and each was four lines of whole sentences. But the branch opened and closed *inside* a
bullet, not around it. The paragraph boundary gives no clear yes for that case, and no answer is needed.
`OPEN` and `CLOSE` are anchored to the start of a line, so a span that begins in the middle of a line
cannot be marked as a section. The text stays in Python, and the asset carries the frame around it with a
token.

**The rule is about the paragraph, not the line.** Slice 16.5 found the case that separates the two. A
branch began and ended on whole lines, but it covered only part of a paragraph: the second half of
*Running ready slices concurrently*, with the paragraph continuing on both sides. The mechanism would mark
that branch without a problem. The rule still says no.

A section is a unit whose edges a reader can see. Half a paragraph is not a unit. If you mark it, the asset
gets a seam in the middle of an argument. That loses the readability that this work exists to gain. So
the test stays as written: *is it a whole paragraph or more?* A branch smaller than a paragraph stays in
Python, even if the markers could hold it.

```markdown
Standing text every project gets.

<!-- section: browser -->
## Browser frontends

The words a project with a browser app gets.
<!-- end section -->
```

The module names the sections that it wants:
`prose.render("guidance.md", text, values, wanted=("browser",))`.

**Why a marker, and not a template language.** With `{% if %}`, an asset could express every one of those
agreements. Then the asset and the declaration would be two places that answer "how many browser apps does
this project have?". That is the drift that kind 2 exists to prevent. The marker can express only "this
section is here, or it is not". It can deliberately express nothing else.

The marker is an HTML comment for a reason. Slipwai copies an asset into a project exactly as it is, and
then writes the resolved file over it. So if a marker leaked, it would be invisible in rendered Markdown. It
would not be a stray word in somebody's `AGENTS.md`.

**Why a closed set, and not `str.format`.** `format` reads every `{` as a field. So a shell `${VAR}` or a
JSON example becomes an escaping problem, and a person writing prose should never have to think about
that. Also, `format` reports a misspelt name with a `KeyError` from the middle of a generation. A closed
set reports a line that names the file and the token.

## What is not prose at all

Slice 16.7 found a fourth kind when it looked at the templates: text that is not English.
`init_script.py` writes shell, and `deploy_workflow.py` writes GitHub Actions YAML. A person does not edit
either of them one paragraph at a time. They are programs, assembled from the answers.

**They stay in Python. The rule above is not the reason, because the rule does not apply to them.** This
page is about English.

This measurement settled it:

| Module | Multi-line literal lines | Of those, interpolating | Largest block |
|---|---:|---:|---|
| `init_script.py` | 167 | 23 | 39 lines, and the rest are shell fragments of 10 to 24 lines chosen per answer |
| `deploy_workflow.py` | 155 | 95 | 25 lines, the workflow's own frame around five strings the target answers |
| `flags.py` | 125 | 109 | **84 lines of English with one substitution in it** |

- **`init_script.py`** looks the easiest to move from the first number, but it is the hardest. Its
  literals are `sh` fragments, such as `extension_case` and `extension_expect`. Each fragment is a few
  lines, selected by whether the project has extensions. If you moved them, a shell program would sit in a
  Markdown file, and the same conditionals would assemble it again. That helps no reader. It also loses the
  one file that a reader can currently read from top to bottom.
- **`deploy_workflow.py`** stays for the opposite reason. Most of it already *is* kind 2. The frame around
  it is three strings of YAML keys.
- **`event_model.py`'s workflow** also stays. Slice 16.5 found that no slice owned it: 16.7's row names
  three modules and not this one. It is the same kind of text, for the same reason. It is GitHub Actions
  YAML assembled from the profile and the services, not English. It also explains why `event_model.py` is
  still near its budget after its prose moved out. Slice 16.8 owns that question. It is not a reason to
  move YAML into Markdown.
- **`flags.py`** is the one module that moved, and it is not a template at all. `release_notes` is the
  release half of `docs/deployment.md`: eighty-four lines of English with one `{{reader-paths}}` in it.
  That is kind 1. The numbers show this clearly when you take them per module, not for the whole row.

## What the check refuses

`make verify` runs `tests/test_generated_prose.py`. It refuses these things:

| Refused | Why |
|---|---|
| An asset that names a token that nothing provides | The asset would ship `{{make}}` into somebody's repository. There it looks like a typo in the method, not a bug in the keel. The file is valid Markdown in both cases, so nothing else catches it |
| A value that is provided but that no asset names | Somebody would keep that value in step with a path that moved, and no reader would ever see it |
| A rendered file that still contains `{{` after generation | The other two checks cannot catch this. A token can be provided and named, and still arrive unresolved, if a page is copied by a path that does not render it |
| A section that is opened and never closed, or that is named twice | Without this check, the result is silent and arbitrary |
| A module that selects a section that the asset does not have | A paragraph would silently disappear from a file that somebody receives. The digest gate exists for this failure. This check catches it earlier |

**The third check reads only what the keel renders, not every file that a project receives. This is
deliberate.** `{{name}}` is not only the keel's spelling. A generated project ships
`scripts/agents/registry.json` with `"argPlaceholder": "{{args}}"`, and a skill with `{{badges}}`. Both
belong to another system's substitution, and both must arrive unchanged. For example, a harness fills
`{{args}}` itself.

If the check scanned every file, it would refuse those. The only way to keep them would be a list of
exemptions by name, and that list would go out of date the first time somebody added a skill. So
`TEMPLATED` in that test names each templated tree and where it lands. A slice that templates another tree
adds a row for it. The rules then cover that tree, and nobody needs to write another test.

## Not a rewrite of any page

If a slice improves the wording while it moves the words, the slice cannot run its digest gate. **Put
wording changes in their own commits, before or after the move. Never put them inside the move.**

Every slice here takes a digest of every generated file on the commit that the slice is written on. The new path
must reproduce that digest exactly. That gate proved its value the first time it ran. A rebase of the
pilot onto a rename silently changed a paragraph of the shared trailer back to an older wording. The
digest was the only thing that saw it. Lint, the type checker and the merge all passed.
