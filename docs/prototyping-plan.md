# The brief: prototyping that feeds slipwai

A plan for a phase after feedback points, written on 2026-11-04 from an exploration that started as "should
slipwai have a prototyping mode". It should not, and this plan says why in one section and then spends the
rest on what to build instead: a contract at slipwai's front door that a prototyping tool can target, so
that a person who has never written a specification can play with a prototype, and what they decided while
playing arrives in a generated project as a requirements document, surfaces with their states, people, facts
and a look. A mock of the whole route, with a clickable prototype of the product it describes, is at
https://claude.ai/artifact/GGdVnjrQzATQi1nUSDj9WM; its sources are under [`mockups/brief/`](mockups/brief/).

**Status, 2026-11-05:** 21.1 to 21.5 have landed. 21.6, the prototyping conversation, is the board's first
page in this repository, after the release carrying 21.2; it was planned as its own repository until the
same day, when the aim was restated as one non-technical person from describing the product through to
delivery, and the board is already their face from the brief door on. Section 8 is the build: the order,
the fixture every slice reads, and the files, tests and gates of each. The table in section 5 is ticked by
hand as each slice merges; the one `scripts/progress.py` ticks from the history is phase 21's table in
[the main plan](slipwai-2-plan.md), which carries one row per slice so that each `Slice-done:` trailer
has a row to count against.

**The principle the plan serves:** a prototype is the cheapest place to be wrong. Every answer a person
gives while tapping through one is a decision the draft stage would otherwise take for them and list under
`## Assumptions`, and every state they see is a state the mock-up stage would otherwise draw and ask them to
approve. So the measure of a prototyping tool is not how fast it makes software. It is how few assumptions
the draft has to make, and whether the storyboard is approved the first time it is shown.

## 1. Why not a mode

Slipwai has five dials and none of them is rigour, and that is deliberate:

| Dial | What it moves | What it leaves alone |
|---|---|---|
| Skiff or liner | The size of the cloud stack | `make verify`, the release modes, the images. [The reference](reference/the-skiff-and-the-liner.md) says so in its last section |
| The telegraph | Boilers, delegates, bunker, stage budgets | The gates. `bar` gets *stricter* as the run slows |
| Sail or cruise, and `upstream` | Who answers, and whether the three upstream stops wait | What the stages are |
| The release mode | How dark a merge is | What a merge must pass |
| Quickstarts and axes | What is generated | The loop that runs in it |

A `prototype` profile beside `standard` and `event-modelling`, or a rigour number under the telegraph, would
be a standing exemption, which rule 5 in `AGENTS.md` forbids by name. The release-mode design derives
behaviour from a fact about the product because *a setting that somebody must remember to change is wrong
each time they forget*; a prototype flag left on is a product built without gates. And each stage a mode
would skip exists because skipping it produced a named failure in the first attempt: screens nobody drew
reached a demo, examples nothing wrote were demoed. A mode brings those back under a switch, and every skill
and check grows an "unless prototype" branch.

Two readings of "prototype" remain, and they get different answers:

- **Answer a question, then throw the code away.** A spike. The story-splitting skill already defines it:
  timeboxed, explicitly disposable, acceptance criteria phrased as answered questions. That belongs inside
  the loop as a slice kind whose branch never merges, and it is **not this plan**: section 5 lists it as the
  thing to do next.
- **Get a person to a thing they can play with, before anything is specified.** This plan.

## 2. What exists today

The front door is `slipwai generate --brief <dir>`, or the board's *Everything else* field on the start
form. `design_docs.py` sorts the folder:

- **The requirements document is found by name, then by heading.** `prd.md`, `prd.txt`, `requirements.md`
  or `brief.md` wins; otherwise any `.md` or `.txt` whose name or first heading says PRD, requirement or
  product brief. Relative links from it to files in the folder are rewritten to where they land.
- **Everything else lands under `docs/design/`**, at most 200 files and 50 MB, and nothing outside the
  folder travels. `commands/mockups.md` reads the directory before drawing and is told to *follow it rather
  than invent one*.
- **Handed-over surfaces are reviewed, not redrawn.** The surfaces stage storyboards them where they are,
  `passage.surface_pages` reads the pages the storyboard embeds, and `drawn_states` reads each page's
  `<title>` as the surface and each `<article class="state">`'s `<h2>` as a state. The board's approve
  button writes `mock-states.md` from that, one verdict per state.
