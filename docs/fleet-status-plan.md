# The Fleet tab says what is happening, what it needs, and when it moves again

A plan for the combined design agreed on 2026-10-22, drawn as artboard D of the canvas
<https://claude.ai/artifact/XZYqPMtXaztPD9qXSYsy8e> ("Fleet status mockups"). The design was taken from one
real day: the `recap` voyage of 2026-10-21, whose logs are the fixture every slice below is checked against.

**Status, 2026-10-22:** slices 19.1 to 19.13 are built on the `fleet-status` branch, one commit each, with `tests/test_recap_day.py` and `tests/test_timeline.py` holding the board to the day. Section 5's open points stand.

## 1. What went wrong, in the words of the logs

At 14:58 and again at 17:40 the harness answered a dispatched session with one line:

```
{"type":"result","subtype":"success","is_error":true,"result":"You've hit your session limit · resets 9:40pm (Europe/London)"}
```

`harness.Session` turns that into exit code 1. `captain.watched` reports "`/sail` exited 1".
`captain.through_its_gate` counts it as a run that missed its gate and runs the slice again; the second
and third runs take under a second each and say the same thing; `attempts` is spent and `captain.finished`
writes `parked` with `why: "LB3: \`/sail\` exited 1. That was the last of 3 run(s)…"`. Eight slices parked
this way in three minutes. The limit reset at 21:40 and nothing in the fleet knows that time exists, so the
parks stood until a person cleared them. A restart at 09:00 the next day lit two captains, each read the
standing parks, found nothing it may start, printed one line and exited in under a second. The catch-up
captain was not lit at all, because its whole-fairway park from 14:59 had no `cleared` receipt.

Three slices (LB6, LB7, LB8) parked for a real reason — a change only a person can land on `main` — and
each wrote it as a 900-character paragraph. The board showed eleven rows under *Waiting on you*, eight of
them saying "exited 1", and no row saying which process was alive.

The three complaints the design answers:

1. **Is anything happening?** The board does not show the processes, their exit reasons, or a timeline.
2. **What does it actually need?** A park is prose. Eleven parks were three causes.
3. **Why would I tell it something?** A limit is not a question, and nothing should wait on a person for it.

## 2. The decisions

**D1. A limit refusal is a park with a `cause` of `limit` and an `until`, and it spends no attempt.** Not a
new kind: `parked` already owes a `cleared` receipt, `open_parks` and `fleet.parked` already read it, and
`waiting: green-trunk` is the precedent for a park the harbourmaster clears by itself
(`harbourmaster.cleared_for_green`). The board calls such a park *paused*, because nobody is asked anything.

**D2. A park is a record.** `parked` gains four optional fields: `cause` from a closed set, `until` (an
instant), `needs` (a list of `{what, by, check?}`) and `then` (one sentence). `why` stays, for the reader and
for every old line. A park with no `cause` is drawn as `other` and read exactly as today.

**D3. The harbourmaster ticks needs it can check.** A need may carry a `check` of two kinds in this plan:
`{"kind":"text","path":"…","has":"…"}` and `{"kind":"make","target":"…"}`. Both run against trunk's checkout
on the harbourmaster's pass, never in a berth. A need with `by: person` and no `check` is ticked only by a
person. When every need of a park is met the harbourmaster writes the `cleared` receipt itself.

**D4. Parks are grouped by cause and needs on the board**, and the group has the one button. Eight limit
parks are one row with a time on it. Three parks on the same host change are one checklist.

**D5. Processes are read from `.slipwai/running`**, which `fleet.start` already writes, plus one new file
per captain saying why it exited. The board stores nothing; it reads what the process wrote when it left.

**D6. The timeline is a fold of the deck and harbour logs**, served as JSON for a window the page asks
for, drawn as a scrollable track with a scale the person picks. Row names stay fixed. No money anywhere on
the tab: tokens are shown where the logs record them, cost is not computed.

**D7. One fixture: recap's day.** The three logs from 2026-10-21 (`library.jsonl`, `catch-up.jsonl`,
`vol_rmt_l07721.jsonl`, 70 KB together) are copied into `tests/fixtures/recap-day/` with paths and names
kept. Every slice adds an assertion against them. A design drawn from one day is tested against that day.

## 3. The slices

Each is one pull request, sized S (a session), M (a day) or L (two to three days). Order matters: 19.1 to
19.4 stop the bleeding and could ship alone; 19.5 to 19.8 make the needs real; 19.9 to 19.12 are the page.

