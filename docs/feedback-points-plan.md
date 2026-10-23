# Feedback points: what a person can judge, and what delaying it costs

A plan for phase 20, drawn from one real voyage: `recap` on 2026-10-21 and 2026-10-22, whose logs, chart,
`try-it.json` files and Try it state are the fixture every slice below is checked against. Fifteen slices
merged in two days and the person who opened Try it saw a starter page, three links and no data, and said
so twice in `docs/feedback/`.

**The principle the plan serves:** a person wants to see the product early and often, because each thing
they can judge is a point where they can say *that's wrong* or *I wanted something else*, and the earlier
that is said the less it costs. A merge is an engineering event: trunk took the slice. A feedback point is a
product event: a person can observe something, and what they say could change what gets built next. The two
sometimes coincide and must never be assumed to. Feedback has a cost of delay: every slice built on an
unjudged assumption before a person sees it is a slice that may be revisited, and some commitments — a mark
set at a plan, the first reader of it merged, a flag hoisted — make the change far dearer after than before.
So the measure of the loop is how much avoidable rework a person was given the chance to prevent, and how
early; every rule below is judged by that.

## 1. What went wrong, in the words of the logs

**Nothing seeded.** `.slipwai/try-it/state.json` at 18:29 on the 22nd: `seeded: []`, `seed_failed` 22 entries.
Every catch-up story died at its first call with `401 {"error":"unauthenticated"}`; every library story with
`no fixture user ada in docker/keycloak/realms`. The catch-up routes bind a resolver that refuses every token
because the slices could not add a JWT library — `package.json` is a shared surface — and each of CU1, CU3,
CU4, CU7, CU8, CU10 and CU15 wrote *"this step records 401"* into its own story and merged. LB3 had built a
working userinfo adapter without a dependency; LB3's told of 11:01 said wiring the catch-up routes to it was
one line at the composition root. Nobody owned the line. The library stories sign in as `ada` and `ines`,
people the plan stage invented for the quickstart; the realm holds one user, and the realm is under
`docker/`, which a slice may not write. `ladder.py`'s `TRY_STORY` tells a slice to use *"a fixture user"*
and *"the quickstart's synthetic people"* in one sentence and nothing checks that those are the same people.
The same text says a refused seed *"is fixed here"*; no gate holds it.

**The screens that exist cannot be reached.** `apps/recap-web/src/App.tsx` mounts eight routes; the nav links
three. Player, voice, catch-up and ask sit under `/books/:bookId/...` and the two screens that would
link to them — LB12 *See the library* and LB13 *See now playing* — are rows 17 and 19 of 34 in the chart.
Feedback 0001 (*"I dont seem to see the catch up part, only upload"*) and 0002 (*"nothing past Add a book"*)
were triaged `planned` and changed nothing.

**The captains built the edges first.** `clearance.cleared` waits on every mark in `steers_by`, and
`chart.py` writes `steers_by` as every event in the slice's `reads`. A `state-view` folds many events, so
LB12 steers by fifteen marks and LB13 by ten; CU5 *Generate the recap* by ten; PR1 *Start preparation* by
two, one of which — `AudioFetched` — is set by LB5, which steers by LB4, which sat parked. The preparation
captain exited four times with *"nothing to start"*. The slices that steer by nothing all ran: decline,
rate, ask, report, settings, stop, enter a position — each writing an event nothing reads yet. PR1's `reads`
means *either* an import or a fetch; the captain read it as *both*.

**Hand-backs were notes.** 59 `told` lines; the ones that gate everything — a JWT library, fixture users,
direct-access grants, the one-line wiring, flag lines in `.env.example` — were written on the 21st and 22nd.
`bridge_page.py` files `told` under *Notes: nothing here blocks a stream; Done clears one.* One landed on
main (`.gitignore`). Each later slice asked again and shipped a stub, and the stub is what Try it shows.

**The demo waits for the capability.** Under `release: flagged` the hand walks a capability when its last
slice merges. `capabilities.py` reads one whole: report-a-spoiler, one slice. CU3, LB2, LB8 and LB11 each
logged *"no demo line, by the ladder's rule"*. So the card's *Merged so far* shows quickstart steps, mostly
curl commands against routes that answer 401, and the person has had nothing to react to for two days.