- **The draft lists what the document did not settle** under `## Assumptions`, so a brief has a score the
  moment it is drafted.

Two things the loop wants have no door at generation: domain facts, which live in `.specify/domain/` and
are *cited, never summarised*; and people, the actors a story signs in as, which live as JSON under
`specs/<feature>/people/` and cannot exist before the draft makes the feature directory.

## 3. The contract

One folder. Its shape, as a prototyping tool must write it and as `slipwai brief check` (21.2) reads it:

```
<brief>/
  prd.md             the requirements document: what it must do, how to tell it works, out of scope
  people.md          one heading per person, with role and what they do      (21.3)
  domain.md          facts true whether or not this product exists, cited    (21.4)
  look/              a stylesheet, a brand sheet, a logo: the direction to follow
  surfaces/
    <surface>.html   one page per surface, no framework, no build step
```

A surface page carries `<title>` naming the surface and one `<article class="state">` per state, headed by
an `<h2>` naming the state. That is the whole contract for a screen, and it is what the board reads today.
Two optional attributes make the hand-over richer without changing what the keel reads: `data-decided="person"`
or `data-decided="proposed"` on the article, which the board shows beside the state (21.5); and a `<link>` to
`../look/*.css`, which the storyboard then serves from where it is.

What the contract does **not** carry: code. A prototype that arrives as a React application is a brownfield
repository, and its door is `slipwai adopt`, with a survey and a convergence map. That is a worse route for a
first feature than a folder of static states, and the plan does not make it better.

## 4. The prototyping tool

It is the board's first page, and the only thing it and the rest of the board share is section 3: it
writes the folder, and everything after it reads the folder. It was planned as a separate tool that never
imports the keel, for a different user with a different output; the aim since 2026-11-05 is one
non-technical person from describing the product through to delivery, and from the brief door on that
person's face is already the board — *Everything else* on the start page, `./init` and `/draft` run from
it, the storyboard approved on the Voyage page, Continue the build a button. A separate tool would put a
folder path between them and all of that. Its working title in the mock is *Sketch*. What it has to do:

1. **Draw a prototype the person can play**, from what they say. Not screens: a thing with taps. The mock's
   fourth frame is the shape — one screen per surface, the states reachable by doing things, two people to
   sign in as.
2. **Walk the states.** Loading, empty, populated, partial, error, recovery, permission denied, offline: the
   same list the mock-up researcher asks per surface. It asks the ones a person has to answer, proposes the
   ones every good version of a screen has, and writes each as a state with who decided it. Nobody draws a
   loading state unprompted, and the builder builds every state whether or not somebody talked about it.
3. **Write decisions as they happen.** Every "no, grey it" is a line in `prd.md`. The draft's assumptions
   count is the metric.
4. **Keep facts apart from choices.** *A checkout lasts two years* goes in `domain.md`; *show the keelboats
   greyed* goes in `prd.md`. The keel's own domain module makes this distinction the whole point, and the
   person who has never written a spec is exactly the person who knows the facts.
5. **Name the people.** Role, name, what they do. They become the people files and the demo as the actor.
6. **Record what is out of scope**, which a prototype never records and the split always needs.
7. **Check before hand-over, in plain words.** Green for what the builder can start without asking, amber for
   what it will decide and say. The person never opens the folder; the developer can.
8. **Export static state pages**, not the prototype's code. The prototype is for the person to play with. What
   crosses the boundary is one page per surface, one block per state.

Its first version is a conversational session the board runs the way it runs the draft — one headless
session of the installed harness, with the person present in the page — using the toolkit's own skills:
`frontend-design`, `storyboard`, `find-gaps` in its design-mock mode; the mock-up stage's researcher and
draughtsman, run before a project exists. It writes the folder of section 3 under the board's own
directory and hands it to the start page as the *Everything else* answer, so the person presses one button
and never sees a path. The folder is still the seam: an outside tool that writes the same shape comes in by
the same door, and `slipwai brief check` is the acceptance for both.

## 5. The slices

