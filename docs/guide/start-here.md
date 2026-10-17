# Start here

**Fifteen minutes from nothing to a product repository with one slice demoed.** This page is the first
ten of them: install the command, answer its questions, and watch the gate go green. The next page,
[your first feature](first-feature.md), is the other five.

You need Python 3.10 or newer, Git, and — for a TypeScript or JavaScript project — Node. Nothing else has
to be set up first.

There are two ways through step 3, and they end in the same repository — pick whichever you prefer:

- **In the terminal** — `slipwai generate` asks the questions one at a time:
  [generate the repository](#3-generate-the-repository).
- **In the browser** — `slipwai` opens the board, where the same questions are a form:
  [the same interview, on the board](#the-same-interview-on-the-board).

Steps 1 and 2 are the same for both.

---

## 1. Install the command

```sh
uv tool install slipwai
```

`pipx install slipwai` and `pip install --user slipwai` work too. There is also a standalone executable on
the releases page for a machine with no Python toolchain, which scaffolds with Git alone.

Check it arrived:

```console
$ slipwai --version
slipwai 2.0.0
```

## 2. Get a language

The command itself knows how to scaffold a repository. It does not know TypeScript, or Python, or Go —
those come from the **chandlery**, which is the index of packages it can install from. Look in it:

```console
$ slipwai search
  go            language  1.0.0         available  backends: go
  java          language  1.0.0         available  no description
  java-quarkus  language  1.0.0         available  backends: java-quarkus
  java-spring   language  1.0.0         available  backends: java-spring
  python        language  1.0.0         installed  backends: python
  typescript    language  1.0.0         available  backends: typescript
```

The last column is what each package *answers*, and `slipwai search postgres` searches that rather than the
name — which is usually the search you want: you know you need something that will talk to Postgres for
you, not what it is called.

Install one:

```sh
slipwai install typescript
```

It says where the package came from, which version, who published it, and whether their signature is one
you have trusted. The first time you install from a publisher you have not met you are asked once, and the
answer is remembered; everything after that is silent. The file's checksum is checked against what the
index listed every time, whoever published it.

## 3. Generate the repository

```sh
slipwai generate
```

It asks one question at a time and shows a default for each, so Enter all the way through is a working
project. These are the questions, in the order they come:

```console
$ slipwai generate
Create a new product monorepo. Press Enter to accept a shown default.
Project name: bookings

Start from a quickstart? Each one is a set of answers somebody already settled — which languages, how
the project is laid out, and which optional tooling it switches on.
  none — ask me every question — the interview as it has always been
  laptop-trial — A first project you intend to read, run and throw away: one service on your own
    machine, a real store in a single file, with nothing to install, start or log into.
  internal-tool — A screen over a table for people who work here: a handful of forms, a list, and
    nobody will ever ask what it looked like last March…
Start from (none/laptop-trial/internal-tool/…) [none]:

Delivery foundation:
  event-modelling — Event Modeling — everything above, plus the workflow modelled before it is built
    and delivered one stamped slice at a time, every event a named business fact. Where truth lives is a
    separate question, asked per service…
  standard — Standard — the walking skeleton, the executable test and the CD gate, and no model of the
    workflow behind them. Features are specified one at a time and a service keeps current state…
Use Event Modeling? [Y/n]:

Production target:
  none — Local only — nothing is deployed anywhere; `make verify` is the end of the road
  aws — one ECS service per app, blue/green, RDS Postgres, Cognito, S3 + CloudFront, by OpenTofu
  azure — one Container App per app, PostgreSQL Flexible Server, Entra ID, Static Web Apps
  existing — this project deploys to infrastructure it does not own
Choose (none/aws/azure/existing) [none]:

Language (typescript) [typescript]:
Service name [service]: bookings
What does bookings own? (a sentence or two; Enter to decide later): Taking and changing a reservation.
Bounded contexts bookings holds, comma-separated [bookings]: booking, availability
Frontend (none/react-vite) [react-vite]:
Browser app name [web]:

Write model:
  How a service decides and records a write. Event sourcing is this keel's recommendation and the
  default; answer `state` where a service has earned the exception…

  events — Event-sourced — the log is the truth and state is a fold of it. The recommended answer,
    and the default. Rung 4…
  state — State-stored — the service keeps current state, and its events are the model's contracts,
    raised after each write and never replayed. Rung 2, and the exception rather than the starting
    point…
Choose (events/state) [events]:

Persistence:
  How this service keeps its data. Every answer is one store behind one port…

  memory — In-memory — zero infrastructure, loses all truth on restart…
  postgres — Postgres — the concurrency control the rung names: unique (stream, version) on an
    append-only table where the write model is `events`, a version column checked on save where it is…
Choose (memory/postgres) [postgres]: memory

Who signs in to this product?
  everyone — everyone, through one identity provider — the people who run it and the people it is for
  staff — people who work here, and nobody else — no public sign-up
  separately — staff and customers, through separate issuers — a realm or tenant each, asked separately
Who signs in (everyone/staff/separately) [everyone]:

Authentication:
  Who signs everybody in. One OIDC issuer for the whole product, with sign-up, verification and
  password reset, and a login the browser app owns. Answer `none` to leave identity until later…
Choose (none/keycloak) [none]:

Output parent [~/code]:
Product requirements document (a path; Enter for none):
Everything else (a folder; Enter for none):
created: /Users/you/code/bookings

Running ./init in /Users/you/code/bookings — it installs Spec Kit for the coding agent, so it
reaches the network once, here.
`./init` is done. `make verify` is the gate, and it is green on a new tree.
```

A question with nothing to explain is the one-line form — `Language (typescript) [typescript]:`. One where
the answers need describing prints them first and then asks, which is why the quickstart offer, `Write
model`, `Persistence` and the authentication questions look different. In a terminal all of them are a list
you move through with the arrow keys; the typed form above is what you get in a pipe, a script, or a
terminal that cannot be put into raw mode.

**The first question and the identity one are both there to save you the rest.** A quickstart is a set of
answers somebody already settled, offered by what the product it suits is like rather than by the packages
it names; this keel carries six, `slipwai quickstart list` names them, and every answer one gives is a flag
you could have typed and can still change. `Who signs in` stands in for two axes — the people who run the
product and the people it is for — and asks about the providers only for the ones your answer says exist.
Answer `separately` and you get both questions, which is what every product used to get.

**Two of these questions are different in kind, and only one of them is hard to undo.** `Use Event
Modeling?` decides whether the workflow is drawn before it is built — whether there is a model at all. It is
worth answering yes to on nearly anything a team will keep working on, including a product whose services
store current state, and you can start modelling later: a model is a design practice, not a storage format.
`Write model` is the storage decision, it is asked per service, and **it is the one that cannot be walked
back.** An event log folds down into tables whenever you decide it should, so a service can stop being
event-sourced; state cannot be turned back into history it never recorded, so "start on `state` and adopt
events later where a subdomain earns it" is an option that mostly does not exist. Every other answer here is
a directory you can regenerate, a service you can add, or an axis you can converge later.

**Press Enter on `Write model`.** Event sourcing is this keel's recommendation, and the default, for two
reasons that are about how the work goes rather than about storage. A slice is independently deliverable
because the log is the contract between slices: a later one reads an event without asking the service that
wrote it, and without the two being planned together. And the system stays changeable after the first
design turns out to be wrong, because a read model nobody thought of is a replay away rather than a
migration. Answer `state` where the service has genuinely earned the exception — a small supporting
domain, a context that honestly is field updates, something whose past nobody will ask about — and write
down why, because the asymmetry runs the other way: you can always stop being event-sourced, and you
cannot start having been.

The two were one question until phase 15: choosing Event Modeling chose the log with it, so a product that
wanted the model over services keeping current state could not be generated, and neither could one with a
context that earned the log beside three that did not. They are two answers now, and `project.json` records
the second per deployable. `slipwai add-service --write-model state` is how a later service answers
differently from the first; left out, it takes the first service's answer.

**The last two questions are for a project that starts from a document.** Give the requirements document
and it is copied in as `docs/prd.md` before the first commit; give the folder it sits in instead —
`slipwai generate --brief <dir>` typed — and the document is found in it for you, by its name or its first
heading, while everything else lands under `docs/design/` for the mock-up stage to follow. What was
decided is printed, so a wrong guess is visible. Enter on both is the usual answer, and the specification
is then written in the agent with you, as on [the next page](first-feature.md).

Everything you were asked is written down in `project.json`, and nothing else keeps a second copy of it:
the Makefile, `docker-compose.yml`, the CI workflow and the gate scripts all read that one file.

### The same interview, on the board

`slipwai` on its own opens **the board** — a page served from this machine only — and its *Start a
project* tab is this interview as a form, in the same order and from the same menus. Three things are
easier there: a quickstart fills in the questions below it and leaves every one yours to change, **Dev
tooling** is one checkbox per extension installed here and the ticked ones are handed to `./init`, and the
brief is a folder picked with your own machine's chooser. A project started from a requirements document
does not stop at `./init`: the board runs `make draft`, which writes the first specification from the
document — every call the document did not settle under `## Assumptions` — and stops there, on the
**Voyage** tab, for you to read it. [Your first feature](first-feature.md#from-the-board) carries on from
that page.

`slipwai bridge install` keeps the board up — a login service for your own account, no root — and opens it
so the browser can put it in your dock. `slipwai bridge uninstall` takes it away again.

## 4. Start the repository

```sh
cd bookings
make verify
```

`./init` has already run: the interview ends by running it in the project it has just made, because nothing
in the tree works until it has. It installs Spec Kit for whichever coding agent you use, and wires in the
skills, commands and agent types the profile needs. It reaches the network once, there, and never again.

`slipwai generate --no-init` declines it and leaves `./init` as your next step — which is also what a
scripted `generate` does, where `--init` asks for it. Running `./init` again later is safe, and is how the
agent is changed: `./init --integration <agent>`.

`make verify` is the whole gate — lint, types, tests, the architecture checks, the model and the chart.
It is what CI runs, and it is green on a repository nobody has written a line in yet:

```console
$ make verify

verify: all gates passed
```

**That green is the point of the first ten minutes.** You now have a repository where the gate is a fact
rather than an aspiration, which is the only state from which "keep the main branch releasable" means
anything.

---

## What you just got

```
bookings/
  apps/bookings/        the service: domain, ports, adapters, tests
  apps/web/             the browser app
  docs/event-model/     model.yaml, and the diagrams and page rendered from it
  specs/                one directory per feature: spec, mock-ups, chart, slices
  scripts/              the gates, the agents, the event-model renderer
  skills/ commands/     what the coding agent is given to work with
  project.json          every answer you gave, read by everything above
  Makefile              make help lists the lot
```

`make help` lists every target with a sentence each. You do not need to read it yet.

## Next

→ **[Your first feature](first-feature.md)** — a specification, a model, a chart, a slice, and a demo you
watch happen.

Other pages: [a second person joins](a-second-person.md) · [let it cruise](let-it-cruise.md) ·
[bring an existing codebase](adopt.md) · [the vocabulary](../../GLOSSARY.md)

Two pages are maps rather than steps: [the workflow](the-workflow.md) lists every step from a document to
an accepted capability, and [the board](the-board.md) describes every screen and control.

Want every step on one page? [The generate runsheet](runsheet-generate.md) is this guide as a checklist,
from installing the command to every release after.
