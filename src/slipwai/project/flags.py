"""The flag half of a project with somewhere to deploy: the reader, the gate, and the release decision.

Under a production target every commit that passes `verify` on `main` is applied to production, so a flag
is the only thing standing between a merge and a customer — which is what the constitution's
`build-once-deploy-is-not-release` requires and what MinimumCD means by trunk being releasable at every
commit. That makes the flag a piece of the *skeleton*, not a convention to describe: a backend gets a
reader in the same way it gets a health check.

One module rather than a row in four, because the parts only make sense together. Each backend's
`flag_reader` answer says where its reader comes from and where it lands; `flag_reader` here is what a
backend's `service_files` merges in; the same answer spells the path for the prose in `AGENTS.md`, the ladder stage in
`commands/sail.md` and the release section of `docs/deployment.md`, so the file, the rule that points at
it, and the page that explains it cannot disagree. Nothing here is emitted under `--target none`: a project
with nowhere to deploy has no unsafe push to make, and `flags.auto.tfvars` — the one place a flag is
declared — is the target's file.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from ..assets import PAGE_ROOT, asset_tree, inside, located
from ..catalog import CATALOG
from ..errors import GenerationError
from ..registry import FLAG_READER, registry
from ..services import App, services_of
from ..targets import managed
from .prose import page

# What prose calls a project's own package, the way a backend's `persistence_directory` answer spells it: the
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


def reader_of(backend: str) -> FlagReader:
    """The backend's `flag_reader` answer, from the registry."""
    return cast(FlagReader, registry().answer(backend, FLAG_READER))


RELEASE_PAGE = "docs/deployment-release.md"


def flag_reader(target: str, backend: str) -> dict[str, str]:
    """The reader and its own tests, keyed relative to a service — and nothing at all under `none`.

    Merged by each backend's `service_files`, before `name_service` runs, so the package rename reaches
    these files the way it reaches every other one: the Python reader lands in the project's own package
    and the Java one declares the project's own package, with no second place that knows how either is
    spelled.
    """
    if not managed(CATALOG, target):
        return {}
    roots = registry().sources(backend)  # its own, then its family's: a framework reads the family's reader
    tree = reader_of(backend).tree
    held = located(roots, f"languages/{tree}", tree=True)
    package = roots[0] if held is None else held[0]
    try:
        directory = inside(package / "assets", f"languages/{tree}", package)
    except ValueError as error:
        raise GenerationError(f"{error}") from error
    if not directory.is_dir():
        raise GenerationError(f"{tree} is not a directory under {package / 'assets/languages'}")
    return asset_tree(directory, package)


def spoken(relative: str) -> str:
    """A committed path as a document has to name it, with the project's own package left as `<package>`."""
    return relative.replace("delivery_starter", PACKAGE).replace("deliverystarter", PACKAGE)


def reader_paths(apps: list[App]) -> str:
    """Every service's reader, as prose names it — one entry per distinct path, in service order."""
    return ", ".join(
        dict.fromkeys(
            f"`{service.path}/{spoken(reader_of(service.backend).source)}`"
            for service in services_of(apps)
        )
    )


def reader_calls(apps: list[App]) -> str:
    """How a slice asks, in each language the project's services are written in."""
    return ", ".join(
        dict.fromkeys(f"`{reader_of(service.backend).call}`" for service in services_of(apps))
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
    """The release-constraint stage of `commands/sail.md`'s ladder, for a project with a target.

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
    return page(PAGE_ROOT, RELEASE_PAGE, values(apps))


def values(apps: list[App]) -> dict[str, str]:
    """Every value the release page may name, and the whole of what it may name.

    One, and that is the measure this slice took the decision on: eighty-four lines of English with a
    single substitution in them is case 1 of `docs/generated-prose.md` — the same words in every project,
    with a value put in — and nothing like the shell and YAML this slice looked at beside it.
    """
    return {"reader-paths": reader_paths(apps)}


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