**Ninety-eight decisions, none judged.** `decisions.md` holds 98 entries: 84 `Decided by: host` (the stage's
recommendation, taken under `decide: recommended-first`), 12 by the skipper delegate, 2 by a human; 41 at
`Confidence: medium`, each with a *Would reverse if* a person could have answered in a minute with the thing
in front of them. Nothing observable shipped, so not one of them has been judged, and every merged slice
reads them as settled. `BookImported` has nine steerers and `ListeningResumed` six; the moment any of those
merge, D-entries about a book's shape stop being cheap to change.

Three complaints the plan answers:

1. **I can't see anything.** Merged work is dark: unseeded, unreachable, or both.
2. **The interesting slices come last.** The order and the clearance rule both push views and engines to the end.
3. **The thing it needed from me was never put to me.** Dependencies and fixtures were notes, not needs.

## 2. The decisions

**D1. A feedback point is an observable, not a merge and not a capability.** An observable is the first
thing a person — or an external system a person can inspect — can judge: a screen, a read model under the
API, an automation's side effect (a server updated, a file gone, an alert raised, a message sent), an
outbound translation. In the model those are the `state-view`, `automation` and outbound `translation`
slices, read with their `actor`; a `state-change` is observable only through one of them, so building it
without its reader buys no feedback. Screens are usually the most impactful observables early and some
products have none; the rule is the same for a read model answered over HTTP or a row that appears in
another system. The capability keeps its readings — converge, gaps, design review, adversary, mutation, the
hand's browser walk — because `capability_gates.py` is right that those only make sense over the whole, and
the person's demo *stop* stays per capability. Try it follows trunk (D8) so that whatever is observable is
reachable at any time; which observables are worth a person's attention, and when, is D6's.

**D2. A seed that fails is a stop at the Demo rung, in every mode.** A slice with a `try-it.json` writes a
`seeded` deck line — the records its story made, against which service, at which commit — and the captain
holds the slice to it the way it holds a slice to its `mark-set` lines: a stage that wrote no `seeded` line
made no progress, and parks with `cause: gate`. Under `/sail` the session runs the seed itself at the same
rung and reads the same answer. *"One the service refuses is fixed here"* becomes true because it is
checked.

**D3. The people a story signs in as are the feature's to declare, additively.** `specs/<feature>/people/`
joins the cumulative artifacts a slice may write (`spec.md`, `contracts/`, `decisions.md`…): one JSON file
per person. `try_it.people()` reads them beside the realm's users; the throwaway sign-in server Try it
already edits creates the ones the realm lacks, and a berth asks the same of its own. `make check-try`
refuses an `as` that names nobody, statically, in `make verify`. The realm file stays the host's.

**D4. A story may be given its inputs.** `try-it.json` gains `given`: events to append to named streams
before the steps run, for marks the slice steers by whose setters are not built. They go through the
service's own seed door — `make seed-<service> FILE=…`, which the language package provides and which
appends through the event-store port with a deterministic id, so a replay records nothing twice — never
through an HTTP route. `make check-try` validates each given event against `model.yaml#<Event>`, so a
story cannot give what the model does not type. The card marks such records *given, not made*, so a person
knows the upstream is not built and what they are looking at is the slice, seeded to a state.

**D5. `reads` is any-of, and a given mark does not block.** On the event profile every mark is typed in
`model.yaml` before any slice runs, which is what a mark being set is *for*. So a `state-view` or
`automation` has clearance when at least one mark it steers by is set, and a mark its story gives is not
waited on at all. `check-model`'s rule that a `reads` names an event an earlier slice produces stands: the
model's order still has to be buildable. `translation` and `state-change` are unchanged.

**D6. Feedback points are ranked by what delaying them costs, and the order is proposed from the ranking.**
For each observable (D1), four terms, each read off an artifact the project already has and printed with
its source so a person can disagree with a number:

- *Uncertainty* — what the observable would let a person judge: the `decisions.md` entries `Written to`
  the artifacts it depends on that were `Decided by` the host or the skipper rather than a human, weighted
  by `Confidence` (medium counts more than high, low more than medium); `parked` mock states on its
  surface; clarifications answered with the recommended option. A decision a human took counts nothing.
- *Blast radius* — the slices not yet merged that steer by the marks those decisions were written to, the
  transitive walk `abreast.critical` already does. Each one built before the feedback arrives is one that
  may be revisited, and a mark is set once.
