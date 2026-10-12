
## Releasing, and undoing a release

Deploying and releasing are two decisions, and everything above this line is the first one. A commit that
passes `verify` on `main` is applied to production with nobody in between, so what makes that safe is that
unfinished work arrives **dark**: merged, deployed, and gated by a flag that is off.

A flag is declared in `infra/service/flags.auto.tfvars` under the service that reads it, seeded `off`, in
the same change as the code reading it. It reaches that service as `FLAG_<KEY>`, and the only place this
side reads one is
{{reader-paths}}.
Only place is meant literally: ask by key and the reader derives the variable, so the declaration and the
code cannot drift apart, an unset variable reads as off rather than as a typo, and a test can drive both
paths without touching the process's own environment.

Where the value comes *from* is one object inside that reader — the source — and it is keyed by the flag's
own key rather than by a variable name. It answers two questions: what this environment holds for one key,
and what it holds for all of them. Today there is one source and it reads this container's environment,
which is where the SSM parameter lands. A transport that is not an environment, an AppConfig agent beside
the container answered over loopback, is a second source and a one-line change to the reader's default: no
call site moves, no test moves, and this page's account of what a flip costs is the only other thing that
has to. The second question is there because something has to answer it for a browser app, which cannot
read this environment itself — and it is a snapshot rather than a subscription, because a transport polling
an agent can promise the values it last saw and nothing stronger. `make check-flags` runs inside `make verify` and
refuses a key declared and never read, a key read and never declared, a new key seeded anything but `off`,
a key whose tests only ever drive one path, and a read that names `FLAG_<KEY>` instead of calling the
reader.

### A flag covers a releasable capability, not a slice

"One flag per slice" is the wrong rule and it is the one teams reach for. A capability that is not coherent
to an actor until three slices land wants **one** flag, held off across all three: three flags mean two
states nobody designed, and the first one turned on shows a customer half a feature. The opposite failure
is one flag stretched over unrelated capabilities — they can then only be released together, and the flag
never gets deleted because something behind it is always unfinished. So the unit is the smallest thing
worth announcing, and the test of a key is whether turning it on is a sentence you would say to a customer.

### Two undo buttons, and they cost different things

| Something is wrong with | Press | What it costs |
|---|---|---|
| the release — it is broken however the flags are set | `.github/workflows/rollback.yml`, started by hand with the environment | re-applies the previous release's digests and its `index.html`, then smokes it. Every unrelated commit in that release goes backwards with it, and the schema does not move — which is why every migration is held to expand/contract |
| the flip — the release was fine until a flag went on | `make flag ENV=… KEY=… VALUE=off` | a rolling restart of one service, about two minutes. No build, no apply, no merge, and nothing unrelated moves |

Pressing the wrong one is the failure worth naming: **a rollback does not turn a flag off.** The parameter
is not in the release record, and `ignore_changes = [value]` means no apply ever puts it back — so a
rollback aimed at a bad flip returns good code to an earlier version and leaves the flag exactly as it was.
Ask which of the two rows you are in before pressing anything: did this break when the release went out, or
when somebody flipped something?

### The flip is the one production change outside the pipeline

`make flag` writes an SSM parameter and forces a new deployment. No `verify`, no review, no commit, and
nothing in the release record — which names a commit and its images. That is deliberate, and it is the one
place this project's own constitution is knowingly stretched: *One Path to Production* says that a thing
that can be changed in a running environment without a commit is not managed. The seed in
`flags.auto.tfvars` is managed; the live value is not, on purpose, because a release that needed a deploy
would not be a separate decision from one.

Two things make that affordable rather than merely true:

- **`make flags ENV=…` is where the answer lives**, and it prints more than the value: SSM keeps every
  parameter's version history, so it also prints who set each flag and when. Nothing extra is stored to
  make that work — a flip has an audit trail because the parameter store already kept one.
- **`make flag` smokes the environment afterwards.** The flip forces a new deployment, so the tasks that
  hold the new value have to come up and pass their health checks either way; waiting for that and then
  asking the environment whether it still answers costs the two minutes already being spent.

### Blue/green means both revisions read the same parameter

During the bake — five minutes in production — the previous release and the new one are both running, and
both resolve the same parameter. A flip in that window reaches both. A key the older revision has never
heard of is harmless, because nothing reads it; a key whose *meaning* changed between the two revisions is
not, and that is the compatibility rule landing on flags instead of on schemas. So a key is never
repurposed: retire it and introduce another, exactly as a column is expanded before it is contracted.

### What is not gated: owner, removal date, expiry

The constitution asks that every release flag have an owner, a removal date, tests on both paths, and an
expiry. `make check-flags` gates the third of those and nothing gates the rest, because on a boolean flag
they are hygiene rather than safety — a flag with no owner is untidy, a flag nobody reads is a feature that
never ships. Record them as a comment beside the key in `flags.auto.tfvars`, and when the capability is
released, delete the key, the branch it gated and the test of the off path in one change: a flag that
outlives its capability is a second code path being maintained for nobody.
