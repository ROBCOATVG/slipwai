# Handover — 2026-10-12

The owner requested a stop to preserve remaining usage, remote preservation of the work, and a resume
prompt. This replaces the earlier handover. **Main has 152 of 169 slices recorded complete.** Unfinished
implementation is pushed to named branches below; it has not been merged just to make the board green.
No 2.0.0 release, tag, PyPI upload, upstream version-2 merge or cloud apply was performed.

## Owner instructions that persist

- Finish the rebuild, divide independent work in parallel, and push reviewed green increments to main.
- The actual 2.0.0 release goes last. Migration, packaging, publication and upstream cutover preparation
  may happen in advance; this explicitly supersedes the earlier prohibition on phase-8 preparation.
- On 2026-10-12 the owner accepted the automated two-clone exercise as final multiplayer acceptance,
  replacing the live second-person/separate-hardware requirement. Retain the explicit seeded interruption,
  elapsed lease and ladder/gate/CI stand-ins; do not describe them as physical hardware or native stages.
- Phase 16 must run alone after overlapping implementation. Phase 9 follows stable behavior.
- Read GLOSSARY.md, AGENTS.md and docs/slipwai-2-plan.md. Chart before claim; fast unit/lint/typecheck
  inside increments; fresh review/refactor and full verification on the final rebased candidate before
  main. Preserve one adversary round and only one further convergence round. No red or incomplete merge.

## Landed and remotely preserved

Core main received foundation/adoption UTF-8 repairs, 15.11 and 15.12, Windows plugin text repair,
multiplayer runtime/WIP/final-publication fixes, 7.11 responsiveness, package snapshot/scaffold repair,
Codex project command skills, read-only distribution preparation, and pinned package source topology.
The latest implementation merge before this handover was **9cc8b14** (PR12); subsequent main commits
record the actual external 15.8 completion and update this document and progress.

TypeScript **15.8 is merged in its own repository**, PR1 at **9143a1a5829721420c3ad2907d5b87df03b1aa52**:
https://github.com/ROBCOATVG/slipwai-language-typescript/pull/1
Versioned memory/SQLite/PostgreSQL state repositories, independent CAS contenders, mandatory event
context, generated native gates and pruning were exercised. Current conformance/state-contract/security
checks passed. HIGH dependency findings were repaired. No TypeScript package version or release changed.
The caller pins workflow, keel and AWS/Azure source topology to **75c053a86817bd12676948f0344f94c451145b62**.

Core PR12 passed its 2,090-test full local gate and Linux/macOS/Windows/documentation CI. Wheels and
executables built and passed smoke tests on all three platforms in read-only run **38253116107**,
against **0178b175a63e7c3df9db0c03f30afa3e2bee1eaa**:
https://github.com/ROBCOATVG/slipwai_v2_Fork/actions/runs/38253116107
This proves that revision, not an arbitrary later release. Initial short-SHA checkout failure was corrected
by dispatching the full SHA. The publisher workflow itself still needs preparation before spending a tag.

AWS/Azure under packages/ are target plug-in sources, holding cloud templates, deployment scripts and
answers behind the target protocol. The keel must not import named cloud packages. They are in this
checkout alongside the toy fixture; they are outside the wheel's src/slipwai package and are not yet
published chandlery target packages. Source-adjacent CI is explicit temporary topology, not a loader bypass.

## Phase position on main

| Phase | Done | Remaining |
|---|---:|---|
| 1 | 6/6 | Complete |
| 2 | 9/9 | Complete |
| 3 | 21/22 | 3.4b skiff/liner WIP |
| 4 | 7/7 | Complete |
| 5 | 29/29 | Complete |
| 6 | 14/14 | Complete |
| 7 | 17/18 | 7.7d proof/fix reviewed, final stacked gate outstanding |
| 8 | 5/8 | 8.3 migration, 8.5 release/cutover, 8.6 final 1.x notice |
| 9 | 5/8 | 9.2, 9.6, 9.7 final docs |
| 10 | 6/6 | Complete; targets still need distribution preparation |
| 11 | 4/5 | 11.5 owner-approved automated closure on PR11 |
| 12 | 5/5 | Fresh acceptance evidence finished; its integration PR13 remains |
| 13 | 5/5 | Complete |
| 14 | 4/4 | Complete |
| 15 | 15/15 | Implementation complete in core and external TypeScript main |
| 16 | 0/8 | 16.1–16.8, alone after other implementation |

Completion trailers on candidate branches do not mean those slices are on main. Run make progress
from the actual merged history; its global total is informational, but each row's tick is gated.

## Preserved branches and exact resume boundaries

All core branches below are pushed to origin. Local worktrees are under .claude/worktrees/; worktrees
and /private/tmp fixtures do not travel to another machine, branches do. Fetch and recreate as necessary.
Never bulk copy modules or blindly replay a stacked branch's ancestors onto main.

