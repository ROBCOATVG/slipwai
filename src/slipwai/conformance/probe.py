"""The checks themselves, run in the interpreter `run.check` starts with the package directory already set.

`python -m slipwai.conformance.probe <language-dir> <package> <report>` writes `{"findings": {check: [line, …]},
"not_run": {check: reason}}` to the file `<report>` and exits 0 whatever it found: a finding is the package's, and
only a crash of the suite itself exits otherwise. Nothing it prints is the report, so nothing a package prints is.
Imported only here, with `SLIPWAI_LANGUAGES` naming the directory, because the merged catalog is read at import
and the directory is the one the author named. A SIGTERM ends it as `SystemExit`, which removes its temporary
directory.
"""
from __future__ import annotations

import json
import signal
import sys
import tempfile
from pathlib import Path

from ..catalog import CATALOG, family_of
from ..errors import GenerationError
from ..examples import markers, snippet
from ..language_directory import named
from ..loaded import refusals
from ..registry import BROWSER_APPS, PROTOCOL, Registry, registry
from .frontends import SHIPS_NONE, frontend_findings
from .generation import profile_findings, read_by, runs, stopped, target_findings
from .rows import row_findings

# Why the checks after `protocol` did not run, as `protocol` decided it: each says what the package did.
UNLOADED = "the package did not load, so nothing it answers can be read"
ALONE = "{family} loaded, but it has no backend of its own and none of its family beside it to check it through"
# Why the backend checks did not run for a package of browser apps alone: there is no backend to read.
FRONTENDS_ONLY = "does not apply: {family} ships browser apps and no backend, and these checks read one"
MISANSWERED = "{package} loaded, but protocol found what it answers wrong, so nothing else it answers is read"
BESIDE_REFUSED = "{family} loaded, but every framework of it beside it was refused, as protocol says, so none checks it"
# Why a check that reads generations claims nothing over them: each stopped on a snippet `markers` named (P001, A62).
STOPPED = "{stopped} of {runs} generations stopped at a snippet markers named"
# What `examples.snippet` says of a marker a backend has no snippet for, and so what a generation stopped by one says.
MISSING_SNIPPET = "missing {backend} example snippet for {skill}/{example} ("
MISSING = object()


def owned(loaded: Registry, root: Path) -> tuple[list[str], list[str]]:
    """The backends and the families whose files are under `root`, in the registry's order."""
    def under(name: str) -> bool:
        return name in loaded.roots and loaded.roots[name].resolve() == root

    return [key for key in loaded.backends if under(key)], [name for name in loaded.families if under(name)]


def required_family(root: Path) -> list[str]:
    """The family a framework's `language.json` requires, as written; nothing for a package that requires none."""
    try:
        requires = json.loads((root / "language.json").read_text(encoding="utf-8")).get("requires")
    except (OSError, ValueError, AttributeError):
        return []
    return [name for name in requires if isinstance(name, str)] if isinstance(requires, dict) else []


def protocol(directory: Path, package: str) -> tuple[list[str], list[str] | str]:
    """The `protocol` check's findings, and the backends every later check reads — or, where there are none to read,
    why, which is what each later check says it did not run for.

    The loader already refuses a package that misses a member, answers one with the wrong kind, reaches outside its
    directory or needs a family that is not loaded, in one line naming which; that line is the finding. A family
    with no backend of its own is checked through every backend of it loaded beside it, its frameworks.
    """
    located = directory / package
    root = located.resolve()
    if not (root / "language.json").is_file():
        return [f"{directory} holds no package {package} (no {package}/language.json)"], UNLOADED

    def said_by(name: str) -> list[str]:
        """The refusals that are `name`'s own: the loader's `language <name> (<root>): ` exactly, root included, so a
        sibling directory called `<name> (x` is not it.

        The root is the directory as it was given. A second spelling of that same directory — `/var` and
        `/private/var` on macOS — is still this package, matched by resolving both sides. The sibling guard
        stays: the line has to name `name`, and the path inside it has to be this package's directory.
        """
        prefix = f"{named(name, directory / name)}: "
        want = (directory / name).resolve()
        marker = f"language {name} ("
        found: list[str] = []
        for line in refusals():
            if line.startswith(prefix):
                found.append(line)
                continue
            if not line.startswith(marker):
                continue
            end = line.find("): ")
            if end < 0:
                continue
            try:
                same = Path(line[len(marker):end]).resolve() == want
            except OSError:
                same = False
            if same:
                found.append(line)
        return found

    refused = said_by(package)
    if refused:
        # A framework refused because its family was: the family's own line says why.
        return [*refused, *(line for family in required_family(root) for line in said_by(family))], UNLOADED
    loaded = registry()
    backends, families = owned(loaded, root)
    if not backends and not families:
        return [f"language {package} did not load from {located}"], UNLOADED
    if not backends:
        backends = [key for key, backend in loaded.backends.items() if backend.family in families]
    if not backends and any(BROWSER_APPS in loaded.families[name].answers for name in families):
        return [], FRONTENDS_ONLY.format(family=", ".join(families))
    if not backends:
        family = ", ".join(families)
        beside = [line for sibling in sorted(directory.iterdir()) if sibling.name != package
                  and set(families) & set(required_family(sibling.resolve())) for line in said_by(sibling.name)]
        if beside:
            return beside, BESIDE_REFUSED.format(family=family)
        return [f"{family} declares no backend of its own, and no backend of family {family} is loaded beside it "
                f"in {directory}: a family is checked with a framework beside it"], ALONE.format(family=family)
    findings: list[str] = []
    for key in backends:
        for member in PROTOCOL:
            if member.required:
                try:
                    loaded.answer(key, member)
                except KeyError as error:
                    findings.append(str(error.args[0]))
    findings += kind_findings(loaded, backends)
    return findings, (MISANSWERED.format(package=package) if findings else backends)


