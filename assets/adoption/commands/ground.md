---
description: Ask the person what the tree cannot say — one question per row of the convergence map — and record each answer with its provenance
argument-hint: [axis ...]
---

# Ground

This repository adopted the delivery method around code that was already here. `{{convergence-page}}` says where it stands
on each ladder a generated project sits at the top of. The survey placed every row it could from a file, and the
rows it could not are `unrecorded` — a question, not a default. This command is that question set, asked by you
of the person, one row at a time, with the answers written where the record keeps them. Two ways in, one question
set: run it on its own after `./init` and before the first slice, or let `/sail` run it — its Ground stage is this
command, for the axes the slice touches, and the ladder continues once the rows are placed. `$ARGUMENTS` names the
axes to ask about; empty means every row a person has not yet placed.

## The rules

- **One question at a time.** Ask, wait, write, confirm what was written, then the next. Never a questionnaire
  (`skills/find-gaps/SKILL.md` has the discipline).
- **Evidence and rungs first.** Before asking, show the row as it stands — the evidence the survey found and each
  rung's meaning — so the person places themselves on a ladder rather than answering a quiz.
- **Settle from the tree whatever the tree settles, and say you did.** A question you can answer by reading a
  file is not a question to put: read it, say what you found and where, and record it. Ask only what reading
  cannot reach — what a person intends, what they would ship on, what they know about how the work is done. A
  menu offered for something the tree already states asks somebody to guess at their own repository.
- **Ask how much to explain, first, and hold to the answer.** The opening question is not about this
  repository: it is whether they want each answer's consequence spelled out — what it writes, what moves,
  what it costs — or the short form. Somebody who knows this codebase and this method does not need to be
  told what webpack does, and being told anyway is how a question set becomes a wall to skim; somebody
  meeting either for the first time cannot answer safely without it. Offer both, say which you would pick
  for them and why, and take the answer as standing for the rest of the run unless they change it — which
  they may, at any question, in either direction.
- **In full, every answer on offer says what it does.** The person reads the options, not the paragraph above
  them, so each one names what it writes, what moves because of it, and what it costs. *`library`, and the
  gate holds its lint: `make verify` runs `npm run lint` here from now on, and a red one stops every change
  until it is fixed or quarantined* is an answer. *Yes — hold its lint* is a label, and a label is what gets
  picked by somebody who does not yet know what they are picking. Where two options differ only in a word,
  say what turns on that word. Never offer one whose consequence you have not stated: if you cannot say what
  an answer does, you are not ready to ask it.
- **In short, the labels stand alone — and two things never go.** The short form drops the elaboration, not
  the honesty: what you think and why, from what you read, stays (the next rule), and *I don't know* stays an
  answer on offer. What a short answer costs is a sentence away whenever they ask, and offering that once —
  *say the word and I will spell any of these out* — costs a line.
- **Say what you think, and why, from what you read.** A recommendation with its reasoning is what makes an
  answer a confirmation rather than a guess, and it is what lets somebody disagree with you on the evidence
  rather than on authority. Never a bare menu.
- **"I don't know" is one of the answers, every time, and offered as one.** It is the honest state of most
  rows in most repositories on the first pass, and a question that does not offer it is a question that
  manufactures an answer.
- **A rung is claimed only from a fact.** Here the person is the fact for what only they can know (how work is
  integrated, whether they would ship on the tests). Where the tree can contradict a rung — a release path, a
  quarantined suite, a template constitution, an application's role, no accepted ADR — the tree wins:
  `make check-convergence` fails the row, so say that instead of recording it.
- **"I don't know" stays `unrecorded`,** and is said so in the row's evidence. It is not filled in from context.
- **`detected` is the tree's reading, not the person's answer.** A row the survey placed from a file is asked
  about like an `unrecorded` one the first time; only `confirmed` and `overridden` mean a person has spoken.
- **A row a person already placed** (`confirmed`, `overridden`) is asked about again only if `$ARGUMENTS` names
  its axis; never moved silently.
- **Record, do not paraphrase.** `rung`, `provenance` `confirmed`, `evidence` in the person's own words, and
  `planned` where they name the slice that will move it. Where the answer is a fact under another key — the
  release path, an application's `kind`, a home, `why` — write it there with `confirmed` provenance; the row
  follows when `/survey` re-reads the record.

## The first question

Asked before anything about this repository, once, and answered for the rest of the run:

**Ask:** how much should each answer explain itself? *Long* spells out, for every option, what it writes to
the record, what moves because of it, and what it costs — which is what somebody meeting this repository or
this method for the first time needs in order to answer safely. *Short* gives you the reading, the
recommendation and the answers as labels, on the understanding that you already know what confirming an
application or placing a rung does. Say which you would pick for this person and why, from what you can see:
a repository whose record is entirely `unrecorded` and whose person has not met the method suggests long; a
second or third adoption by the same hands suggests short.

Then say, once: *say the word at any question and I will spell that one out* — and mean it, in either
direction, at any point.

