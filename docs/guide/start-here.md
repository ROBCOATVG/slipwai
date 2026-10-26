# Start here

**In about fifteen minutes, you go from nothing to a product repository with one slice demoed.** This
page covers the first ten minutes: install the command, answer its questions, and see the gate pass. The
next page, [your first feature](first-feature.md), covers the other five minutes.

You need these before you start:

- Python 3.11 or newer
- Git
- Node, for a TypeScript or JavaScript project

You do not need to set up anything else first.

You can do step 3 in two ways. Both ways make the same repository. Use the way that you prefer:

- **In the terminal.** `slipwai generate` asks the questions one at a time. Go to
  [generate the repository](#3-generate-the-repository).
- **In the browser.** `slipwai` opens the board, which shows the same questions as a form. Go to
  [the same interview, on the board](#the-same-interview-on-the-board).

Steps 1 and 2 are the same for both ways.

---

## 1. Install the command

```sh
uv tool install slipwai
```

`pipx install slipwai` and `pip install --user slipwai` also work. The releases page also has a standalone
executable for a machine that has no Python toolchain. The executable needs only Git to create a project.

Make sure that the command is installed:

```console
$ slipwai --version
slipwai 2.0.1
```

## 2. Get a language

The command knows how to create a repository. It does not know TypeScript, Python or Go. Languages come
from the **chandlery**. The chandlery is the index of packages that the command can install. Look in the
chandlery:

```console
$ slipwai search
  go            language  1.0.0         available  backends: go
  java          language  1.0.0         available  no description
  java-quarkus  language  1.0.0         available  backends: java-quarkus
  java-spring   language  1.0.0         available  backends: java-spring
  python        language  1.0.0         installed  backends: python
  typescript    language  1.0.0         available  backends: typescript
```

The last column shows what each package *answers*. `slipwai search postgres` searches that column, not the
package name. Usually, this is the search that you want: you know that you need something that works with
Postgres, but you do not know what the package is called.

Install one package:

```sh
slipwai install typescript
```

The command tells you:

- where the package came from
- which version it is
- who published it
- whether you trust the publisher's signature

The first time that you install from a new publisher, the command asks you to confirm that publisher. It
remembers your answer and does not ask again. Each time, for every publisher, the command checks the
file's checksum against the checksum in the index.

## 3. Generate the repository

```sh
slipwai generate
```

The command asks one question at a time and shows a default for each question. If you press Enter for
every question, you get a working project. These are the questions, in the order that they come:

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

There are two forms of question:

- A question that needs no explanation uses one line, for example `Language (typescript) [typescript]:`.
- A question whose answers need a description prints the answers first and then asks. This is why the
  quickstart offer, `Write model`, `Persistence` and the authentication questions look different.

In a terminal, each question is a list. Use the arrow keys to move through the list. You see the typed form
above in a pipe, in a script, or in a terminal that cannot go into raw mode.

**The first question and the identity question save you from answering the others.**

- A quickstart is a set of answers that somebody has already decided. The keel offers each quickstart by
  what its product is like, not by the packages that it names. The keel carries six quickstarts.
  `slipwai quickstart list` names them. Each answer that a quickstart gives is a flag that you could have
  typed, and you can still change it.
- `Who signs in` replaces two questions: the people who run the product, and the people that the product
  is for. It asks about identity providers only for the groups that your answer says exist. If you answer
  `separately`, you get both questions. Before this question existed, every product got both questions.

**Two of these questions are different from the others, and only one of them is hard to undo.**

- `Use Event Modeling?` decides whether you model the workflow before you build it, that is, whether there
  is a model at all. Answer yes for nearly any product that a team will continue to work on. This includes
  a product whose services store current state. You can also start to model later. A model is a design
  practice, not a storage format.
- `Write model` is the storage decision. The command asks it for each service. **You cannot reverse this
  decision.** An event log can become tables whenever you decide, so a service can stop being
  event-sourced. But state cannot become a history that it never recorded. So the plan "start on `state`
  and adopt events later where a subdomain needs them" mostly does not work.

You can change every other answer later: it is a directory that you can regenerate, a service that you can
add, or an axis that you can converge later.

**Press Enter on `Write model`.** Event sourcing is the keel's recommendation and the default. There are two
reasons, and both are about how the work goes, not about storage:

- **Each slice can be delivered on its own.** The log is the contract between slices. A later slice reads
  an event without asking the service that wrote it, and the two slices do not need to be planned together.
- **The system stays easy to change when the first design is wrong.** A new read model needs a replay of the
  log, not a migration.

Answer `state` only where the service really is an exception. Examples are a small supporting domain, a
context that really is only field updates, or something whose history nobody will ask about. Write down the
reason. The decision only goes one way: you can always stop being event-sourced, but you cannot start to
have been event-sourced.

Until phase 15, these two answers were one question. If you chose Event Modeling, you also chose the log.
So you could not generate a product that had a model but services that kept current state. You also could
not generate a product where one context used the log and three contexts did not. Now they are two answers,
and `project.json` records the second answer for each deployable. To give a later service a different
answer from the first service, use `slipwai add-service --write-model state`. If you leave the flag out,
the new service takes the first service's answer.

**The last two questions are for a project that starts from a document.**

- If you give the requirements document, the command copies it in as `docs/prd.md` before the first commit.
- If you give the folder that contains the document instead (with `slipwai generate --brief <dir>`), the
  command finds the document in the folder by its name or its first heading. Everything else in the folder
  goes under `docs/design/`, and the mock-up stage follows it. The command prints what it decided, so you
  can see a wrong guess.

Usually, you press Enter for both questions. You then write the specification with the agent, as on
[the next page](first-feature.md).

The command writes every answer in `project.json`. Nothing else keeps a second copy. The Makefile,
`docker-compose.yml`, the CI workflow and the gate scripts all read that one file.

### The same interview, on the board

`slipwai` with no arguments opens **the board**. This machine serves the board, and only this machine can
open it. The *Start a project* tab is the same interview as a form, in the same order and with the same
menus. Three things are easier on the board:

- A quickstart fills in the questions below it. Each answer stays yours to change.
- **Dev tooling** has one checkbox for each extension that is installed on this machine. The board gives
  the ticked extensions to `./init`.
- You pick the brief folder with your own machine's file chooser.

A project that starts from a requirements document does not stop at `./init`. The board runs `make draft`.
This writes the first specification from the document, and puts every decision that the document did not
make under `## Assumptions`. The board then stops on the **Voyage** tab, so that you can read the
specification. [Your first feature](first-feature.md#from-the-board) continues from that page.

`slipwai bridge install` keeps the board running. It installs a login service for your own account, and it
does not need root. It also opens the board, so that your browser can put it in your dock.
`slipwai bridge uninstall` removes it again.

## 4. Start the repository

```sh
cd bookings
```

Start your coding agent there. `./init` has already run. The interview runs it at the end, in the project that it has just made, because
nothing in the tree works until `./init` has run. `./init` installs Spec Kit for your coding agent. It also
adds the skills, commands and agent types that the profile needs. It uses the network once, at that point,
and never again.

`slipwai generate --no-init` does not run `./init`, and leaves it as your next step. A scripted `generate`
also does not run it, unless you give `--init`. You can run `./init` again later safely. This is also how
you change the agent: `./init --integration <agent>`.

In the agent, type `/verify`. It runs `make verify`, the whole gate: lint, types, tests, the architecture
checks, the model and the chart. CI runs the same gate. It passes on a repository where nobody has written any
code yet:

```console
> /verify
verify: all gates passed
```

Where something fails, `/verify` names every gate that fails in one run, with the line each printed, and says
what was skipped rather than passed.

**That passing gate is the purpose of the first ten minutes.** The gate is now a fact, not a hope. "Keep the
main branch releasable" only means something when the gate is a fact.

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

`make help` lists every target, with one sentence for each. You do not need to read it yet.

## Next

→ **[Your first feature](first-feature.md)**: a specification, a model, a chart, a slice, and a demo that
you watch.

Other pages: [a second person joins](a-second-person.md) · [let it cruise](let-it-cruise.md) ·
[bring an existing codebase](adopt.md) · [the vocabulary](../../GLOSSARY.md)

Two pages are maps, not steps. [The workflow](the-workflow.md) lists every step from a document to an
accepted capability. [The board](the-board.md) describes every screen and control.

Do you want every step on one page? [The generate runsheet](runsheet-generate.md) is this guide as a
checklist, from installing the command to every release after that.