- *Urgency* — a commitment point ahead of it: a sibling about to set one of those marks at its plan, the
  first reader of one about to merge, a flag about to hoist. Past the point the term drops, because the
  cost has been paid.
- *Cost to surface* — the slices still needed to make it observable, counting a `given` (D4) as cheap and
  a producer slice as dear, plus a screen to style, a flag to turn on, an external stub to run.

Cost of delay is the first three together; the score is cost of delay over cost to surface — the shape of
weighted-shortest-job-first, applied to information rather than features. `clearance.py --feedback` prints
the observables in that order with every term. The split proposes its order from it: the walking skeleton
— the first write and the observable that shows it — then observables by score, each with the givens that
let it go before its producers, then the producers in the order the observables need them. `--order` says
where a cleared observable with a higher score sits below rows that add nothing observable. The ready set
is unchanged: it already takes rows in split order, so a better order is a better ready set.

**D7. A hand-back that names a shared surface is a need.** `told` gains an optional `needs` list in the
shape a park's needs already have (`what`, `by`, `check`). The harbourmaster ticks them against trunk
exactly as it ticks a park's; the Fleet and bridge pages group them under *Waiting on you* by need, not
under *Notes*; *Done* is not offered on one until its needs are met. A slice that ships a stub around the
need still ships, and the need stays open on the board, attached to the slice, until it lands — and the
card says which needs keep a merged slice dark.