| Slice | What lands | Size | Status |
|---|---|---|---|
| 19.1 | The park record in the log schema | S | done |
| 19.2 | The harness reads what the refusal said | S | done |
| 19.3 | The captain pauses on a limit instead of spending attempts | M | partial: no paragraph in `commands/sail.md` saying a limit is paused, not retried |
| 19.4 | The harbourmaster clears a park whose time has come, and the fleet says "paused until" | S | partial: `fleet list` does not say paused |
| 19.5 | A session's own park is a record | S | partial: written in `drive-captain.md`, not `sail.md`; no LB6 five-need example; no test that it parses |
| 19.6 | The harbourmaster ticks needs against trunk | M | partial: no tests for two needs met one at a time, a failing `make` target, or no rerun per commit |
| 19.7 | The board folds parks into groups with a cause | M | done |
| 19.8 | Processes on the board, with why each one left | M | partial: harbourmaster writes no `.exit` file |
| 19.9 | The Fleet tab: headline, processes, needs | L | partial: no Questions card; Streams and Last lines not under `<details>`; no tile or decision test |
| 19.10 | The timeline fold and its endpoint | M | partial: `/timeline.json` ignores `from`/`to`; no lit/exited marks |
| 19.11 | The timeline on the page: scroll and scale | M | partial: the page never asks `/timeline.json`; the published copy has no scale select |
| 19.12 | Paused in clearance, the work columns, the terminal and the agent inbox | S | partial: `mcp.py` inbox lists parks, not groups |
| 19.13 | Words, mockup, catch-up notes | S | partial: no pause paragraph in `cruise.md` or `where-are-we.md`; no 19.11 changelog fragment |

### 19.1 The park record in the log schema — S

`src/slipwai/logs.py` is the source; `make shared` renders `assets/toolkit/scripts/agents/logs.py` and
`make check-shared` refuses drift. Both land in one commit.

- `DECK_KINDS["parked"]` stays `("fairway", "why")`. Add `OPTIONAL: dict[str, tuple[str, ...]]` beside it:
  `{"parked": ("slice", "waiting", "cause", "until", "needs", "then")}`. `slice` and `waiting` are already
  written and read; naming them closes a gap rather than opening one.
- `CLOSED["parked"] = {"cause": CAUSES}` with
  `CAUSES = ("limit", "host", "question", "demo", "gate", "silence", "exit", "ceiling", "trunk", "budget", "other")`.
  `limit`: the harness refused the run. `host`: a change on trunk only a person may make. `question`: an
  open `question` line. `demo`: sent back. `gate`: a mark not set. `silence`: ended for writing nothing.
  `exit`: `/sail` exited non-zero for any other reason. `ceiling`, `trunk`, `budget` name the three
  existing self-clearing or policy parks.
- `until` is checked as an instant in the log's own format (`%Y-%m-%dT%H:%M:%SZ`) on the way in and out.
- `needs` is a list; each item `{"what": str, "by": "person"|"fleet", "check": {...}?, "path": str?}`.
  `check.kind` is closed: `("text", "make")`. A malformed `needs` makes the line `Unreadable`, as any other
  field outside its shape does.
- `HARBOUR_KINDS` gains `"need-met": ("fairway", "parked", "need", "how")` for 19.6.
- `open_parks`, `fairway_parks`, `held_slices` unchanged. Add `paused(parks, now) -> list[Entry]`: the open
  parks with `cause == "limit"` or an `until` in the future, which is the one question three later slices ask.
- Tests: `tests/test_logs.py` round-trips a full record and refuses a bad `cause`, a bad `until`, a `check`
  of an unknown kind. The recap fixture's lines, which carry none of the new fields, still read.

### 19.2 The harness reads what the refusal said — S

`assets/toolkit/scripts/agents/harness.py`. `Ending.read` already keeps `outcome` and `erred` from the
`result` event. It keeps the `result` text too, and `Session` exposes `refusal`.

- `Ending.said: str` — the last `result` event's `result` string, or `""`.
- `refusal(text: str, now: datetime) -> tuple[str, str] | None`: `("limit", until_iso)` for the session-limit
  message, parsing "resets 9:40pm (Europe/London)" with `zoneinfo`, choosing today or tomorrow by which is
  next after `now`, rounded up to the minute; `("limit", now + 15 min)` for a rate-limit or overloaded
  answer (`429`, "overloaded", "rate limit") where no time is given; `None` for everything else. The message
  formats are the harness's and may change: an unparsable time falls back to `now + 60 min`, and the fallback
  is said in the park's `why` so a reader knows the time was guessed.
- `Session.refusal` is `refusal(self.ending.said, now)` once the session has ended, else `None`.
- Tests: a fake session that prints three stream-json lines, the last the recap `result` line verbatim, and
  the parsed `until`; the two fallbacks; a normal success is `None`.

