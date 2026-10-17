# Fresh native captain acceptance (12.5)

This record reports a real, fresh captain session against candidate `14dbccc`. It was not a simulated
delegate and not a Python delivery loop. The fixture is `/private/tmp/native-captain-proof`. The fixture is
disposable. It has no remote, no cloud target, no forge credential and no production data.

## Fixture and scope

The fixture was generated from this candidate with the pinned toy language package:

```sh
PYTHONPATH=src SLIPWAI_LANGUAGES=packages python3 -m slipwai generate native-captain-proof \
  --profile standard --backend toy-plain --frontend none --target none \
  --output /private/tmp --skip-checks
cd /private/tmp/native-captain-proof
./init --integration codex --non-interactive
```

`project.json` declares the service `apps/service`, the framework `toy-plain` and the target `none`.

Bootstrap commit `7417c69` committed these before the captain's claim: the chart, the typed JSON Schema, the
specification, the examples, the plan, and the immutable fixture checks. The checks add real Python
unittest, Ruff and strict mypy commands to the generated toy placeholders. The placeholders themselves
prove no implementation behaviour.

The chart `specs/arrival/chart.yaml` declares the fairway NAT, the slice NAT-01 and the capability
`label-arrival`. The slice sets the schema mark `ArrivalLabel` and consumes no marks. The schema is a
non-empty JSON string. The slice does three things with an incoming label:

- It trims the label.
- It keeps the case and the inner spacing.
- It raises `ValueError("arrival label is blank")` for blank input.

## Observed captain work

The fresh collaboration session read `agents/drive-captain.md`, the generated `commands/sail.md`, trunk and
the logs. No Python captain, cruise, sail or fleet loop ran. Python helpers only read state, took the Git
claim and appended individual log entries.

- `make check-chart` passed. `python3 scripts/agents/clearance.py NAT-01` reported the slice as cleared.
- The captain acquired the claim `refs/slipwai/claims/NAT` at `b387a3b` before the first slice edit.
- The captain appended `claimed`, `mark-set` and heartbeats. It used `logs.entry`, `O_APPEND` and one
  `os.write` for each line. The fixture deck log is `.slipwai/logs/arrival/NAT.jsonl`.
- Tasks and implementation ran in the captain's host context. They used the documented fallback for an
  unavailable harness. The stage file records the model, the context and the reason.
- For trim, the RED step was an observed assertion failure against the identity function. For blank
  validation, the two RED steps were observed assertion failures against the trim-only function. Both came
  before their implementation. Each GREEN step passed unit tests, lint and strict types.
- Fresh convergence later required a validating, immutable `ArrivalLabel(str)` domain value. Its
  direct-constructor rejection tests also failed before the validation moved into the constructor.
- Five tests now cover both rules, the constructor and the public domain result type.
- At every completed boundary, `python3 scripts/agents/inbox.py NAT` reported no unread messages, no overdue
  waits and no unreviewed decisions. The controlled paths were compared against the bootstrap commit, and
  they had not changed. `harbour.json` sets a 60-second wait bound.

The first full fixture gate found that the bootstrap constitution was incomplete. Its required principles
were ratified from `check-constitution.py --requirements`. The gate itself did not change. The
harbourmaster cherry-picked the repair, which changed only the constitution setup, onto fixture main as
`7b00dcf`. The captain rebased, and the repair is not part of the product slice diff. Nobody edited a
controlled gate. The record of the first setup failure stays.

## Native delegate attempts

The installed Codex CLI v0.152.1 ran with `exec --sandbox read-only`, no model override, and a brief to
read `agents/sail-review-mate.md`. It reached service start-up but returned HTTP 400. Its configured model,
`gpt-6.1-sol`, is not supported for this ChatGPT account. This is a failed live attempt. It is not a
completed review.

Claude Code was also installed. A fresh convergence call with its default model was rejected by the
automatic approval review before the process ran. The reason was that the call would send source and
specifications to that external service without explicit permission for that destination. The captain did
not bypass the rejected call and did not retry it.

Fresh convergence used two real, independent collaboration contexts:

- The first context found a HIGH domain-type conflict and a MEDIUM missing plan compliance check. Both were
  closed.
- The second context returned converged.

A fresh gaps delegate found that the public result type was not pinned. It was closed with
`assertIsInstance`. The captain demonstrated the public callable and appended `demo: accepted`. This is
evidence of the slice's behaviour. It is not a person's acceptance of the capability.

Fresh review found a P2 issue: a missing Given/When/Then description of the acceptance boundary. The captain
closed it by documenting the existing public operation and its two outcomes. The reviewer independently
passed five tests. The reviewer found no other material defect in implementation, reuse, simplification or
ownership. The refactor pass kept the validation in the constructor, and kept the public helper as the
driving port.

The fresh adversary passed five tests and 580 additional actor-input cases, with no material finding. The
fresh mutation delegate ran the retained harness. It independently checked the successful baseline and the
error handling. It reported the tool's own line `mutation: 5/5 killed (100%)`, exit 0, real 0.05 seconds.
These were five targeted in-memory mutants. This is not exhaustive mutation coverage.

The rebased fixture's `make verify` passed with exit 0 at source `176c382`. The captain verified a clean
tree, and verified that the controlled paths matched fixture main `7b00dcf`. Then, at
`2026-10-12T12:58:08Z`, it appended the request `native-NAT-01-merge` and stopped dispatching. The request
asks only for the local fixture merge. It does not ask for a push, a deployment, a publication or a flag
action. The real NAT claim stayed held while the captain waited for the outcome.

The harbourmaster merged fixture trunk to `d9a5770`, and wrote the grant at `2026-10-12T12:59:14Z`. This was
66 seconds after the request: six seconds more than the 60-second silence bound. At `2026-10-12T12:59:54Z`,
the captain recorded a park, kept the claim, and requested the matching clearance. This run proves the
explicit overrun-and-park path. It does not prove exact deadline scheduling. The harbourmaster cleared that
original park at `2026-10-12T13:00:19Z`. The captain folded the receipt, and at `13:00:59Z` wrote `merged`
with the real trunk commit.

At the same timestamp, the captain requested local log durability. The harbourmaster used the real
`travel.push_log` to create `refs/slipwai/logs/NAT` at `17513355`. It granted local durability at
`13:01:43Z`, which is within the wait bound. The persisted deck log holds the complete end of the log,
including `merged` and the durability request. After the grant, the captain released its local claim at
`35650aba`.

The captain first used a wrong path for `git show`. Because of this, the captain's own byte-for-byte check
happened just after the release. The correct snapshot path is `.slipwai/logs/arrival/NAT.jsonl`. The real
snapshot and the grant both came before the release. But this record does not claim that the captain's
independent comparison came before the release.

No remote exists, so durability is local only. No forge publication, push or cloud action happened. A
request never proves a merge. Only two things together can prove a merge: a harbourmaster grant that names
trunk's commit, and the captain's `merged` line after it.

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

The retained fixture and the ignored deck log are local evidence. This document does not claim that the
temporary path is an installed product. It does not claim that platform CI ran.