**D8. Try it follows trunk and the hand is handed it.** After a merge the harbourmaster refreshes a running
Try it (`try_it.py refresh`, keeping data, loading the new slice's story); under `/sail` the merge rung does
the same. The demo stop's *"the thing the actor uses"* is `make try`'s URL with the capability's links; the
hand's brief carries the same. Nothing starts a second app for a demo where Try it is already up.

**D9. The card tells the truth and takes feedback.** *New since the last update* lists only slices whose
story seeded; a merged slice whose story failed is under *Merged but dark* with the need that darkens it
(D7) or the step that refused. Every link carries the slice, the person signed in as and trunk's commit into
the feedback capture, so what a person types lands with its context.

**D10. One fixture: recap's second day.** `chart.yaml`, `model.yaml`, the thirteen `try-it.json` files, the
realm file, `.slipwai/try-it/state.json` and the three deck logs from 2026-10-22 go into
`tests/fixtures/recap-try/`. Every slice below adds an assertion against them: that LB12 clears at row 17
under D5, that the order under D6 names the dark run, that the 22 failures become 2 needs under D7.

## 3. The slices

Each is one commit on a branch, sized S (a session), M (a day) or L (two to three days). Order matters:
20.1 to 20.4 stop the bleeding — a seed is checked, people exist, a failure is a stop — and could ship
alone; 20.5 to 20.7 bring the middle forward; 20.8 to 20.10 put it in front of a person.

| Slice | What lands | Size | Status |
|---|---|---|---|
| 20.1 | `make check-try`: every story parses, every `as` names somebody, every `open` path is mounted | S | done |
| 20.2 | People under `specs/<feature>/people/`, created in the sign-in server | M | done |
| 20.3 | The `seeded` deck line, and the Demo rung's seed as a gate in both modes | M | partial: no test of the `seeded` line `try_it.py seed --slice` writes |
| 20.4 | Hand-backs carry needs: `told` with `needs`, ticked and grouped | M | done |
| 20.5 | `given` in a story, the seed door, and the schema check | L | partial: `seed.ts` is the TypeScript package's, not here; no CU5 test with three given events |
| 20.6 | Clearance: `reads` any-of, a given mark does not block | M | partial: `check-chart` does not check `pattern`; the LB5 case is not on recap's chart |
| 20.7 | `clearance.py --feedback`: observables ranked by cost of delay, and the order proposed from it | L | partial: the chart does not record `seen_through`; the Voyage card is untested |
| 20.8 | Try it follows trunk; the demo stop and the hand are handed it | S | done |
| 20.9 | The card: new, dark, and feedback with context | M | partial: dark rows carry no needs; no test over recap's `state.json` |
| 20.10 | Words, ladder text, catch-up notes | S | partial: no paragraph in `docs/whats-new.md` |

### 20.1 `make check-try` — S

`src/slipwai/check_try.py`, rendered into the toolkit as `scripts/check-try.py` the way the other gates
are, and a `check-try` target in `agent_targets.py` that `verify` runs. No app, no Docker: it reads files.

- Every `specs/*/slices/*/try-it.json` is JSON of the shape `TRY_STORY` describes; a malformed one is named.
- Every `as` (the story's and each step's) names a person: a user of a realm under `docker/keycloak/realms/`
  with a password credential, or — from 20.2 — a file under `specs/<feature>/people/`. The refusal prints
  the names it knows.
- Every `open[].path` starts with a route the browser app mounts, read from the web app's route table the
  way `try_it.flag_keys` reads its flags (`WEB_FLAG_CALLS` has the one reader per framework; this adds a
  `WEB_ROUTE_CALLS` beside it, `path="…"` in a `<Route>`). A story with no browser app skips the check.
- Where 20.5 has landed, every `given[]` event validates against `model.yaml#<Event>`.
- Tests: `tests/test_check_try.py` over the recap fixture: thirteen stories, two unknown people (`ada`,
  `ines`), the exact names it should print; a story whose `open` names `/books/nw-1/player` passes against
  recap's `App.tsx`.

**Catch-up:** `slipwai migrate` brings the gate and the `verify` line. A project whose stories already name
people nobody declared goes red at `check-try` on the first `make verify` after the merge, and the refusal
prints the names: write each under `specs/<feature>/people/` (20.2) and run `make verify` again. Never
soften the gate; the next migration brings it back.

### 20.2 People under `specs/<feature>/people/` — M

`assets/toolkit/scripts/agents/try_it.py` and `src/slipwai/project/ladder.py`.

- `people(where)` returns realm users first, then one per `specs/<feature>/people/*.json`:
  `{"username", "name", "password", "realm", "roles"?, "email"?}`. A file whose username a realm already has
  is a duplicate and `check-try` refuses it.
- `sign_in_server(where, env)` already holds an admin token for the throwaway Keycloak. After it moves the
  clients it creates every declared person the realm lacks (`POST /admin/realms/{realm}/users`, enabled,
  email verified, the password credential), and reports how many it made.
- A new verb, `try_it.py people --apply`, does the same against whichever Keycloak the environment names,
  for a berth: the Demo rung runs it before `seed --slice`.
- `TRY_STORY` says: *`as` names a person under `specs/<feature>/people/` or in the local realm; a story that
  needs someone new writes their file beside it.* `sail.md`'s shared-surface rule lists `people/` with the
  cumulative artifacts.
- Tests: the realm fixture plus two people files; `people()` lists three; the admin calls are recorded by a
  fake server and the two missing users are created once; a second run creates none.

**Catch-up:** `slipwai migrate` brings `try_it.py` and the ladder; a project runs `make agents`. Stories
that name people nobody declared fail `check-try` until the files are written — which is the point.

### 20.3 The `seeded` deck line, and the seed as a gate — M

`src/slipwai/logs.py` (rendered to the toolkit by `make shared`), `captain.py`, `ladder.py`, `sail.md`.

- `DECK_KINDS["seeded"] = ("fairway", "slice", "records", "commit")`, optional `("given", "api")`. One
  per story that ran green from a berth. `records` is the count of steps that answered.
- `try_it.py seed --slice <id> --api <url>` writes the line when every step answers, through `logs.entry`,
  the way a stage writes `mark-set`; it writes nothing on a refusal and exits 1 as today.
- The Demo rung (`ladder.py`, after `TRY_STORY`): *run `try_it.py people --apply` then `seed --slice <id>
  --api …` against the app this berth runs; a refused step is fixed here, and the slice does not reach the
  review rung until the `seeded` line is written.* Same words under `/sail` and `/cruise`.
- `captain.through_its_gate`: a slice that has a `try-it.json` and whose turn wrote no `seeded` line parks
  with `cause: gate`, `needs: [{"what": "the story in slices/<id>/try-it.json seeds green", "by": "fleet",
  "check": {"kind": "make", "target": "check-try"}}]` — the static part is tickable; the live part is the
  next run's.
- Tests: `tests/test_captain_gate.py` gains a turn that wrote `mark-set` and no `seeded` and parks; a turn
  that wrote both passes. `tests/test_try_it.py` holds the line's fields.

**Catch-up:** `make shared` output and `captain.py` come with `slipwai upgrade`; a project runs `make
agents`. A slice in flight at the upgrade owes a `seeded` line at its next turn.

### 20.4 Hand-backs carry needs — M

`src/slipwai/logs.py`, `harbourmaster.py`, `fleet.py`, `fleet_page.py`, `bridge_page.py`, `sail.md`.

- `OPTIONAL["told"] = ("slice", "needs")`, `needs` held to the park's shape (`what`, `by`, `check`), the same
  validator. `logs.py tell --need '<what>' [--check text:<path>:<has> | make:<target>]`.
- `harbourmaster.needs_met` walks told lines with needs beside parks: a `need-met` receipt keyed by the
  told's `t`, and a `cleared`-shaped receipt `told-met` when all are met. The agent inbox drops a told whose
  needs are met.
- `fleet.py`'s groups: a told with needs joins the park groups under its first need, with its slice; the
  headline counts it under *waiting on you*. `bridge_page.py` lists it under *Needs*, not *Notes*, and shows
  *Done* only once met; a person may tick a `by: person` need from the row, as they tick a park's.
- `sail.md`, shared-surface rule: *under `/cruise` a need the host must meet is a `told` with `needs`, one
  per item, with a `check` wherever trunk can prove it landed — a dependency is
  `text:<manifest>:"<package>"`, a realm user is `text:<realm file>:"<username>"`, a flag line is
  `text:.env.example:<KEY>=`.* `sail-slice-watch.md` and `drive-captain.md` carry the same sentence.
- Tests: the recap day's 59 told lines read unchanged; one rewritten with needs is grouped and ticked when a
  fixture trunk gains the line; the Fleet headline says *2 things waiting on you* where it said 0.

**Catch-up:** `slipwai upgrade` carries the scripts; `make agents` the briefs. Old told lines stay notes.

### 20.5 `given` in a story, the seed door, and the schema check — L

`try_it.py`, `check_try.py`, the TypeScript language package (its service skeleton), `ladder.py`.

- Story shape: `"given": [{"stream": "book-nw-1", "event": "BookImported", "data": {…}}]`, appended in order
  before `steps`. `check-try` validates `data` against `docs/event-model/model.yaml#<event>` with the
  JSON Schema the chart's `marks` already point at, and refuses a `given` naming an event the chart has no
  mark for, or one this slice itself sets.
- The seed door: the service skeleton gains `scripts/seed.ts` (`npm run seed -- <file>`) and the Makefile a
  `seed-<service>` target. It opens the event store the same way `main.ts` does, appends each event at the
  stream's current version with `eventId` = a hash of (stream, event, data), and records nothing for an id
  already on the stream. It needs the durable store: with no `DATABASE_URL` it says so and exits 2, which
  `check-try` cannot see and the Demo rung must.
- `try_it.seed` runs the door once per service with the union of every story's `given` (one file, in
  story order) before the first step, in the Try it workspace and — under `--slice --api` — in the berth,
  which has `make services-up`. A refused `given` fails that story the way a refused step does.