Keel side first, because a tool cannot target a contract nobody has written down. Sizes as in the other
plans: S is a morning, M a day, L two or three.

| Slice | What lands | Size | Status |
|---|---|---|---|
| 21.1 | `docs/reference/the-brief.md`, and the fixture brief the page points at | S | done |
| 21.2 | `slipwai brief check <dir>`, and the page readers moved to `drawn.py` | M | done |
| 21.3 | People in the brief: `people.md` becomes `specs/<feature>/people/` at the draft | M | done |
| 21.4 | Domain facts in the brief: `domain.md` lands as `.specify/domain/brief.md` | S | done |
| 21.5 | Who decided a state: `data-decided` read, counted on the board, written to `mock-states.md` | S | done |
| 21.6 | The prototyping conversation, as the board's first page | L | todo |

### 21.1 `docs/reference/the-brief.md` — S

The contract of section 3 as a reference page, in the shape of the other reference pages: what is read,
by which module, and what each refusal says. Links from `runsheet-generate.md` and the board's *Everything
else* help text. No code changes.

### 21.2 `slipwai brief check <dir>` — M

Reads a folder the way `generate --brief` would and prints what it found, before anything is generated:

```
requirements document: prd.md, by name
surfaces: 3, states: 16, each with a heading
look: look/look.css
people: 2   facts: 2, cited
the draft will have to assume: 1 — one booking per member per day (prd.md leaves it open)
```

- It calls `design_docs.briefed` and `passage`'s page readers, so what it prints is what the stage will read.
- A surface page with no `<article class="state">` is reported as one state, `shown`, which is what
  `drawn_states` does, and the line says so.
- "Will have to assume" is a heuristic over `prd.md`: a question mark in a heading or a bullet, `TBD`,
  `open:`, and a `## Open` section. The line names the file and the heading. It is not the draft.
- Every refusal ends with the command or edit that fixes it.
- Tests: a fixture brief under `tests/fixtures/brief/`; a brief with no PRD prints the "written in the
  agent" line; an oversized folder refuses with the count.

### 21.3 People in the brief — M

`people.md` in the folder, one `##` heading per person with `role:` and a line of what they do. The draft
writes `specs/<feature>/people/<username>.json` from it, in the shape `try_it.people()` reads, with a
generated password and no email. `draft.md` names the file; `check-try` already refuses a username the realm
holds. A brief with no `people.md` changes nothing.

### 21.4 Domain facts in the brief — S

`domain.md` in the folder is copied to `.specify/domain/brief.md` at generation, with a first line saying
where it came from. The skipper's citation rule needs no change: a fact there is a fact to cite.

### 21.5 Who decided a state — S

`drawn_states` reads `data-decided` on a state article where it is present. The voyage's storyboard card
shows it beside the state. `record_verdict` writes it into `mock-states.md` as a trailing `(decided by
<who>)` on the state line, so the split and the example map can see which states a person chose and which
were proposed.

### 21.6 The prototyping conversation, as the board's first page — L

A page before the start page, in this repository, that runs the eight steps of section 4 as a board
session and writes the folder of section 3 under the board's directory. The three frames of the mock —
describe it, walk the states, check and hand over — are its three faces, and hand-over is a button that
fills the start page's *Everything else* answer. It runs its session the way `draft.py` runs the draft and
the surfaces stage runs its draughtsman: the harness's own session, the toolkit's skills, the board
reading what it says. Its acceptance test is one real brief through the page, `generate --brief`, `/draft`
and `make surfaces` on a laptop-trial quickstart, with the two numbers recorded: assumptions after the
draft, and whether the storyboard was approved the first time. Where it does not reach: a person still
installs slipwai, Docker and a harness to have a board at all. That is section 6's last line and a plan of
its own.

## 6. What this plan does not do

- **It does not add a mode, a profile or a telegraph number.** Section 1.
- **It does not build the spike slice kind.** That is the right answer to the other reading of "prototype":
  a slice with a question and a timebox, whose branch is kept as a ref and never merges, whose output is a
  finding under `docs/spikes/`. It needs a chart entry kind, a command and one refusal, and it is a plan of
  its own.
- **It does not accept a prototype's code.** A code prototype is an adoption.
- **It does not change the storyboard stop.** The person still approves, surface by surface, on the board.
  The brief makes the drawings theirs; it does not skip the look.
