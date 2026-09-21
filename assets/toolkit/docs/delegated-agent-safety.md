# Delegated-agent safety

Every delegated brief references this page and adds only its task, contract and file manifest. The write
scope comes from the *type* the brief delegates to — `agents/drive-tasks.md`, `drive-implement`,
`drive-converge`, `drive-gaps`, `drive-adversary`, `drive-mutation`, `drive-slice` — which declares it in words no harness owns and is
projected into the installed harness with as much of it enforced as that harness can express
(`docs/agent-harnesses.md`). Keeping the standing constraints here, and the scope there, prevents an older
brief from carrying an incomplete copy of either.

- Treat the type's write scope literally, whether or not the harness could enforce it — the stamp on your own
  projection says which. An adversary is read-only; a tasks delegate writes only its slice's `tasks.md`; an
  implementation delegate may edit only the files its manifest names. Stop and report when another change
  is needed.
- Preserve work already in the checkout. Never use `git stash`, never use `git checkout` without the exact
  path and intent, and never copy a tracked file aside as a backup. The one sanctioned way to observe a
  failure without leaving the tree dirty — to check an assertion has teeth, or to see a RED on code that
  already exists — is to change the production file, run the test, and restore that file with
  `git checkout -- <exact path>`. A prohibition with no legal route gets routed around by exactly the
  delegates trying hardest to do the job well; this is the route.
- A delegate that edits the tree as part of its *method* rather than its output — a converge pass mutating
  code to prove a finding, an implementation delegate checking an assertion discriminates — owns leaving it
  clean on every exit path, including being stopped: branch or commit before the first such edit, restore
  each file before the next, and report what was touched. A stopped pass once left a mutation live in the
  tree the demo was next to run from.
- Do not stop processes by command-line pattern: `pkill -f <pattern>` can match the shell issuing it. Stop only
  a PID the task started and recorded.
- Leave existing long-lived processes running, including development servers, demos, watchers and backing
  services. Report a conflict instead of replacing or restarting one.
- Do not send a state-changing HTTP request to an already-running application. It may point at a schema holding
  a person's real or demo data. Use an isolated test process and disposable data for reproductions; if that
  cannot be arranged, report the proposed request instead of sending it.
- Do not alter branches, commits, tags, remotes, credentials or repository-wide configuration unless the brief
  explicitly delegates that operation.

The host remains responsible for triage and for verifying a delegate's evidence. A delegate that reaches a
product decision or needs scope beyond its manifest returns the question; it does not choose or search outward.