- The card and `state.json`: `links[]` gains `given: true` on a link whose story gave anything; the Demo
  rung's record names what was given.
- `TRY_STORY`: *a mark this slice steers by whose setter has not merged is given, not waited for — the
  events the story needs, in the model's shape; a story that gives nothing and steers by an unset mark
  cannot seed, and says why in `plan.md`.*
- Tests: a fake service whose seed door writes to a JSON file; the recap fixture's CU5-shaped story with
  three given events seeds; one with a misspelled field is refused by `check-try` naming the schema path.

**Catch-up:** the door comes with the TypeScript package's next release (`slipwai language upgrade`); until
then a story's `given` is validated and not applied, and the seed says *no seed door yet* — which is a need
(20.4) on the language package, not on the project. The standard profile has no `given` in this plan; a
story on it that carries one is refused by `check-try` with that sentence.

### 20.6 Clearance: `reads` any-of, a given mark does not block — M

`clearance.py`, `chart.py`, `sail.md`'s *It has clearance* paragraph.

- `chart.py` carries each slice's `pattern` onto the chart (`"pattern": "state-view"`), beside `steers_by`;
  `check-chart` holds it to the model.
- `clearance.cleared`: for `state-view` and `automation`, `waiting` is every mark in `steers_by` minus those
  set, and the slice is cleared when `waiting` is shorter than `steers_by` — at least one set — or when
  every waiting mark is given by the slice's story (read off `specs/<feature>/slices/<id>/try-it.json`,
  which the preparation band writes first; a story not yet written gives nothing). For `state-change` and
  `translation` the rule is unchanged. The sentence it prints says which marks are *set*, *given* and
  *unset*, so a reader sees why the slice may start.
