"""The flag half of a project with somewhere to deploy: the reader, the gate, and the release decision.

Under a production target every commit that passes `verify` on `main` is applied to production, so a flag
is the only thing standing between a merge and a customer — which is what the constitution's
`build-once-deploy-is-not-release` requires and what MinimumCD means by trunk being releasable at every
commit. That makes the flag a piece of the *skeleton*, not a convention to describe: a backend gets a
reader in the same way it gets a health check.

One module rather than a row in four, because the parts only make sense together. `FLAG_READERS` says
where each backend's reader comes from and where it lands; `flag_reader` is what a backend's
`service_files` merges in; the same table spells the path for the prose in `AGENTS.md`, the ladder stage in
`commands/drive.md` and the release section of `docs/deployment.md`, so the file, the rule that points at
it, and the page that explains it cannot disagree. Nothing here is emitted under `--target none`: a project
with nowhere to deploy has no unsafe push to make, and `flags.auto.tfvars` — the one place a flag is
declared — is the target's file.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..assets import LANGUAGE_ROOT, asset_tree
from ..catalog import CATALOG
from ..services import App, services_of
from ..targets import managed

# What prose calls a project's own package, the way `backends.event_store_directory` spells it: the
# directory is named after the project, so a document cannot name it and stay true for every project.
PACKAGE = "<package>"


@dataclass(frozen=True)
class FlagReader:
    """One backend's flag reader: where it is committed, where it lands, and how a slice asks it.

    `source` and `tests` are in the template spelling — `delivery_starter`, `deliverystarter` — because
    that is how they arrive, and each backend's own `name_service` renames them after the project along
    with everything else in the service. `spoken` turns either into the spelling a document has to use.
    """

    tree: str
    source: str
    tests: str
    call: str


# Keyed by backend. Both Java backends read one tree, for the reason they share `java/build/` and every
# `../java/` source in `service_layouts.py`: this class names no framework type — no `@ConfigProperty`, no
# `@Value` — so a second copy would have nothing to say differently and could only drift.
FLAG_READERS: dict[str, FlagReader] = {
    "typescript": FlagReader(
        tree="typescript/flags",
        source="src/flags.ts",
        tests="tests/flags.test.ts",
        call="flagEnabled('checkout-v2')",
    ),
    "python": FlagReader(
        tree="python/flags",
        source="src/delivery_starter/flags.py",
        tests="tests/test_flags.py",
        call='flag_enabled("checkout-v2")',
    ),
    "go": FlagReader(
        tree="go/flags",
        source="flags/flags.go",
        tests="flags/flags_test.go",
        call='flags.Enabled("checkout-v2")',
    ),
    "java-quarkus": FlagReader(
        tree="java/flags",
        source="src/main/java/com/example/deliverystarter/flags/Flags.java",
        tests="src/test/java/com/example/deliverystarter/flags/FlagsTest.java",
        call='Flags.enabled("checkout-v2")',
    ),
    "java-spring": FlagReader(
        tree="java/flags",
        source="src/main/java/com/example/deliverystarter/flags/Flags.java",
        tests="src/test/java/com/example/deliverystarter/flags/FlagsTest.java",
        call='Flags.enabled("checkout-v2")',
    ),
}


def flag_reader(target: str, backend: str) -> dict[str, str]:
    """The reader and its own tests, keyed relative to a service — and nothing at all under `none`.

    Merged by each backend's `service_files`, before `name_service` runs, so the package rename reaches
    these files the way it reaches every other one: the Python reader lands in the project's own package
    and the Java one declares the project's own package, with no second place that knows how either is
    spelled.
    """
    if not managed(CATALOG, target):
        return {}
    return asset_tree(LANGUAGE_ROOT / FLAG_READERS[backend].tree)


def spoken(relative: str) -> str:
    """A committed path as a document has to name it, with the project's own package left as `<package>`."""
    return relative.replace("delivery_starter", PACKAGE).replace("deliverystarter", PACKAGE)


def reader_paths(apps: list[App]) -> str:
    """Every service's reader, as prose names it — one entry per distinct path, in service order."""
    return ", ".join(
        dict.fromkeys(
            f"`{service.path}/{spoken(FLAG_READERS[service.backend].source)}`"
            for service in services_of(apps)
        )
    )


def reader_calls(apps: list[App]) -> str:
    """How a slice asks, in each language the project's services are written in."""
    return ", ".join(
        dict.fromkeys(f"`{FLAG_READERS[service.backend].call}`" for service in services_of(apps))
    )


def flag_gate_dependency(target: str) -> str:
    """`check-flags` in `verify`'s dependency list, under a target and nothing otherwise.

    A flag is declared in `infra/service/flags.auto.tfvars`, which is the target's own file, so under
    `none` there is nowhere to declare one, nothing to read and no unsafe push to hold back. A gate that
    always passed would be worse than its absence: it would read as coverage this project does not have.
    """
    return " check-flags" if managed(CATALOG, target) else ""


