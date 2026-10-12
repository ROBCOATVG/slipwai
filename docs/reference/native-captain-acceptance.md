# Fresh native captain acceptance (12.5)

This record reports an actual fresh captain session against candidate `14dbccc`, not a
simulated delegate or Python delivery loop. Fixture: `/private/tmp/native-captain-proof`.
The fixture is disposable and has no remote, cloud target, forge credential, or production data.

## Fixture and scope

Generated from this candidate with the pinned toy language package:

```sh
PYTHONPATH=src SLIPWAI_LANGUAGES=packages python3 -m slipwai generate native-captain-proof \
  --profile standard --backend toy-plain --frontend none --target none \
  --output /private/tmp --skip-checks
cd /private/tmp/native-captain-proof
./init --integration codex --non-interactive
```

`project.json` declares service `apps/service`, framework `toy-plain`, target `none`.
Bootstrap `7417c69` committed the chart, typed JSON Schema, specification, examples,
plan and immutable fixture checks before the captain's claim. The checks add actual
Python unittest, Ruff and strict mypy commands to the generated toy placeholders.
The placeholders themselves prove no implementation behavior.

Chart `specs/arrival/chart.yaml` declares fairway NAT, slice NAT-01 and capability
`label-arrival`; it sets schema mark `ArrivalLabel` and consumes no marks. The schema
is a nonempty JSON string. The slice trims incoming labels, preserves case and inner
spacing, and raises `ValueError("arrival label is blank")` for blank input.

## Observed captain work

The fresh collaboration session read `agents/drive-captain.md`, generated `commands/sail.md`,
trunk and the logs. No Python captain, cruise, sail or fleet loop was invoked.
Python helpers only read state, take the Git claim and append individual log entries.

- `make check-chart` passed; `python3 scripts/agents/clearance.py NAT-01` reported cleared.
- Claim `refs/slipwai/claims/NAT` at `b387a3b` was acquired before the first slice edit.
- The captain appended `claimed`, `mark-set` and heartbeats using `logs.entry`, `O_APPEND`
  and one `os.write` per line. The fixture deck is `.slipwai/logs/arrival/NAT.jsonl`.
- Tasks and implementation ran in the captain's host context using the documented
  unavailable-harness fallback. The stage file records the model, context and reason.
- Trim's RED was an observed assertion failure against the identity function. Blank
  validation's two REDs were observed assertion failures against the trim-only function.
  Both preceded their implementation. Each GREEN passed unit, lint and strict types.
  Fresh convergence later required a validating immutable `ArrivalLabel(str)` domain value;
  its direct-constructor rejection tests also failed before validation was moved there.
  Five tests now cover both rules, the constructor and the public domain result type.
- `python3 scripts/agents/inbox.py NAT` reported no unread messages, overdue waits or
  unreviewed decisions at every completed boundary. Controlled paths were compared
  against bootstrap and remained unchanged. `harbour.json` sets a 60-second wait bound.

The first full fixture gate found the bootstrap constitution incomplete. Its required
principles were ratified from `check-constitution.py --requirements`; the gate itself
was unchanged. The harbourmaster cherry-picked the constitution-only setup repair onto fixture main as
`7b00dcf`. The captain rebased and the repair is excluded from the product slice diff.
No controlled gate was edited; the initial setup failure remains recorded.

## Native delegate attempts

Actual installed Codex CLI v0.152.1 was invoked with `exec --sandbox read-only`, no
model override, and a brief to read `agents/sail-review-mate.md`. It reached service
startup but returned HTTP 400: its configured `gpt-6.1-sol` model is unsupported for
this ChatGPT account. This is a failed live attempt, not a completed review.

Installed Claude Code was also available. A fresh convergence call using its default
model was rejected by automatic approval review before process execution because it
would send source/specifications to that external service without explicit destination
authorization. The captain did not bypass or retry that rejected call.

Fresh convergence used two actual independent collaboration contexts. The first found
a HIGH domain-type conflict and MEDIUM missing plan compliance check. Both were closed;
the second returned converged. A fresh gaps delegate found unpinned public result typing,
closed with `assertIsInstance`. The captain demonstrated the public callable and appended
`demo: accepted`; this is slice behavior evidence, not a person’s capability acceptance.

Fresh review found a P2 missing Given/When/Then acceptance boundary description;
the captain closed it by documenting the existing public operation and its two outcomes.
The reviewer independently passed five tests and found no other material implementation,
reuse, simplification or ownership defects. The refactor pass kept validation in the
constructor and the public helper as the driving port.

The fresh adversary passed five tests and 580 additional actor-input cases without a
material finding. The fresh mutation delegate ran the retained harness, independently
checked the successful baseline and error handling, and reported the tool's own line
`mutation: 5/5 killed (100%)`, exit 0, real 0.05 seconds. This is five targeted
in-memory mutants, not exhaustive mutation coverage.

Rebased fixture `make verify` passed with exit 0 at source `176c382`. The captain
verified a clean tree and controlled paths matching fixture main `7b00dcf`, then
appended request `native-NAT-01-merge` at `2026-10-12T12:58:08Z` and stopped
dispatching. The request asks only for the local fixture merge, never push, deployment,
publication or flag action. The real NAT claim remained held while awaiting the outcome.

The harbourmaster actually merged fixture trunk to `d9a5770` and wrote the grant
at `2026-10-12T12:59:14Z`. This was 66 seconds after the request, exceeding the
60-second silence bound by six seconds. The captain recorded a park at
`2026-10-12T12:59:54Z`, retained the claim, and requested matching clearance.
This run proves the explicit overrun/park path; it does not prove exact deadline
scheduling. The harbourmaster cleared that original park at `2026-10-12T13:00:19Z`; the captain
folded it and wrote `merged` with the actual trunk commit at `13:00:59Z`.

The captain requested local log durability at the same timestamp. The harbourmaster
used actual `travel.push_log` to create `refs/slipwai/logs/NAT` at `17513355` and
granted local durability at `13:01:43Z`, within the wait bound. The persisted deck
contains the complete suffix, including `merged` and the durability request. The
captain released its local claim at `35650aba` after the grant. A wrong first
`git show` path caused the captain's own byte-for-byte verification to happen just
after release; the correct snapshot path is `.slipwai/logs/arrival/NAT.jsonl`.
The actual snapshot and grant predate release, but this record does not claim the
captain’s independent comparison preceded it. No remote exists: durability is
local-only, and no forge publication, push or cloud action occurred. No request proves a merge; only a harbourmaster grant naming
trunk's commit and the captain's subsequent `merged` line can prove that.

## Recheck the retained fixture

```sh
cd /private/tmp/native-captain-proof
git show -s --format='%H %s' refs/slipwai/claims/NAT
python3 scripts/agents/clearance.py NAT-01
python3 scripts/agents/inbox.py NAT
make check-chart
git diff main -- apps/service specs/arrival contracts/schemas/ArrivalLabel.json
git diff --exit-code main -- Makefile scripts tools .github/workflows .gitea/workflows
PATH=/Users/lukegee/Documents/dev/slipwai_v2_Fork/.python-tools/bin:$PATH \
PYTHONPATH=/Users/lukegee/Documents/dev/slipwai_v2_Fork/.python-tools \
PYTHONDONTWRITEBYTECODE=1 make unit lint typecheck
PYTHONDONTWRITEBYTECODE=1 python3 specs/arrival/slices/NAT-01/mutation_harness.py
```

The retained fixture and ignored deck log are local evidence; this document makes no
claim that the temporary path is an installed product or that platform CI ran.