| Work | Branch / worktree | Head | Replay only after |
|---|---|---|---|
| Native acceptance evidence | codex/native-acceptance / native-acceptance | bff0d0380326866c7d32dc4a6288ca86e86599a9 | 75c053a |
| Multiplayer acceptance | codex/phase-11-acceptance / phase-11-acceptance | e0681ff | 0178b17 |
| Captain greenfield + merge lock | codex/phase-7-acceptance / phase-7-acceptance | 066eb92033c0b14b81e94f573a5889127193eec4 | 27a304e |
| Migration WIP | codex/migration-prep / migration-prep | b6ea4441d109a581abe923240485d0db4534649f | be1c842 |
| Skiff WIP | codex/phase-3-skiff / phase-3-skiff | bd8bcc91beeb323989d38129952434966b537974 | 51c0293 |

Acceptance PRs (attached to this chat):
- PR11: https://github.com/ROBCOATVG/slipwai_v2_Fork/pull/11
- PR13, draft: https://github.com/ROBCOATVG/slipwai_v2_Fork/pull/13
- PR14, draft: https://github.com/ROBCOATVG/slipwai_v2_Fork/pull/14

Rebase only each branch's own changes with git rebase --onto <new-parent> <boundary> <branch>.
Resolve shared plan summaries with make progress, retaining other fairways' rows and trailers.
Suggested acceptance order: native evidence, 11.5 closure, then 7.7d. For 7.7d use the updated 11.5 branch
as its new parent and 27a304e as the old boundary. Run the final rebased full gate and current platform
checks; fresh reviews are already recorded, so do not restart adversary/convergence without new findings.

### Native evidence

PR13 contains docs/reference/native-captain-acceptance.md. Actual fresh host captain read the persona,
claimed NAT, performed observed RED/GREEN work, dispatched independent collaboration stages, requested
rather than took the merge, read the actual HM grant, wrote merged, obtained local log durability and
released its claim. No Python captain delivery loop was invoked. Five targeted mutations were killed;
580 adversarial cases passed. Evidence is independently reviewed.

Limits are explicit: installed Codex default CLI failed with unsupported-model HTTP400; automatic approval
review rejected the Claude external call, so it was not retried or bypassed. Fresh collaboration supplied
the stages. HM grant exceeded a 60-second wait by six seconds; the captain parked and received matching
clearance. Its own corrected snapshot-path comparison occurred just after release; the actual HM snapshot
and grant predated it. Fixture had no remote, so durability is local-only. Do not upgrade these claims.

Earlier core gate on 0178b17 passed; final combined gate on bff0d03 was stopped at the owner's handover
request, so it MUST be rerun. Local retained fixture: /private/tmp/native-captain-proof. Earlier logs:
/private/tmp/native-core-root-verify.txt, /private/tmp/native-fixture-verify.txt. Interrupted final log:
/private/tmp/native-core-final-verify.txt. Do not assume these temporary paths survive another machine.

### Multiplayer and greenfield

PR11 explicitly records the changed owner criterion, fixes the stale release checklist and checks the
actual fleet.board: merged=1, state=idle, waiting=1 when the next slice is cleared. Four targeted tests,
fast gates, independent review, final local full gate and all three platform/documentation checks passed
on e0681ff. Its base predates the latest main changes; rebase and gate the final combined tree before merge.
Final receipt: /tmp/slipwai11-accepted-final-verify.log.