**Write:** nothing. It is how you talk, not a fact about the repository, and it is not a row.

<!-- section: candidates -->
## What is an application here

Asked first, and before any row: until one of these is confirmed there is nothing for the rows to be
about, and `{{make}} verify` refuses rather than passing over nothing. `adopt` recorded them and
wrapped none of them, because which of them the gate should hold is a question the code answers and a
terminal cannot ask.

   The directories the survey found that build:

{{candidate-rows}}

**Where they asked for the long form, say what the word means before the first candidate** — once,
in your own words, and in the terms of this repository. *Application* here is not "something that
gets deployed": it is a directory whose build this gate holds, and a library or a test suite can be one.
Confirming one means, and the person is agreeing to all of it:

   - its recorded `lint`, `typecheck` and `test` join `{{make}} verify`, which every change has to
     pass — the person's, `/sail`'s and `/cruise`'s. Findings already there are recorded as the baseline
     on the first run and only new ones fail, but a red test suite stops the gate until it is fixed or
     quarantined on purpose with `{{make}} ratchet-tighten`;
   - the gate's own CI workflow runs that `verify` on every push to the main branch and every pull
     request, on the runtime the application's toolchain names — so what its lint and tests need to run,
     CI needs too, and a red one is a red check on the pull request;
   - `/sail` and `/cruise` can plan changes to it, and will not change it until somebody has recorded
     the command that starts it and proves it answers (`smoke`, asked at the end of this command);
   - it is named on the map, the structure page and the architecture view, as what this repository is.

   Declining records nothing: the code stays, agents still read it, its own CI keeps running, and the
   delivery gate says nothing about it — `/survey` goes on listing it as a directory that builds with no
   record. Leaving it a candidate is *not yet decided*, and it is asked again. Say too that neither a
   confirm nor a decline can be taken back by a command today, short of reverting the commit that
   recorded it — so where the person is unsure, leaving it is the answer that keeps every door open.

**Ask, one at a time, having read the directory first:** is this an application the gate should hold —
or is it an asset bundle, a test suite for something else here, a sample, a vendored dependency? Say
which you think it is *and why, from what you read*, before asking; the person is confirming your
reading, not answering a quiz. Where it is one: what should it be called (the directory's name is what
the record proposes, and `default` or `ui` is rarely what anybody calls it), what does it own in a
sentence or two, and are the commands the survey read the ones that matter?

Where they asked for the long form, each answer says what confirming it does: which commands join
the gate and what running them needs, what a red one would stop, and what declining forfeits
instead. *Held as a `library` for its lint — `make verify` gains `npm run lint` here, which needs
only Node* and *declined — its lint stays in the repository's own CI, which already runs it, and
the delivery gate says nothing about this directory* are answers somebody can choose between. *Yes*
and *No* are not. Where they asked for the short form, the labels stand alone and your reading above
them carries the reasoning.

{{rung-question}}**Write:** one `slipwai adopt --confirm <name>` per application — with `--as <name>=<new>` where the
directory's name is not its name, and `--kind`, `--purpose` and `--command` for what you established —
and `--decline <name>` for each that is not one. The command builds the record and regenerates
everything that reads it, so never edit `deployables` by hand. A directory you are unsure of stays a
candidate: that is what the state is for, and leaving it is an honest answer where guessing is not.

<!-- end section -->
## The rows, as they stand

{{map}}

## The questions

{{questions}}

## How each application starts

Not a row of the map, and asked before any slice changes code that was here: an application nobody has proved
starts is the floor beside the build, and `/sail`'s Pin stage refuses to change one. The first adoptions each
merged a slice that had stopped the application starting — constructor injection the container could not call —
and no suite saw it, because no suite builds the context.

**Ask:** For each application below — how is it started: the command, the port, what has to be seeded first, the
runtime it needs and the ones it cannot run on? What proves it answers — a URL, a command? Has anyone run it that
way since the method arrived, and did it start?

   The applications that were here:

{{how-each-starts}}

**Write:** what was proven, with the date, in `{{running-page}}` — the repository's own file,
which the `run-the-app` skill points to — including the run that failed and why. Then the one command that starts
the application and proves it answers, exiting non-zero when it does not, as `smoke` under the application's
`commands` in `project.json`, with `provenance.commands` `confirmed`: `make smoke` and the gate's smoke job run it
from then on, `verify` never does. An application nobody can start anywhere but production is a written `null`
with the reason in the same file — never a key left unwritten, which reads as a question still open.

## Then

1. `/survey` (`slipwai adopt --refresh`): the pages follow the record, and the strategy recommendation is
   re-made from what was said. Read the person the map's summary line and the recommendation
   `docs/change-strategy.md` now opens with.
2. `make verify` — `check-convergence` holds every row you wrote to the tree.
3. Commit as one change: what the person said, in the rows and the facts, and the pages that followed.
4. Say which rows are still `unrecorded`, and that `/sail` will ask about each before a slice that touches it.