### 19.3 The captain pauses on a limit instead of spending attempts — M

`assets/toolkit/scripts/agents/captain.py`.

- `dispatch` returns the refusal with its tuple (a fourth value, or a small dataclass replacing the tuple:
  the tuple is already `(finished, why, fresh)` and a fourth member is one more place to get the order wrong).
- `through_its_gate`: on a refusal, return at once with `cause="limit"`, `until`, and a `why` of the form
  "the harness refused the run: <said>. Paused until <until local>; no attempt spent". `tried` is not
  incremented. The function's return grows to carry the record fields; `finished` writes them.
- `finished` passes `cause`, `until`, `needs`, `then` through to `logs.entry("parked", …)`. The parks the
  captain writes today each get a `cause`: `gate_missed` → `gate`/`demo`/`silence`/`exit`, the open-question
  park → `question`, the ceiling park → `ceiling`, `resolve: false` → `trunk`.
- The turn's end: where every slice this captain could carry on is paused, print
  `captain: <fairway> is paused until HH:MM — <said>` and exit. Add `" is paused until "` to `STOPS`.
- Before dispatching a slice whose newest open park is paused with `until` ahead, skip it with one line,
  so a captain relit early does not burn a refusal per slice.
- `commands/sail.md`: one paragraph under the retry rules, saying a limit is paused, not retried.
- Tests in `tests/test_captain_gate.py` with a `fake_drive` variant that prints the recap `result` line and
  exits 1: one park, `cause: limit`, `until` set, no second run, the exit line says paused. An existing gate
  miss still retries up to `attempts`.

### 19.4 The harbourmaster clears a park whose time has come, and the fleet says "paused until" — S

- `harbourmaster.cleared_by_time(already)`: for every open park with `until <= now`, a `cleared` receipt
  with `what: "the time it waited for came: <until>"`. Called in `once()` after `cleared_for_green`.
  `fill_free_berths` then relights the fairway on the same pass, because `fleet.parked` no longer finds an
  open park. The pass interval is `HEARTBEAT = 15.0`, so a resume lands within fifteen seconds of the time.
- `fleet.relight` and `fleet.parked`: a fairway whose newest open park is paused prints
  `<fairway>: paused until HH:MM, so not lit` rather than `parked, so not lit`, and `fleet list` says it.
- A person's `told` still clears a paused park early (`told_after_parks` unchanged); the next refusal
  re-parks it with the harness's new `until`, which costs one free request and one line.
- Tests: `tests/test_harbourmaster.py` with an `until` in the past writes the receipt once and not twice;
  `tests/test_fleet_start.py` reads the new line.

### 19.5 A session's own park is a record — S