- **It does not make the board reachable without a terminal.** Through to delivery for a non-technical
  person is blocked by installation — a Python CLI, Docker, a harness and its login, a cloud target — not
  by where the prototyping conversation lives. 21.6 is a better front door onto the same step; a board a
  person can have without a terminal is a plan of its own, and a bigger one.

## 7. Open points

- Whether `people.md` should also let a brief name an existing realm user, for a brief written against a
  product that already has one.
- Whether the tool should emit `given/when/then` examples per state for the event-modelling profile, or leave
  that to the model stage. Leaving it is the default: the model derives examples from approved surfaces, and
  a second source of examples is a second thing to keep in step.
- The tool's name. *Sketch* is the mock's working title and nothing more.

## 8. The build

Written on 2026-11-04 from the code on `main` at `be3e9b1`, module by module. Every slice is one branch off
`main`, one pull request, one `changelog.d/` fragment and a commit ending `Slice-done: 21.<n>`, with
`make progress` run after it so the main plan's phase 21 row is ticked in the same commit; the fast
gate inside the slice, `make verify` once before the merge, the same as every other phase. A new module
gets its `TIERS` line in `scripts/check-structure.py` in the commit that adds it.

### The order

Two tracks, both starting from 21.1:

```
21.1 the page and the fixture
  ├── 21.2 brief check, and drawn.py ── 21.5 data-decided
  └── 21.4 domain.md ──────────────────── 21.3 people.md
21.6 the board's first page, once the release carrying 21.2 is out
```

- **21.1 first** because the fixture it adds is what 21.2's tests read line for line, what 21.4 and 21.3
  generate from, and what 21.6 has to reproduce.
- **21.2 before 21.5** because 21.2 moves the page readers out of `passage.py` into `drawn.py`, and 21.5
  edits them there. `passage.py` stands at 449 of its 450 lines; a change to the readers where they are
  would be a budget argument instead of a slice.
- **21.4 before 21.3** because both touch the `--brief` block of `cli_generate.py`, 21.4 is the smaller
  change, and 21.3 then rebases onto a settled shape. The two tracks do not touch each other's files.
- **21.6 last and elsewhere.** The tool targets a released keel, and its first job is to make `slipwai brief
  check` print the fixture's six lines for a brief it wrote itself.

### The fixture: `tests/fixtures/brief/`

The club boat bookings brief from the mock, written as the tool would export it and no larger than the
contract needs:

