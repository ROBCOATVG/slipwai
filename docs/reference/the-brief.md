# The brief

**A brief is one folder. The requirements document in it is found, not named; everything else is carried;
a surface is a page and a state is an article on it.** A person who has never written a specification can
fill a folder, and a prototyping tool can write one, so the folder is the one shape slipwai's front door
reads. The command is `slipwai generate --brief <dir>`, or the *Everything else* question on the board's
start form. [The prototyping plan](../prototyping-plan.md) says why a folder and not a mode.

```
<brief>/
  prd.md             the requirements document: what it must do, how to tell it works, out of scope
  people.md          one heading per person, with a role and what they do
  domain.md          facts that are true whether or not this product exists, each saying where it came from
  look/              a stylesheet, a brand sheet, a logo: the direction the drawing follows
  surfaces/
    <surface>.html   one page per surface, no framework, no build step
```

Only the first line is required. A folder of wireframes and a brand sheet with no document in it is a
brief; so is a document on its own.

---

## How the requirements document is found

`design_docs.briefed` sorts the folder. It asks three questions in order of how much each proves, and the
first answer wins:

1. **The name a requirements document usually has:** `prd.md`, `prd.txt`, `requirements.md` or
   `brief.md`, anywhere in the folder, in that order.
2. **A name that says what it is:** any `.md` or `.txt` whose name contains `prd`, `requirement` or
   `product brief`, so `game-prd.md` is found.
3. **The document's own first heading:** a `# ` heading containing one of those words, which survives a
   file somebody called `v2-final.md`.

The document lands as `docs/prd.md`. Every relative link in it to a file inside the folder is rewritten to
where that file landed, and a document in a subfolder may point back up into the rest of the brief; a link
outside the folder, a symlink out of it and an absolute path are left exactly as written and never copied.

**No document is an answer, not a failure.** The folder is carried as design material and the
specification is written in the agent, the way it always could be. `generate` prints which it found.

`--prd` and `--design` name either half exactly, and win where both are given: an explicit answer is never
second-guessed.

---

## What everything else is

Every other file lands under `docs/design/`, keeping its own path inside the folder: `look/look.css`
becomes `docs/design/look/look.css`. Dotfiles and dot-directories do not travel. One handed-over tree may
hold at most 200 files and 50 MB; over either, `generate` refuses with the count, because a home directory
or a `node_modules` pointed at by mistake is a refusal naming the size rather than a generate that appears
to hang.

The mock-up stage (`commands/mockups.md`) reads `docs/design/` before it draws anything, and is told to
follow a direction it finds there rather than invent one. The whole folder is committed with the project.

---

## A surface page

A surface is one HTML page under `surfaces/`. `drawn.page_states` reads two things from it and nothing else:

- `<title>` names the surface. A leading *Mock:* or *Mock-up:* is dropped, and so is anything before a dash,
  so `Mock: Club boats — Book a boat` is the surface *Book a boat*.
- Each `<article class="state">` is one state, named by the first `<h2>` inside it. Two articles with the
  same heading are one state.

A page with no article at all is one state, `shown`. That is what the stage read before this contract was
written down, and it is why a plain page is still a brief.

The page is embedded where it is. The surfaces stage storyboards handed-over pages instead of redrawing
them, the storyboard links each page under `docs/design/surfaces/`, and the board's *Approve storyboard*
writes `specs/<feature>/mockups/mock-states.md` from the pages the storyboard shows, one verdict per state.
So a relative `<link rel="stylesheet" href="../look/look.css">` resolves, because `look/` landed beside
`surfaces/` the way it was handed over.

**`data-decided`** on an article records who chose the state: `person`, for a state the person asked for or
answered a question about, or `proposed`, for one the tool put in because every good version of the screen
has it. The storyboard's note on the Voyage window counts them — *16 states: 10 decided by a person, 6
proposed* — and each verdict line in `mock-states.md` ends `(decided by a person)` or `(proposed)`, after
the verdict, so the gates that read the line are unchanged. A page that does not say is written as before.