A session under `/sail` appends its own `parked` line when it stops for the host (LB6's paragraph). The
instructions live in `assets/toolkit/commands/sail.md`; there is no writer script to change.

- The park section of `sail.md` says: write `cause`, one of the closed set; `needs`, one item per thing that
  has to change, each with `what` (one sentence, the path in it), `by`, and a `check` where one of the two
  kinds can tell; `then`, one sentence on what the fleet does once the needs are met; `why`, still, as the
  one paragraph a reader without the board sees.
- The example in the page is LB6's park rewritten as a record: five needs, two `text` checks against
  `docs/event-model/model.yaml` and `specs/…/chart.yaml`, one `make check-model`, two `by: person`.
- The skipper's path (`captain.skipper_round`) and the bosun's are untouched: they answer `question` lines.
- Tests: `tests/test_skills.py` already checks the command pages for retired words; add a check that the
  park example parses through `logs.read`.

### 19.6 The harbourmaster ticks needs against trunk — M

- `harbourmaster.needs_met(already)`: for every open park with `needs`, evaluate each unmet need's `check`
  against the trunk checkout the harbourmaster already keeps for merges (`SCRATCH`, advanced to trunk's tip
  with the merge's own `advance`). `text`: the file at `path` contains `has`. `make`: the target exits 0,
  run with the merge gate's environment and a bound of `wait_bound` minutes, at most once per trunk commit
  per need. A met need writes `need-met` with `how` (the commit it was seen at). Receipts already written
  are read back so a need is ticked once.
- A park whose needs are all met, none of them `by: person` without a receipt, gets its `cleared` receipt
  with `what: "every need landed on trunk at <commit>"`.
- A person ticks a `by: person` need from the board: `/tell` aimed at the slice with the message
  `need <n> done: <what>`; `told_after_parks` is unchanged and the board reads the tick from the `told`.
  This is the smallest thing that works; a `need-done` deck kind is a later slice if the `told` reads badly.
- Tests: a park with two `text` needs against a temp checkout, one met; the receipt appears when the second
  lands; a `make` need against a Makefile with a passing and a failing target; nothing runs twice per commit.

### 19.7 The board folds parks into groups with a cause — M

`src/slipwai/fleet.py`.

- `inbox()` rows of kind `parked` carry `cause`, `until`, `needs` (each with `met: yes|no` from `need-met`
  receipts and person ticks), `then`, `slice`.
- `groups(inbox_rows) -> list[dict]`: parks with the same `cause` and the same `needs` (compared by `what`)
  are one group: `cause`, `slices` in park order, `needs` with the union of met flags, `then` (the newest),
  `until` (the latest), `t` (the earliest), `kind: "group"`. Told and question rows are not grouped.
- `Fairway.paused` and `state_of` → `"paused"` where the stream's newest open park is paused; `STATES` in
  `bridge_page` gets `"paused": "paused"`. `berths` rows gain `paused: int` and `parked: int`.
- `board()` gains `"groups"` and `"counts"`: slots in use of `boilers`, paused, parked on you, blocked,
  not started, merged — the numbers under the headline.
- Tests in `tests/test_board.py` against the recap fixture: 11 open parks, 2 groups once 19.3's cause is
  applied to the fixture's limit parks by a fixture-only rewrite (the fixture keeps the old lines too, so an
  ungrouped `other` park is also asserted).

### 19.8 Processes on the board, with why each one left — M

- Captain: on exit, write `.slipwai/running/captain-<fairway>.exit` as JSON `{at, why, code}`, `why` being
  the `STOPS` line it printed. Harbourmaster writes the same on a clean exit. `fleet.start` deletes the
  `.exit` when it starts the process again. Ignored by git (`.slipwai/running/` already is).
- `src/slipwai/fleet.py`: `processes(root, config) -> list[dict]`: one row per `*.pid` and per charted
  fairway with none — `name`, `role` (harbourmaster, captain), `fairway`, `state` (`running`, `exited`,
  `not lit`), `since` (pid file mtime), `why` (the `.exit` or, for a fairway never lit, `fleet.parked`'s
  reason or "paused until"), `starts_when` (one sentence: "a park is cleared", "the pause ends at HH:MM",
  "LB5 sets AudioFetched", "—"). `starts_when` for an exited captain comes from the clearance query the
  board already runs: the first `blocked` reason for the fairway's next slice.
- `voyage.fleet_running` stays; the processes list is what the Fleet tab's strip and `slipwai fleet` print.
- Tests: `tests/test_fleet.py` with pid files for a live pid and a dead one, an `.exit` file, a fairway with
  no pid; Windows is covered by `alive`'s existing branch.

### 19.9 The Fleet tab: headline, processes, needs — L

`src/slipwai/voyage_page.py`, `bridge_page.py`, `bridge.py`.

- A new `fleet_page.py` module renders the tab from `board()` (the tier is `page_shell`'s); `live_cards`
  keeps serving the published read-only copy until 19.11 replaces it there too.
- **Headline**: one sentence from the counts and groups. Paused with a time: "Paused. The harness refused
  the fleet at HH:MM; it resumes itself at HH:MM, in Nh Mm." Parked on a person: "Stopped. N slices wait on
  you for M things." Working: "N slices working in M slots." Nothing lit and nothing parked: "Nothing is lit.
  N slices wait on marks nobody has set." The dot colour follows: blue, gold, teal, grey.
- **Process strip**: four tiles from `processes()`, state chip, what it is doing, starts when.
- **Counts line** from `board()["counts"]`.
- **Needs you**: one card per group in cause order (`host`, `question`, `demo`, `gate`, `exit`, `silence`,
  then `ceiling`/`trunk`/`budget`, with `limit` groups shown in the headline, not here), each with: chip of the
  cause, title from the newest park's first sentence, meta (asked by whom, when, holds which slices), progress
  bar of met needs, the needs as a checklist with the check that ticks each one, the `then` line, and the
  buttons. Buttons post what the bridge already has: **Landed** → `/tell` to each slice in the group with
  the message "landed: <title>"; **Resume now anyway** → `/tell` to each paused slice; **Open D32** → the
  decision log anchor; **I have read all N** → `/read`. No new POST route.
- **Questions** card says "None open" when it is, with the count the skipper decided today.
- **Each park, in one line** table at the bottom from the ungrouped rows.
- The Streams table and Last lines move under a `<details>` at the foot: still there, no longer first.
- Tests in `tests/test_voyage.py`: the recap fixture renders the headline sentence, four process tiles, two
  need groups, nine decisions, the one-line table; the published copy renders with nothing to press.

### 19.10 The timeline fold and its endpoint — M

- `src/slipwai/timeline.py`: `spans(found: list[Fairway], harbour, since, until) -> dict`: per fairway, per
  slice, a run span from `claimed` (or the first line naming the slice after a `cleared`) to the next
  `parked`/`merged`/`stopped` naming it; a park span from the park to its receipt or `until` or now, with its
  `cause`; harbour `cleared` whose `what` came from a person's `told` as a `person` mark; parks with
  `cause: limit` as `limit` marks at their `t`; `fleet` `.exit` files and pid mtimes as `lit`/`exited` marks.
  Rows: run spans of one fairway are packed into `boilers` rows by first fit; park spans of slices held on
  a person go in a `parked on you` row per fairway; a whole-fairway park is its own thin span.
- `GET /timeline.json?from=<iso>&to=<iso>` on the bridge, controls only; the published copy embeds the
  fold for the voyage so far at publish time.
- Tests: the recap fixture yields two limit marks, two person marks, the three-slot packing of 16:43 to
  17:40, CU1's park span from 14:59 to the fixture's end.

### 19.11 The timeline on the page: scroll and scale — M

- A card on the Fleet tab: a fixed 130 px names column and a horizontally scrolling track whose width is
  `span / scale`; a `<select>` of 4, 8, 24 hours and "whole voyage"; hour ticks by scale (1h, 1h, 2h, 4h),
  date on the midnight tick; the future shaded from now; a `now` mark; the `until` marks for pauses.
  In-bar labels hide at 24 hours and wider. The chosen scale is remembered in `localStorage` like the theme.
  The track scrolls to `now` on load.
- Colours from the page's tokens: teal run, brass park, a blue pause (`#d6e6f8` on `#1d4f8f` dashed in
  light; the dark pair is added to `page_shell.THEME`), critical red for a limit mark.
- The page asks `/timeline.json` for the window and redraws on scale change; the published copy draws the
  embedded fold with the select working on it.
- Tests: the markup for the fixture holds the row names, the marks, the select; the published copy has no
  fetch.

### 19.12 Paused in clearance, the work columns, the terminal and the agent inbox — S

- `clearance.py`: `STATES` gains `"paused"` before `"awaiting-decision"`; the two park reasons at the
  `awaiting-decision` branch return `paused` with "its pause ends at HH:MM" where `logs.paused` says so.
- `voyage.folded`: a paused slice sits in *Queued* with the chip `Paused · resumes HH:MM`, never in
  *Waiting on you*. `voyage_page.chip_of` draws it.
- `cli_fleet`: the first line becomes the headline sentence; "waiting on you: N" counts parked-on-person
  only; a `processes` block. `mcp.py`'s inbox returns the groups, not the parks.
- Tests: `test_clearance.py`, `test_voyage.py`, `test_fleet.py` one case each.

### 19.13 Words, mockup, catch-up notes — S

- `docs/slipwai-2-plan.md` section 1 gains **Pause** ("a park with a time on it, which the harbourmaster
  clears itself; nobody is asked anything") and **Need** ("one thing a park waits for, ticked by a check or
  a person"); `make glossary`.
- The agreed artboard is saved as `docs/mockups/fleet-tab.html`, beside `ledger-bridge.html`, with a line
  in its head naming the canvas it came from.
- `commands/cruise.md` and `commands/where-are-we.md`: the paragraph on parks says what a pause is and that
  `/cruise-tell` still clears one early.
- Each slice carries its `changelog.d/` fragment. The catch-up line for 19.1 to 19.6 is `slipwai upgrade`,
  which carries the toolkit scripts; for 19.7 onward the board is the keel's and needs nothing.

## 4. What is checked at the end

`make verify` on the rebased branch of each slice, and once at the end a replay: `slipwai fleet` and the
Voyage page against `tests/fixtures/recap-day/` at three instants, 14:59, 18:05 and 09:02 the next day,
each asserting the headline sentence, the process tiles, the groups and the timeline marks. The 18:05 one
is artboard D.

## 5. Open

- The reset-time format is the harness's. A second harness answers a limit differently; `refusal` is a
  table per harness key in `registry.json` when a second one is wired, not before.
- Whether a person's tick of a need is a `told` for long. It reads oddly in the log ("need 3 done: …") but
  needs no schema change; revisit after one real voyage.
- `make` checks run on the harbourmaster's trunk checkout and cost what the target costs. A target that
  takes minutes is bounded by `wait_bound`; whether a project may list a target at all is `harbour.json`'s
  `checks` allow-list, decided in 19.6.
