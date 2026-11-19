PATCH

**Four rules say the same thing everywhere they are stated.** An audit after the per-slice readings fix
found the same fault in other rules: the rung that owns a rule had moved and other pages still stated the old
one, in the agent briefs, `AGENTS.md`, the constitution and tasks templates, two skills and the guides.

- **When a slice is pushed.** Three briefs, both constitution templates, the tasks template and two skills
  said "after demo acceptance". The rule is the ladder's: once every example is proven by a test and the
  review is closed.
- **When a capability's gates run.** About twenty places said "once its last slice has merged". The gates run
  on the last slice's branch, before that slice merges; the harbourmaster refuses the merge until they clear.
- **What a slice does before it is done.** The tasks template still told every slice to run a full attack and
  mutation testing, and two pages still described the version 1 order. A slice records its trigger table and
  attacks nothing; the attack and mutation are the capability's.
- **The check before a push.** `/sail` said to stop and ask the user whenever no flag holds a change back. A
  pre-launch product has no flags, so that read as a stop at every push. It now follows the release mode: no
  question under `open`, the keystone under `keystone`, the flag under `flagged`.

For the keel's own developers, `scripts/rule-copies.py` records every file that restates one of six rules
against a digest of the passage that owns it. Changing the owner, or adding a copy, fails
`tests/test_rule_copies.py` and lists each copy to read again.

**Catch-up:** `slipwai migrate` carries the pages, briefs and templates. A constitution already ratified
keeps its own wording: where Principle V says commits wait until "the actor has accepted the demo", amend it
to "until every example of the slice is proven by a test". A `tasks.md` already written from the old template
may list a full `/adversary` pass and mutation testing under Phase 4: neither is owed by the slice.