- `order_reasons` and `position` print the same words; `abreast.ready` changes nothing — it calls `position`.
- `sail.md`: *a view or an automation steers by many marks and folds whatever exists; it has clearance when
  one is set, and its story gives the rest.*
- Tests: against the recap chart, LB12 is cleared once `BookImported` is set (it was, on the 21st); PR1 is
  cleared on `BookImported` alone; CU5 is cleared when its story gives `ChapterTranscribed` and
  `ChapterIndexed`; LB5 (`translation`) still waits on `ServerBookAdded`.

**Catch-up:** nothing to write; `make chart` regenerates the chart with `pattern` on it, and `check-chart`
asks for that regeneration once.

### 20.7 `clearance.py --feedback`: observables ranked by cost of delay — L

`clearance.py`, `chart.py`, `src/slipwai/decision_log.py` (the entry parser `make decisions` already has),
`story-splitting/SKILL.md`, the split's `## Order` template.

- `chart.py` carries each slice's `pattern` and `actor` onto the chart and marks the observables: a
  `state-view`, an `automation`, a `translation` whose actor is an external system. A `state-change`'s
  observable is the nearest observable downstream of a mark it sets; the chart records it as `seen_through`.
- `decision_log.py` reads each entry's `Decided by`, `Confidence`, `Slice`, `Written to` and `Status`
  (`check-decisions` already holds the shape). A new `feedback.py` under `scripts/agents/` joins them:
  for each observable, the decisions written to its slice, its marks' schemas or its surface's mock states;
  the not-yet-merged steerers of those marks; the next commitment point from the deck logs (a sibling
  planning, a merge granted, a flag hoisted); and the slices between the chart's cleared set and the
  observable, with a `given` in its story counting one and a producer counting the producer's own distance.
- `clearance.py --feedback` prints one row per observable: the score, the four terms, and under each the
  decisions, marks and slices it was read from. A term read from nothing prints as such, never as zero
  silently. The same words go to the Fleet tab's voyage view as the next three feedback points.
- `--order` keeps the three clauses and adds *seen through*, and after the rows says where a cleared
  observable scores above the rows placed over it.
- The skill's held-to rules: rule 3 becomes *the walking skeleton goes first: the first write and the
  observable that shows it*; a new rule 4, *observables in `--feedback` order, each before its producers
  where its story can give what they would set, and a producer only as early as the observable that needs
  it*. The `## Order` table gains `Seen through` and `Feedback score`.
- Tests: over the recap fixture, the row for LB12 names its decisions and its nine unmerged steerers; CU5
  scores above every catch-up state-change because its decisions on the window, the gradient and the check
  are the most numerous at medium confidence and `RecapGenerated` has four steerers; CU15 scores last with
  nothing steering by `SpoilerReported`. The fixture's ranking is written down once in the test and held.

**Catch-up:** a project's existing order is not rewritten; `--feedback` and `--order` say what the next
`/story-splitting` would propose and the person decides. Under `/cruise` with `decide: recommended-first`
the next split run records the reorder as a decision, citing the scores.

### 20.8 Try it follows trunk; the demo stop and the hand are handed it — S

`harbourmaster.py`, `ladder.py`'s merge rung, `demo_stop.py`, `cruise_hand.py`, `sail-demo-hand.md`.

- After a `granted` merge lands, the harbourmaster runs `try_it.py refresh` where `state.json` says Try it
  is `ready` (and nothing where it is stopped — a person starts it). The refresh keeps data and seeds the
  new slice's story, as it does today.
- The merge rung under `/sail` says `make try-update` in the same breath as the push.
- `demo_stop.py`'s *It ends with the thing the actor uses*: where Try it is running, the URL is Try it's and
  the links are the capability's `links[]` from `state.json`; the hand's brief (`cruise_hand.py`) hands the
  same, and `sail-demo-hand.md` says to walk there rather than start an app of its own where one is up.
- Tests: a fake `granted` line followed by a fake `state.json` at `ready` runs the refresh verb once; at
  `stopped`, never.

**Catch-up:** `slipwai migrate` brings the harbourmaster and the ladder text; `make agents` projects the
hand's brief. A Try it already running keeps its data; `make try-update` moves it to trunk once by hand.