def flag_gate(target: str) -> str:
    """The `check-flags` recipe, for a project that has somewhere a flag could be declared.

    Part of `verify` rather than of the production section beside `make flag`: it reads files and needs no
    account, so it belongs with the other four static gates and runs on every commit — which is the only
    point at which "this flag is read nowhere" is cheap to hear.
    """
    if not managed(CATALOG, target):
        return ""
    return """check-flags: ## Fail when a flag is declared and never read, read and never declared, seeded on, or tested on one path
\tpython3 scripts/check-flags.py
"""


def flag_stage(apps: list[App]) -> str:
    """The release-constraint stage of `commands/drive.md`'s ladder, for a project with a target.

    Between the slice's gaps review and its plan, because the plan is where the decision is written down
    and because deciding it later means deciding it after the code exists — which is when "it is only a
    small change" starts to sound reasonable.
    """
    return f"""**Release constraint** — the slice's flag is decided and written down in the plan: which
   releasable capability the slice belongs to, the flag key that holds it, and the fact that the flag is
   declared in `infra/service/flags.auto.tfvars` seeded `off` in the same change as the code that reads
   it. A flag covers a **releasable capability**, which is usually more than one slice: a capability that
   is not coherent to an actor until three slices land wants one flag held off across all three, not three
   flags — and one flag stretched over unrelated capabilities is the opposite failure, because they can
   then only be released together. So state which of the three this slice is, and why:
   it **continues** a capability that already has a flag and reuses that key; it **opens** one and needs a
   new key; or it is **releasable on merge and needs no flag**, because everything it adds is coherent and
   safe to an actor the moment it lands — a read-only path that shows only what the actor may already see
   is the usual case, and a change with no actor-visible behaviour at all is the other.
   The third answer is a decision like the other two and is written down like them: name it in the plan
   with its reason. An absent flag and an undecided flag look identical afterwards, and only one of them is
   safe — so a slice with no key says so in a sentence rather than saying nothing, and `AGENTS.md` asks for
   that same sentence again in the turn that pushes. **Recommend the answer with its reason rather than
   asking an open question**, and ask the user only where it is genuinely undecidable which capability the
   slice completes, or whether what it exposes is already the actor's to see — those are product questions
   and not defaults. Never add a second flag for a capability that already has one, and never gate a slice
   for the look of it: a flag over something already released is a code path kept alive for nobody.
   Where there is a flag, it is read **only** through {reader_paths(apps)}, asked by key
   ({reader_calls(apps)}) — never by naming `FLAG_<KEY>` at the point of use, which loses the transform,
   the single spelling and the seam that lets a test drive both paths. `make check-flags` refuses a key
   declared and never read, a key read and never declared, a new key seeded anything but `off`, a key
   whose tests only drive one path, and a read that goes round the reader."""


def release_notes(apps: list[App]) -> str:
    """The release half of `docs/deployment.md`: what a flag covers, which undo button, and what a flip is.

    Here rather than in `production_docs.py` for the reason the rest of this module is here: every sentence
    below is about the same three files — the reader, `flags.tf` and `flags.auto.tfvars` — and the page that
    explains them should not be able to drift from the rule in `AGENTS.md` that points at them.
    """
    return f"""
## Releasing, and undoing a release

Deploying and releasing are two decisions, and everything above this line is the first one. A commit that
passes `verify` on `main` is applied to production with nobody in between, so what makes that safe is that
unfinished work arrives **dark**: merged, deployed, and gated by a flag that is off.

A flag is declared in `infra/service/flags.auto.tfvars` under the service that reads it, seeded `off`, in
the same change as the code reading it. It reaches that service as `FLAG_<KEY>`, and the only place this
side reads one is
{reader_paths(apps)}.
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
"""


# What `docs/gates.md` says about the flag gate, beside what it says about the image half of `make ci`.
FLAG_GATE_NOTE = """
`make check-flags` is in `verify` for a reason of the same kind: every commit that passes it on `main`
reaches production, so a feature flag is the only thing between a merge and a customer. It refuses a flag
declared in `infra/service/flags.auto.tfvars` and read nowhere, a flag read and declared nowhere — which
exists in no environment and so can never be turned on — a new flag seeded anything but `off`, a flag
whose tests drive only one of its two paths, and a read that goes round the service's own reader to name
`FLAG_<KEY>` itself, which loses the key-to-variable transform and the seam both paths are tested through.
`docs/deployment.md` says what one flag covers, which undo
button a bad flip needs, and why the flip is the one production change made outside the pipeline.
"""


PUSH_CHECK = """### Before you push, name the release constraint

A push to `main` is a production deploy here: `verify` passes, `deploy.yml` applies staging, smokes it,
applies production and smokes that, with nobody in between. So the last thing before pushing is to say, in
the turn that pushes, what holds this change back from the actor — the flag key, and that it is `off` in
both environments.

**If nothing does — no flag, or a flag that is already on — stop and ask the user to confirm that this is a
release they want now.** Do not push and mention it afterwards, and do not decide on their behalf that the
change is small enough to be safe: there is no later gate at which somebody would catch it, which is the
whole reason the question is asked here. A refactor with no actor-visible behaviour is not a release and
needs no flag; say that it is one, rather than saying nothing.
"""