def kind_findings(loaded: Registry, backends: list[str]) -> list[str]:
    """Every member answered with a kind the protocol does not want, optional ones included: the loader holds only
    the required ones to their kind (`registry.load`), and `None` is an answer like any other."""
    findings: list[str] = []
    for key in backends:
        backend = loaded.backends[key]
        holders = [backend.answers, *([loaded.families[backend.family].answers] if backend.family in loaded.families
                                      else [])]
        for member in PROTOCOL:
            held = next((answers[member] for answers in holders if member in answers), MISSING)
            if held is not MISSING and not isinstance(held, member.kind):
                kinds = member.kind if isinstance(member.kind, tuple) else (member.kind,)
                findings.append(f"backend {key} answers {member.name} with {type(held).__name__}, where the protocol "
                                f"wants {' or '.join(kind.__name__ for kind in kinds)}")
    return list(dict.fromkeys(findings))


def marker_findings(backends: list[str]) -> tuple[list[str], dict[str, list[str]]]:
    """Every marker some profile carries that a backend has no snippet for, with the profiles that carry it; and, per
    backend, what a generation stopped by each of those says, so `profiles` and `targets` do not name it again."""
    asked = {profile: markers(profile) for profile in CATALOG["profiles"]}
    every = sorted(set().union(*asked.values()))
    findings: list[str] = []
    missing: dict[str, list[str]] = {key: [] for key in backends}
    for key in backends:
        for skill, example in every:
            try:
                snippet(key, family_of(key), skill, example)
            except GenerationError as error:
                profiles = ", ".join(profile for profile, carried in asked.items() if (skill, example) in carried)
                lead = MISSING_SNIPPET.format(backend=key, skill=skill, example=example)
                if str(error).startswith(lead):
                    findings.append(f"backend {key} has no snippet for {skill}/{example} ({profiles})")
                    missing[key].append(lead)
                else:
                    # One that is there and cannot be used — not a file, not text — in the words generation stops on.
                    findings.append(f"backend {key} cannot use its snippet for {skill}/{example} ({profiles}): {error}")
                    missing[key].append(str(error))
    return findings, missing


def probe(directory: Path, package: str) -> dict[str, dict]:
    """Every check over `package` in `directory`: what each found, and why any did not run."""
    findings: dict[str, list[str]] = {}
    not_run: dict[str, str] = {}
    findings["protocol"], backends = protocol(directory, package)
    loaded_families = owned(registry(), (directory / package).resolve())[1] if not findings["protocol"] else []
    with tempfile.TemporaryDirectory(prefix="slipwai-frontends-") as output:
        found, why = (frontend_findings(registry(), loaded_families, Path(output)) if loaded_families
                      else ([], backends if isinstance(backends, str) else SHIPS_NONE))
    if why is None:
        findings["frontends"] = found
    else:
        not_run["frontends"] = why
    if isinstance(backends, str):
        not_run.update(dict.fromkeys(("markers", "profiles", "targets", "prune rows"), backends))
    else:
        findings["markers"], missing = marker_findings(backends)
        loaded = registry()
        with tempfile.TemporaryDirectory(prefix="slipwai-conformance-") as output:
            read = {"profiles": [0, 0], "targets": [0, 0], "prune rows": [0, 0]}
            findings.update((name, []) for name in read)
            for key in backends:
                done = runs(Path(output), key)
                findings["profiles"] += profile_findings(loaded, key, done, missing[key])
                findings["targets"] += target_findings(loaded, key, done, missing[key])
                findings["prune rows"] += row_findings(loaded, key, done)
                for name, over in read_by(key, done).items():
                    read[name][0] += sum(stopped(run, missing[key]) for run in over)
                    read[name][1] += len(over)
        # A check none of whose findings are its own claims no pass over runs that never reached the package's code.
        for name, (halted, total) in read.items():
            if halted and not findings[name]:
                del findings[name]
                not_run[name] = STOPPED.format(stopped=halted, runs=total)
    return {"findings": findings, "not_run": not_run}


def main(argv: list[str]) -> int:
    # A stop (CI cancelling a job, `timeout`) ends the run as an exception, so `probe`'s temporary directory is removed.
    signal.signal(signal.SIGTERM, lambda _number, _frame: sys.exit(128 + signal.SIGTERM))
    directory, package, destination = Path(argv[0]), argv[1], Path(argv[2])
    if not directory.is_absolute():
        directory = directory.absolute()
    destination.write_text(json.dumps(probe(directory, package)), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