```
tests/fixtures/brief/
  prd.md             the decisions Sam made; a `## Open` section with one line, so the assume heuristic has one thing to find
  people.md          `## Sam` role: member; `## Jo` role: bosun; one sentence each
  domain.md          two facts, each with a line saying where it came from (the club's rules), so both read as cited
  look/look.css      the club blue, one font, nothing else
  look/logo.svg
  surfaces/book-a-boat.html             7 states
  surfaces/my-bookings.html             5 states
  surfaces/boat-out-of-service.html     4 states
```

Each page carries `<title>`, `<link rel="stylesheet" href="../look/look.css">`, and one
`<article class="state" data-decided="person|proposed">` per state with its `<h2>`. The count of each
`data-decided` value is ten `person` and six `proposed`, asserted by 21.5. The page under
`docs/reference/` links this folder as the worked example, the way the quickstarts are the reference's other
worked examples.

### 21.1 — the page and the fixture

- `docs/reference/the-brief.md`, new, in the shape of the other reference pages: the folder; how the
  requirements document is found (`PRD_NAMES`, `PRD_WORDS`, the first heading) and what happens when none
  is; where everything else lands and the two limits; a surface page, its `<title>`, its articles and the
  `shown` state a page with no article gets; the two optional attributes; what the folder does not carry,
  and why that is `adopt`; a table of which module reads each file at which stage; and every refusal with
  the command or edit that fixes it. The page describes the code as it is, so the `people.md`,
  `domain.md` and `data-decided` rows say *planned, 21.3* and so on until each slice turns its row present
  tense in its own pull request.
- A row in `docs/reference/README.md`; the *1.1: from a document* bullet of `docs/guide/runsheet-generate.md`
  links the page; the *Everything else* question's `why` in `interview_page.py` ends with the page's path.
  `tests/test_interview_page.py` is read first for a pinned copy of that text.
- `tests/fixtures/brief/` as above, and one case in `tests/test_design_docs.py`: `briefed(fixture)` finds
  `prd.md` by name and seven other files.
- Fragment `21.1-the-brief-reference.md`, PATCH, catch-up nothing.

### 21.2 — `slipwai brief check <dir>`

- `src/slipwai/drawn.py`, new, edge tier beside `passage`: the four regexes, `_plain`, `_surface_name`,
  `surface_pages`, a new `page_states(page) -> tuple[str, list[str]]` that `drawn_states` is then a loop
  over, and `record_verdict`. `passage.py` imports the four public names back so `bridge.py`,
  `upstream.py`, `voyage_page.py` and `tests/test_passage.py` keep their imports, and its budget line comes
  down to what is left. Nothing changes behaviour; `test_passage` is the proof.
- `src/slipwai/brief_check.py`, new, edge tier beside `design_docs`: `people(path)` (one `## ` heading per
  person, a `role:` line), `facts(path)` (one `## ` heading per fact, cited where a line says where it came
  from, which is the shape `.specify/domain/README.md` asks for), `assumptions(prd)` (a question mark in a
  heading or a bullet, `TBD`, `open:`, a `## Open` section; each named by file and heading), and
  `report(home) -> list[str]`. It calls `design_docs.briefed`, `design_docs.weighed` and
  `drawn.page_states`, so what it prints is what the stage will read. The lines, exactly:

  ```
  requirements document: prd.md, by name
  surfaces: 3, states: 16, each with a heading
  look: look/look.css
  people: 2   facts: 2, cited
  the draft will have to assume: 1 — one booking per member per day (prd.md, ## Open)
  ```

  A folder with no document says `requirements document: none; the specification is written in the agent`
  and exits 0, the answer `generate` gives. A page with no article says `1 state (shown: the page has no
  <article class="state">)`. Not a directory and over the limits are refusals, exit 1, each ending with the
  fix. `people` and `facts` are read here, before 21.3 and 21.4 do anything with them, so the output is
  stable from this slice on.
- `src/slipwai/cli_brief.py`, new: `brief_main(argv)`, `prog="slipwai brief"`, the one sub-verb `check`;
  `brief` in `VERBS` and a row in `dispatch`'s tuple in `cli.py`.
- Tests, all fast: `tests/test_brief_check.py` over the fixture's six lines; no document; no `surfaces/`;
  a page with no article; `FILES + 1` files refused with the count; the four assumption shapes, and a
  heading that is a question counted once. `tests/test_cli.py`: `slipwai brief` alone prints usage naming
  `check`.
- `docs/reference/the-brief.md` gains *What `slipwai brief check` says*; the runsheet's 1.1 bullet says to
  run it before `generate`.
- Fragment `21.2-brief-check.md`, MINOR, catch-up nothing: it is a verb of the command.

### 21.5 — who decided a state

- `drawn.py`: `_ARTICLE` keeps the opening tag's attributes as a group; `page_states` returns each state
  with its `data-decided` value or `""`; `drawn_states` keeps its shape as a projection, and a new
  `decided_states` carries the value. `record_verdict` writes `- <state> — approved (decided by sam)` and
  `- <state> — parked: <why> (decided by sam)` where the value is present and the line it writes today
  where it is not. The three readers of that line — `check-surfaces.py`'s `STATE`, `agents/surfaces.py`'s
  `VERDICT`, `agents/feedback.py` — match `— approved` and `— parked` with a word boundary and are not
  touched; one test runs `check-surfaces.py`'s regex over a line with the suffix to prove it.
