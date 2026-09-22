# 0003. The terminal asks what a terminal can answer, and a wrapped application begins as a candidate

Date: 2026-09-22

## Status

Accepted. Two pieces of it are already on `main` and are named below as taken, because they stand on their
own and the evidence for them was not in doubt: `slipwai adopt --next` and the shell-segment fix
(`f68f70b`), and the coding agent established at adoption time rather than asked for by `./init`
(`14d4ba1`). Everything under *Decision* that is not marked *taken* is what this ADR decided.
Brownfield adoption is experimental as [`AGENTS.md`](../../AGENTS.md#versioning-is-not-optional) defines the
word, so the shape this changes may change in a MINOR; this is the exemption being spent deliberately rather
than drifted through.

## Context

`slipwai adopt` on PrestaShop — a real brownfield monorepo, chosen because it is one — asked **thirty
questions**: five candidate directories × (wrap it? / language / kind / keep these commands? / what does it
own?), then the two homes, the forge, the release path, and why the work is happening. Every one was
answered with Enter, which is what a person does when they have no basis to answer otherwise. The result:

- **Four of the five wrapped directories are not applications.** `themes`, `admin-dev/themes/default` and
  `admin-dev/themes/new-theme` are webpack asset bundles; `tests/UI` is a Playwright suite testing something
  else in the tree. `Wrap it as the application …? [Y/n]` defaults to yes, so Enter was the wrong answer four
  times out of five.
- **The names are directory basenames** — `default`, `ui`, `themes`, `new-theme` — and they go into Make
  targets, docs and `project.json` permanently. `default` is the worst available identifier in a repository
  that also has `themes`.
- **`kind` was guessed inconsistently** — `service` for one webpack bundle, `library` for another — and both
  guesses were stamped `confirmed`, the record's strongest provenance, by the same Enter.
- **Every `purpose` came back blank**, because "What does `default` own?" is asked at the moment the person
  knows least, and the adoption page then says *what it is for is not recorded* three times.

The questions are not badly worded. The problem is structural, and it shows up against `generate`:

| | `slipwai generate` | `slipwai adopt` |
|---|---|---|
| Questions | twelve to fourteen | thirty |
| What an answer **is** | a choice — it becomes true because the factory then builds it | a claim about existing code — it can simply be false |
| The authority | the catalog: `axis_applies`, `offered_backends` and `resolve_selection` refuse combinations that do not work | the tree, which the person has not read |
| What a default **means** | a recommendation (`Frontend [react]`) | a guess read off a file (`Kind: service`) |
| A wrong answer costs | `rm -rf` a directory the factory just made | `git reset --hard HEAD^` in the person's own repository, and all thirty again |

Both use the same prompt widgets and the same `[default]` spelling, so a guess and a recommendation are
indistinguishable on screen — and Enter, which means *sure* in one, is recorded as *I confirm this is true*
in the other.

Three further facts settled the shape:

- **There is no undo.** `resurvey.refresh` *reports* a directory that builds and has no record
  (`resurvey.py:171`); it never removes one, and there is no `--unwrap`. A wrong yes is permanent short of
  resetting the commit and starting over.
- **The agent was chosen one step too late.** `./init --integration` asked which harness gets the skills and
  commands *after* `adopt` had asked all thirty — so no agent could help with any of them. Taken in
  `14d4ba1`: `harness.py` establishes it during the adoption, from the environment the run started in or
  from what the tree already reads, recorded with provenance.
- **`/ground` is the right interview in the wrong place.** Its discipline is exactly what these questions
  need — one at a time, evidence and rungs before asking, *I don't know* stays `unrecorded`, the tree wins
  over the person — but it runs after the record is written, and it deliberately does not re-ask a row a
  person has `confirmed` (`ground_command.py:182`). Five wrong Enters are invisible to it by design.

## Decision

1. **A question belongs in the terminal when the survey has the fact and the answer is confirm-or-override;
   it belongs to the coding agent when answering it means reading files that are not on screen.** This is the
   criterion, and it is what the rest follows from. By it, of the ten kinds of question `adopt` asks, one is
   terminal-shaped, one should not be a question at all, one is a person's alone, and seven want the code in
   hand.
2. **The terminal asks the forge, and the harness only where it cannot be established.** Name, delivery
   directory and each candidate's language are *shown* as facts, not asked: the language line was printed
   immediately above the question that asked for it again. A thirty-six-row harness list is not a question a
   terminal has any good way to ask, so where detection cannot say, nothing is recorded and `./init` keeps
   its own question. (*Partly taken*: the harness in `14d4ba1`, the language behind the switch in `f68f70b`.)
3. **A buildable directory the survey finds is recorded as a candidate, not as a deployable.** `deployables`
   starts empty; each candidate is written with the evidence that found it. This is the load-bearing decision:
   the record gains the state it was missing. `unrecorded` already distinguishes *nobody has said* from
   *somebody said this* for every row of the convergence map, and `deployables` had no way to say the same
   thing about an application — which is precisely what five Enters exploited.
4. **`verify` refuses while no application is confirmed**, naming the command that confirms them. A gate
   holding a repository to a record nobody has read is worse than a gate that is not yet running, and the
   refusal is what makes the candidate state honest rather than decorative.
5. **The agent confirms the candidates, in `/ground`, not in a second command.** It opens with them — which
   of these are applications, what is each called, what is it for, which commands matter — and continues into
   the rows it already covers, with *why is this work happening* asked first rather than thirtieth. One
   command, adopt-only: `scaffold.py:112` puts `/ground` inside `if adoption is not None`, a generated project
   never gets it, and nothing here reaches `generate`.
6. **`adopt` is re-runnable**, because the first run no longer has to be right.
7. **`./init` runs from `adopt`** — last, after the commit and never inside it, so an unreachable Spec Kit
   source costs the adoption nothing. (*Taken in `14d4ba1`, as `--init`*; opt-in, because `./init` reaches
   the network and making every `--yes` in a script or a test need connectivity is a poor trade for one line.)
8. **All of it ships behind `--experimental-intro` until it is the default.** The exemption permits changing
   this shape in a MINOR; it does not permit changing it under somebody mid-adoption without warning.
   `experimental.py` is the single predicate, so turning it on by default is deleting that module and its
   callers rather than hunting for conditions it grew.

## Consequences

- **No un-wrap needs building.** Nothing is wrapped until somebody confirms it, so the operation that would
  have had to exist to make a wrong wrap survivable is not needed. This is the whole reason for choosing the
  candidate state over writing everything as `detected` and correcting it afterwards.
- **`--yes` has to mean something new and say it.** It confirms every candidate unlooked-at — the unattended
  path, which is what it is for — and the report says plainly that nobody looked, rather than recording
  thirty `detected` facts that read as if the survey had been checked.
- **A generated project sees none of this.** Its equivalent questions — service name, purpose, bounded
  contexts — are asked by `generate` in the terminal and correctly stay there: they are choices about
  something that does not exist yet, which is the asymmetry this ADR is about, read from the other side.
- **`migrate` carries an adopted repository forward as always.** A record written before the candidate state
  has its applications in `deployables` already, which is confirmation by an earlier factory and is left
  alone; the change writes its catch-up note like any other under the exemption.
- **The report gets shorter and `--next` gets longer.** The wall of `Next:` / `Then:` lines collapses towards
  one instruction, because with `./init` run and the harness known, *run `/ground` in your agent* is a real
  next step rather than one that is two steps away. Where somebody is in the sequence is `adopt --next`'s
  job, derived from the marks each step leaves.
- **What this does not decide:** how the agent should rank a candidate — whether a rubric belongs in
  `/ground` or whether the judgement is left to the agent with the evidence in front of it — and whether
  `deployables` should keep the candidate list after confirmation as a record of what was declined. Both are
  worth answering with a second PrestaShop run as evidence rather than now, and belong on
  [#74](https://git.treyco.dev/ROBCOATVG/volaris-slipwai/issues/74).