PR14 adds an unseeded, sequential ORD-then-BIL two-clone exercise: four product commits, real claims,
merges, published receipts and two finished board rows. It found a real defect: claims.fetch fetched
refs/slipwai/claims/* but omitted the raw refs/slipwai/merge. The second clone therefore missed an existing
released lock and could never acquire it. Fetch the optional merge ref in the same call; retain atomic CAS.
Direct actual-Git RED observed holder None; 18 claim tests passed, greenfield passed in44.271s, unit1721
with49 existing skips and lint/types passed after refactor. Fresh review/adversary had no material findings;
LOW seeded/unseeded/scheduling documentation clarified. Final rebase/full gate/CI are still required.
Receipts: /tmp/slipwai7-merge-lock-red.log, /tmp/slipwai7-merge-lock-green.log,
/tmp/slipwai7-greenfield-only.log, /tmp/slipwai7-acceptance-final-fast.log.

### Migration WIP — 8.3

All10 generated profile/backend rows plus both adopted rows and real languages-to-packages loading passed
against installed PyPI1.5.1. Every migrated fixture ran its own full gate. Unit1756/49 existing skips,
27 targeted tests, lint/types passed. This does NOT close all implementation:
- Legacy queued inbox conversion remains.
- Human/abrupt stopped-state mapping remains; only parked with a reason is handled.
- Claimed branch retention/rename/rebase notes exist, but the migrated deck claimed seed remains.
- Fresh review/refactor, final exact acceptance rerun and full keel gate remain.

Merge preserves actual Git conflict stages/abort, renamed-path edits, CRLF person text and binary bytes;
preflight refuses ignored replacement/symlink/shape collisions before project mutation. Reconstruction uses
latest generator.updatedWith (fallback generatedWith), not the original scaffold version. Proposal clearance
and explicit claims --take are guarded. Release-mode convergence is evidence: unrecorded→recorded→confirmed.
The 7.7d fetch-only claims.py fix is independent of migration's take guard; preserve both when merging.

Local fixtures/logs: /tmp/migration-complete.log, /tmp/slipwai-migration-complete,
/tmp/slipwai-migration-fixture-packages, /tmp/slipwai-migration-legacy-factory/bin/python,
/tmp/migration-unit7.log, /tmp/migration-targeted5.log, /tmp/migration-harness-check.log.

### Skiff WIP — 3.4b

WIP includes root's Azure changes. Last lint/types passed408; last unit had1720 cases/49 existing skips
and THREE failures: project/readme.py371 lines exceeds350; two test_target_reading assertions expect only
2 documentation pages rather than the added infra/README. Fix the module budget by extracting the skiff
production README section to the appropriate existing helper; update page assertions to verify the new page.
Then rebase, fast/targeted gates, fresh review/refactor, one convergence and full/CI gates. No Slice-done3.4b.

New target member DEPLOYMENT_SHAPES is separate from bootstrap/service SHAPES. New slipways default skiff;
missing shape on old manifests means liner. Skiffs have only production; convergence prepares expansion
without deleting data/state. AWS Lightsail private managed PostgreSQL cannot simply become liner RDS through
DNS: backup/export/import and validation are explicit; retain old stack/state, never silently replace DB.
Azure retains its existing firewall/TLS database policy (no new private-network claim), resource addresses
and state. CPU0.25/memory0.5Gi, minimum0 with HTTP wake; database does not scale to zero.

17 generic/AWS controller regressions and4 Azure package tests passed. Actual TypeScript/Postgres skiff and
liner bootstrap/service stacks for BOTH targets initialized, formatted and validated with pinned providers;
actual skiff Postgres→memory pruning left both stacks valid. Scratch-image migration wrapper Docker proof
passed; its containers/images were removed. AWS migration jobs use static BusyBox, immutable migration
images, explicit success markers, bounded waits, redacted0600 diagnostics and ownership-checked cleanup;
explicit buildpack migrate commands use /cnb/lifecycle/launcher. No cloud apply or real infrastructure.

Local generation packages: /private/tmp/slipwai-skiff-proof-packages (external TypeScript plus checkout
targets). Provider receipts: /tmp/slipwai-azure-{skiff,liner}-*.log and agent's AWS proof logs. Final freeze
fast log: /private/tmp/phase-3-freeze-fast.log. Recreate .python-tools link from main if needed; it is
untracked and must never be included by git add -A.

### Final 1.x notice WIP — 8.6, separate upstream repository

Public upstream ROBCOATVG/slipwai branch codex/phase-8-1x-notice is pushed at
78400d5b2fa4e3384ea6a9c214cfad7737347367, based on e1a9e4372b384f8eb086be381b737f0e84aa4883.
Local clone: /private/tmp/slipwai-1x-upgrade-notice. Three files only: conditional upgrade --check notice,
typed chart and PATCH fragment. VERSION remains1.5.2.dev0; only byte-compilation was checked. No release.
Missing: actual docs/migrating-to-2.md, meaningful registry/installed-shape tests, lint/types, review/fullgate.
Future canonical URL: https://github.com/ROBCOATVG/slipwai/blob/main/docs/migrating-to-2.md
Working 8.3 CLI has --check/--with-claims/--no-install; verify final flags before documenting. A conditional
notice can be prepared before2 exists and must say it is available only after actual registry discovery.

## Finish order and cautions

1. Rebase/gate/merge acceptance increments; preserve both independent claims.py fixes.
2. Close migration/skiff outstanding work in parallel and review/gate their final rebased candidates.
3. Prepare publication route, target/language package releases/channel updates and upstream cutover.
   Bare published languages currently need declared target packages: do not call source-linked proof a
   successful fresh registry install. Re-run the published-package backstop against the final candidate.
4. Phase16 alone, then final phase9 documentation/changelog/reference consistency and migration page.
5. Complete final1.x notice preparation, full release dry-run and all distribution/platform proofs;
   actual2.0.0 cut/publication/upstream merge last. Do not spend a tag with no working publisher.

Older unowned adoption, UTF-8, snapshot scaffolding, glossary and Codex commandsDir findings are repaired.
Small careen notes from the earlier run still need disposition: discarded diagnostics in older takeover
keeper code and stale Refreshed comments. Deck/harbour logs are ignored; stops and iterations were recorded
there. Do not commit logs, trust stale checkpoints, or reuse interrupted test output as a passed gate.