A page may hold anything else a browser can show. Nothing beyond the title and the articles is read.

---

## People and facts

**`people.md`** is one `## ` heading per person, a `role:` line and a sentence of what they do. It lands as
`docs/design/people.md`, and the draft writes one `specs/<feature>/people/<username>.json` per heading, in
the shape the try-it stories sign in as: the heading lowercased as the username, the heading as the name,
a generated password, the project's realm, the role, and no email. The draft lists them under `## People`
in the specification. A project with no sign-in server has nothing to sign in to, so the draft writes the
heading and no files, and says so.

**`domain.md`** is one `## ` heading per fact and a line saying where it came from. A fact is what is true
whether or not this product exists: *a checkout lasts two years* is a fact; *show the keelboats greyed* is a
decision, and belongs in the document. The file lands as `.specify/domain/brief.md`, beside the project's
own domain files and in their shape, so a decision cites a fact by its heading and the skipper reads what
the business already knows rather than guessing it. Only the folder's top-level `domain.md` is read this
way; one deeper travels as material like anything else.

---

## What the brief does not carry

**Code.** A prototype that arrives as an application is a brownfield repository, and its door is
`slipwai adopt`, with a survey and a convergence map. A folder of static pages is the better route for a
first feature, and this contract does not try to make the other one better.

---

## Who reads what

| In the folder | Lands as | Read by | When |
|---|---|---|---|
| the requirements document | `docs/prd.md` | `/draft` | the first stage after `./init`, which stops with the specification and its `## Assumptions` |
| `surfaces/*.html` | `docs/design/surfaces/*.html` | the surfaces stage, then `drawn.page_states` | the storyboard, and the approve button on the Voyage window |
| `look/` and anything else | `docs/design/…` | `commands/mockups.md` | before a surface is drawn |
| `people.md` | `docs/design/people.md` | the draft, which writes `specs/<feature>/people/` from it | the first stage after `./init` |
| `domain.md` | `.specify/domain/brief.md` | every stage that cites a fact, by its heading | from the draft on |

---

## The refusals

Each ends with what to do.

| `generate` says | Why | The fix |
|---|---|---|
| `--brief <dir> is not a directory` | the flag names the folder, not the document | point it at the folder, or use `--prd <file>` for one document |
| `--brief <dir> holds N files, over the 200 one handed-over tree may carry` | a parent directory was named | point it at the design material rather than at its parent |
| `--brief <dir> is NMB, over the 50MB one handed-over tree may carry` | the folder holds something that is not design material | move the large files out, or link to them from the document |

## The check

`slipwai brief check <dir>` reads the folder the way `generate` would — the same sorting, the same page
reader, the same limits — and prints what it found, before anything is generated:

```
requirements document: prd.md, by name
surfaces: 3, states: 16, each with a heading, 10 decided by a person, 6 proposed
look: look/look.css
people: 2   facts: 2, cited
the draft will have to assume: 1 — Can a member hold two bookings on the same day? (prd.md, ## Open)
```

- A folder with no document says so and exits 0: that is an answer, the one `generate` gives.
- A page with no `<article class="state">` is counted as one state, `shown`, and the line names the page.
- A fact whose section has no `Source:` line is named as having no source.
- The last line is a reading of the document, not the draft: a heading that is a question, whatever is
  under a `## Open` heading, and a bullet that ends in a question mark, says `TBD` or starts `open:`. It
  finds what the document says it left open. What the document does not know it left open, the draft
  finds, and lists under `## Assumptions`.
- Not a directory, and over either limit, are the refusals above, exit 2.

---

## The worked example

[`tests/fixtures/brief/`](../../tests/fixtures/brief/) is a brief as a prototyping tool would export it: a
document with one line left open, two people, two facts with their sources, a look, and three surfaces
with sixteen states between them, each saying who decided it. The suite reads it, so it cannot drift from
the shape this page describes.

---

Next: [the runsheet for a new project](../guide/runsheet-generate.md), where the folder is handed over ·
[the chart and the mark](the-chart-and-the-mark.md), which is written after the storyboard the folder's
surfaces become