### 20.9 The card: new, dark, and feedback with context — M

`try_card.py`, `try_it.py` (`whats_new`, `state.json`), `bridge.py`'s feedback capture.

- `whats_new` keeps the slices whose story is in `seeded`; the rest of the new slices go to a `dark` list
  with their `seed_failed` entry and — from 20.4 — the open needs attached to the slice.
- `new_html`: *New to try · N* lists seeded slices, each with its links first and its quickstart steps under
  a disclosure; *Merged but dark · M* lists the rest, each with one line: the step that refused and what it
  said, or the need that keeps it dark, with the Fleet tab's tick where it is a person's.
- Every link on the card carries `?slice=<id>&as=<username>&trunk=<commit>`-shaped context into the app's
  tab, and the feedback box on the card is pre-filled with the same `CONTEXT` fields `feedback.py` reads,
  so a message typed after clicking a link lands with its slice.
- The headline's *N refused* becomes *N dark*, with the first reason.
- Tests: `tests/test_try_card.py` over the recap `state.json`: 0 new, 4 dark, the LB1 row says *no fixture
  user ines*; after 20.2 and 20.4 are applied to the fixture, 2 dark with a need each.

**Catch-up:** nothing in the project; the card is the keel's and reads `state.json` as it stands. A card on
an older `state.json` with no `seeded` list shows every new slice as dark until the next `make try-update`.

### 20.10 Words, ladder text, catch-up notes — S

- `GLOSSARY.md` (through the plan's vocabulary table): **Observable** — the first thing a person or an
  inspectable external system can judge: a screen, a read model, an automation's side effect, an outbound
  translation; **Feedback point** — an observable a person is asked to judge, placed by what delaying the
  judgement would cost; **Given** — a record a story appends through the
  seed door because its setter is not built; **Seeded** — the deck line that says a story ran green.
- `ladder.py`'s Demo rung re-read as a whole so it says one thing: examples proven by tests, people declared,
  the story seeded green, the `seeded` line written, then review. `capability_gates.py`'s docstring gains
  the sentence that distinguishes the *showing* (per slice) from the *readings* (per capability).
- `changelog.d/20-*.md`, one per slice, each with its catch-up paragraph; `docs/whats-new.md` the one
  paragraph for a person.

## 4. What this plan does not do

- It does not make every merge a feedback point, and it does not move the hand's browser walk or the
  capability's readings to the slice. Try it following trunk keeps every observable reachable; D6 says which
  ones a person is asked to look at and when. The seed is a check that the story works, not a demo.
- It does not add a dev-only HTTP seeding route. The seed door is a process with the store's credentials,
  never a route the app serves.
- It does not fix `recap`. The three edits that would light it today are the project's: wire the catch-up
  routes to the userinfo adapter, add `ada` and `ines`, rebase LB4. Under this plan the first two would have
  been a need on the board on the 21st and a refused seed at CU1's Demo rung.

## 5. Open points

1. **A berth on the in-memory store.** `given` needs the durable store, so the Demo rung's seed check needs
   `make services-up` in the berth. The alternative — an in-process door the service opens on loopback when
   a seed flag is set — is faster and is the thing the bosun's list calls catastrophic in production code.
   The plan takes the slower path; say if the berth's Postgres is a cost worth avoiding.
2. **Any-of and schema drift.** A view cleared on one mark builds against the model's schema for the rest.
   A setter that later changes an event's shape at its plan stage breaks that view's fold. The events
   module is additive by rule and `check-model` refuses an implemented slice naming an event absent from the
   source, which catches it at the setter's merge rather than the view's. Whether that is early enough is a
   voyage's evidence away.
3. **The standard profile.** `given` is defined for events. A CRUD service's story would give rows, and
   nothing here types a row. Left until a standard-profile voyage shows the same dark run; tracked as
   [#36](https://github.com/ROBCOATVG/slipwai/issues/36).
4. **The weights.** Medium confidence over high, a given over a producer, a commitment point's multiplier:
   the first numbers are guesses printed beside their terms so they can be argued with. Three voyages'
   rankings against what the person actually changed will say whether they are the right guesses.
5. **Feedback that is not a voyage's.** Cost of delay is computed from the chart and the decision log; it
   does not know that the market, a partner or a launch date makes one observable urgent. That is the
   product order the split already asks as a question, and the ranking is its evidence, not its answer.