- `voyage_page.py`'s `verdict_form`: where any state carries the attribute, the note gains one line, `16
  states: 10 decided by Sam, 6 proposed`, and nothing otherwise. The file stands at 785 of 790 lines; the
  line is written inside that or the budget moves with its reason in the same commit.
- `brief_check.py`'s surfaces line gains `, 10 decided by a person, 6 proposed` where any page carries it.
- `assets/toolkit/commands/mockups.md`: one sentence saying a handed-over page may carry `data-decided`
  and a redraw keeps it. `tests/fixtures/command-pages.sha256` is taken again with
  `PYTHONPATH=src:tests python3 tests/command_pages.py`.
- Tests: `test_passage` (the suffix written, a page without the attribute unchanged, a parked line keeps
  the suffix after the reason), `test_voyage` (the count line), `test_brief_check` (the fixture's split).
- Fragment `21.5-decided-states.md`, MINOR; catch-up `slipwai migrate`, which brings the command page.

### 21.4 — domain facts in the brief

- `cli_generate.py`, the `--brief` block: a `domain.md` at the folder's top is taken out of `rest` before
  the rest is weighed, and written through `files`, the way `docs/prd.md` is, as `.specify/domain/brief.md`
  with a first line: *Handed over with the brief as `domain.md`. A fact here is cited by its heading, like
  any other file in this directory.* `domain_files` already writes the directory's `README.md` on every
  profile, so nothing else is scaffolded. The `brief:` line printed at generation names the copy.
- Tests, in `tests/test_design_docs.py`, following the case there that generates and reads the tree: a
  generate from the fixture lands `.specify/domain/brief.md` with that first line and both headings, and
  no `docs/design/domain.md`; a brief without one writes nothing. That module already shells out to
  `generate` and is not in `SLOW`; if `make unit` slows for it, it moves to `SLOW` in the same commit.
- `the-brief.md`'s `domain.md` row turns present tense.
- Fragment `21.4-brief-domain.md`, MINOR; catch-up for a project generated from a brief before this:
  `cp docs/design/domain.md .specify/domain/brief.md`.

### 21.3 — people in the brief

- `people.md` already travels, as `docs/design/people.md`; the keel changes nothing at generation.
- `assets/toolkit/commands/draft.md` gains a step after the assumptions step: where `docs/design/people.md`
  exists, write `specs/<feature>/people/<username>.json` per `## ` heading, in the shape `try_it.py`'s
  `declared_people` reads — `username` from the heading, lowercased; `name`; a generated password, sixteen
  characters, never reused; `realm`; `roles` from the `role:` line; no `email` — and name each file in the
  say-back and under a `## People` heading in the specification. The one line to settle at the keyboard is
  `realm`: it is read from `docker/keycloak/realms/`, against `try_it.py`'s own reading, and the step says
  what a project with no sign-in server writes. `check-try` (20.1) already refuses a username a realm holds.
- `brief_check.people` (21.2) and this step read the same shape; `the-brief.md` states it once, and both
  cite the page.
- Tests: `command-pages.sha256` taken again; a prose test in the style of `tests/test_skills.py` that
  `draft.md` names `docs/design/people.md` and `specs/<feature>/people/`; `test_brief_check` already holds
  the fixture's two people.
- Fragment `21.3-brief-people.md`, MINOR; catch-up `slipwai migrate` for the page, and a project whose
  draft has already run writes the files by hand from `docs/design/people.md`.

### 21.6 — the board's first page

Planned in outline only, once the release carrying 21.2 is out; its own section 8 is written then, module
by module, the way this one was. What it stands on: the reference page as the contract, `tests/fixtures/brief/`
as the folder it must write, `slipwai brief check` as its acceptance, and three things the board already
has — a headless session run from a page (`init_run.py`, `scripts/agents/draft.py`), a card that shows what
a session says as it says it (`console_page.py`), and the start page's *Everything else* answer
(`interview_page.py`). What it adds: one page module and its card, a session script in the toolkit's
`scripts/agents/` that runs the eight steps with the person present, and the hand-over button. Its README
line is the two numbers from one real brief through the page, `generate --brief`, `/draft` and `make
surfaces` on a laptop-trial quickstart. Its name is open point 3; *the first page* will do until then.

### What to watch

- **Budgets.** `passage.py` 449/450 until 21.2 moves the readers; `voyage_page.py` 785/790 at 21.5.
- **Typecheck.** The vendored mypy wants Python 3.14: `PYTHONPATH=.python-tools python3.14 -m mypy`.
- **The ten captain and cruise-question tests** that fail on this machine fail on `main` too; a slice does
  not own them, and `make verify` in CI is the reading that counts.
- **Words.** The folder is *the brief*; the tool is unnamed; nothing here is a mode, a profile or a rigour.
