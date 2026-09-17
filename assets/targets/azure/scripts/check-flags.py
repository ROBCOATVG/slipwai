#!/usr/bin/env python3
"""Hold every feature flag to what can be checked without an account, whatever language reads it.

A flag is what makes deploying and releasing two decisions. Every commit that passes `verify` on `main` is
applied to production, so unfinished work is safe there only while something holds it back — and the
constitution requires exactly that: incomplete work reaches production dark, behind a flag, with tests on
both paths. This is the gate on the half of that clause a static check can see. It reads files, runs no
`az` and no `tofu`, and needs nothing running.

Four rules, each with the failure it exists to prevent:

1. **A declared flag is read somewhere.** A key in `infra/service/flags.auto.tfvars` that no source file
   asks for is dead configuration: a secret in every environment, a line in `make flags`, and nothing
   behind it. Usually it is the remains of a released capability whose branch was deleted and whose key was
   not.
2. **A flag that is read is declared.** The more dangerous direction. A key nothing declares exists in no
   environment, so it can never be turned on — and from the outside that looks exactly like a feature that
   shipped and was fine. Nothing fails; the feature is simply never reachable.
3. **A new flag is seeded `off`.** The seed in `flags.auto.tfvars` is what a *new* environment starts at,
   and a flag being introduced is by definition not released yet. Seeded `on`, an environment created
   tomorrow behaves differently from the one beside it, and the seed cannot be corrected afterwards —
   `ignore_changes = [value]` means the stack never touches a secret it has created.
4. **Both paths are exercised in tests.** While a flag is off, the branch running in production is the one
   the slice's own tests do not reach unless somebody wrote them; "it worked before the branch was added"
   is not evidence about the code after it. Heuristic, in the same way and to the same degree as
   `check-migrations.py` is heuristic: it reads the test corpus for the key driven on and driven not-on.
5. **A flag is read through the reader.** The service's own flag package is the only place that touches the
   environment — or, where the environment reads its flags from App Configuration, the only place that
   calls it. A slice that reaches for the App Configuration client is refused outright rather than counted
   as a read, because the key never appears in its source: rules 1 and 2 cannot see a flag they are never
   told the name of. The package says so about itself: "os.Getenv is called here and in no other package." A hand-
   derived `os.Getenv("FLAG_CHECKOUT_V2")` at the point of use loses three things at once — the key-to-
   variable transform, so a typo reads as absent and absent reads as off and the flip merely looks broken;
   the one spelling of the key, so `flags.auto.tfvars` and the code can drift apart with nothing to notice;
   and the seam the reader exists for, since a function reading the process environment directly cannot be
   driven down both paths by a test, which is rule 4 quietly unsatisfiable.

**What counts as reading a flag.** A call through the service's own reader — `flagEnabled('checkout-v2')`,
`flag_enabled("checkout-v2")`, `flags.Enabled("checkout-v2")`, `Flags.enabled("checkout-v2")` — or the
environment variable itself, `FLAG_CHECKOUT_V2`. The variable counts deliberately: a hand-derived read is
a real read, and rules 1 and 2 would be lying if it were invisible to them — a key would look dead while
something was in fact consulting it. Rule 5 is what stops that allowance from becoming permission. The two
work as a pair: the variable is *seen* as a read, and *reported* as the wrong way to have made one.

Comments are stripped first, so a commented-out read is not a read, and neither is a test — a key declared,
tested on both paths and never consulted by the code is exactly the dead configuration rule 1 exists for.
The readers themselves and their own tests are skipped entirely: they demonstrate the transform with an
example key and are not about this project's flags, and the reader is of course allowed to name the
variable — being the one place that does is the whole of its job. A browser app is unaffected: it reads
`VITE_FLAG_CHECKOUT_V2`, inlined into the bundle at deploy time, which the variable pattern does not match.

**Which service a read belongs to** is the directory it is in, from `project.json`: a read under a
service is that service's, a read in a browser app is the service its `/api` goes to (a flag is declared
once, under the service that enforces it, and the bundle is built from that service's values), and a
read in shared code under `packages/` belongs to nobody in particular and satisfies whichever service
declares the key.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "project.json"
DECLARATION = ROOT / "infra/service/flags.auto.tfvars"
DECLARATION_NAME = DECLARATION.relative_to(ROOT).as_posix()
SOURCE_TREES = ("apps", "packages")
SOURCE_SUFFIXES = {".go", ".java", ".py", ".ts", ".tsx"}
SKIPPED_DIRECTORIES = {"node_modules", ".build", "dist", "build", "target", ".venv", "coverage"}
# The reader and its own tests, by file name: they exercise the transform with an example key, so counting
# them as reads would make every generated project fail rule 2 before anybody had declared anything.
MACHINERY = {"flags", "flags.test", "test_flags", "flags_test", "Flags", "FlagsTest"}
# A test file, in each ecosystem's own convention. `tests/` and `test/` directories cover the two backends
# that keep their suites apart from their sources; the name patterns cover Go, which does not.
TEST_DIRECTORIES = {"tests", "test"}
TEST_NAMES = (
    re.compile(r"_test\.go$"),
    re.compile(r"Test\.java$"),
    re.compile(r"\.test\.tsx?$"),
    re.compile(r"^test_.*\.py$"),
)

COMMENTS = re.compile(r"--[^\n]*|//[^\n]*|#[^\n]*|/\*.*?\*/", re.DOTALL)
# `flags = {`, then `<service> = {`, then `<key> = "<seed>"`. A subset of HCL rather than a parser,
# because this file has one shape: the factory ships it with the map already there and a project fills it
# in. Anything else in it is a syntax error `tofu validate` reports better than this could.
BLOCK = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_-]*)\s*=\s*\{\s*$")
SEED = re.compile(r"^\s*([a-z0-9][a-z0-9-]*)\s*=\s*\"([^\"]*)\"\s*,?\s*$")
CLOSE = re.compile(r"^\s*\}\s*,?\s*$")

# How a slice asks. One alternative per reader, and the argument is the key in its one spelling.
READ_BY_KEY = re.compile(
    r"(?:flagEnabled|flag_enabled|flags\.Enabled(?:In)?|Flags\.enabled)\(\s*['\"]([a-z0-9][a-z0-9-]*)['\"]"
)
# The variable itself, so bypassing the reader is still visible here. `VITE_FLAG_…` does not match: the
# character before `FLAG` is a word character, so the boundary fails.
READ_BY_VARIABLE = re.compile(r"\bFLAG_([A-Z0-9][A-Z0-9_]*)\b")
# The other way round the reader: an environment running `flag_transport = "appconfig"` reads App
# Configuration with an SDK, and a slice can call that SDK directly. Rule 5 has to see that too, and it is
# *worse* than naming the variable — the key never appears in the source at all, only inside the answer
# that comes back, so rules 1 and 2 cannot even tell that something is reading a flag. There is nothing to
# count, so this is refused outright rather than counted as a read.
#
# This is also the one place the Azure target is weaker than the AWS one and the gate has to be stricter
# for it: AWS's agent sits beside the container so no image carries a cloud SDK, and Container Apps has no
# such sidecar, so the SDK is in the image whenever this transport is chosen. Confining it to the reader is
# what keeps that one dependency out of every slice.
READ_BY_SDK = re.compile(r"@azure/app-configuration|azure\.appconfiguration|AppConfigurationClient")
# How each ecosystem spells the reader call, so rule 5 can name the right one. Keyed by file suffix rather
# than by the service's recorded language, because the file that bypassed the reader is all rule 5 has to
# go on: shared code under `packages/` belongs to no service in `project.json` and still has a language.
READER_CALL = {
    ".go": 'flags.Enabled("{key}")',
    ".java": 'Flags.enabled("{key}")',
    ".py": 'flag_enabled("{key}")',
    ".ts": "flagEnabled('{key}')",
    ".tsx": "flagEnabled('{key}')",
}
# The one value that is on, as a test would write it beside the key.
ON_VALUE = re.compile(r"['\"]on['\"]|=\s*on\b")
# An off path, written out: the value, or — far more often — an environment with nothing in it, which is
# how a test drives the branch that runs in production while the flag is off. Deliberately narrow: `None`
# and `()` were here and had to go, because `-> None` and every empty argument list matched them and the
# rule was then satisfied by any test file at all.
OFF_VALUE = re.compile(r"['\"]off['\"]|=\s*off\b|\{\s*\}|Map\.of\(\)|undefined")


def key_of(variable: str) -> str:
    """The declared key a variable name came from: `CHECKOUT_V2` is `checkout-v2`."""
    return variable.lower().replace("_", "-")


def declared(text: str) -> dict[tuple[str, str], str]:
    """Every `(service, key)` the declaration file carries, with the value it seeds a new environment at."""
    found: dict[tuple[str, str], str] = {}
    service: str | None = None
    inside = False
    for line in COMMENTS.sub("", text).splitlines():
        block = BLOCK.match(line)
        if block and not inside:
            inside = block.group(1) == "flags"
            continue
        if not inside:
            continue
        if block:
            service = block.group(1)
            continue
        seed = SEED.match(line)
        if seed and service is not None:
            found[(service, seed.group(1))] = seed.group(2)
        elif CLOSE.match(line):
            if service is None:
                inside = False
            service = None
    return found


def deployables() -> tuple[dict[str, str], dict[str, str]]:
    """Where each service and each browser app lives, and for a browser app the service its `/api` reaches.

    An unreadable manifest leaves both empty, which makes every read unattributed: the rules then compare
    key sets without naming a service, which is weaker but never wrong.
    """
    services: dict[str, str] = {}
    sites: dict[str, str] = {}
    try:
        records = json.loads(MANIFEST.read_text()).get("deployables", {})
    except (OSError, ValueError, AttributeError):
        return services, sites
    for name, record in (records.items() if isinstance(records, dict) else ()):
        if not isinstance(record, dict) or not isinstance(record.get("path"), str):
            continue
        if record.get("kind") == "service":
            services[record["path"]] = name
        elif isinstance(record.get("api"), str):
            sites[record["path"]] = record["api"]
    return services, sites


def owner_of(relative: str, services: dict[str, str], sites: dict[str, str]) -> str | None:
    """Which service a file's flags belong to, or None where the file belongs to no one deployable."""
    for path, name in services.items():
        if relative.startswith(f"{path}/"):
            return name
    for path, api in sites.items():
        if relative.startswith(f"{path}/"):
            return api
    return None


def sources() -> list[Path]:
    """Every file that could read a flag. `Path.stem` drops one suffix, which is what makes one set of
    names cover `flags.ts`, `flags.test.ts`, `test_flags.py`, `flags_test.go`, `Flags.java` at once."""
    found = []
    for tree in SOURCE_TREES:
        for path in sorted((ROOT / tree).rglob("*")):
            if (
                path.is_file()
                and path.suffix in SOURCE_SUFFIXES
                and not SKIPPED_DIRECTORIES & set(path.parts)
                and path.stem not in MACHINERY
            ):
                found.append(path)
    return found


def is_test(path: Path) -> bool:
    return bool(TEST_DIRECTORIES & set(path.parts)) or any(name.search(path.name) for name in TEST_NAMES)


def keys_in(text: str) -> set[str]:
    """Every flag key this text asks for, however it asked."""
    return {match.group(1) for match in READ_BY_KEY.finditer(text)} | variables_in(text)


def variables_in(text: str) -> set[str]:
    """Every key this text asks for by naming the environment variable instead of calling the reader.

    A subset of `keys_in`, kept apart because the two are used for opposite purposes: that one asks *whether*
    a key is read, so both spellings have to count; this one asks *how* it was read, which is rule 5.
    """
    return {key_of(match.group(1)) for match in READ_BY_VARIABLE.finditer(text)}


def variable_of(key: str) -> str:
    """The environment variable a key becomes — the transform the reader owns, spelled here to quote it."""
    return f"FLAG_{key.upper().replace('-', '_')}"


def mentions(line: str, key: str) -> bool:
    """Whether one line is about this flag, in either spelling — the key, or the variable it becomes."""
    return key in line or variable_of(key) in line


def paths_tested(key: str, tests: list[tuple[str, str]]) -> tuple[bool, bool]:
    """Whether the tests that are about this flag drive it on, and whether they drive it off.

    The two halves are asked differently, because they are written differently. Turning the feature *on*
    can only be done by setting the flag, so the on path is a line naming both the key and the value `on`.
    The off path usually names no flag at all — the test drives the same code with an environment that has
    nothing in it — so it is an off value or an empty environment anywhere in a file that tests this flag.

    That asymmetry is the whole heuristic, and it is aimed at the failure that actually happens: one test,
    flag on, done. A file whose every line about the key sets it on, and which never once drives the code
    with the flag absent, has not been near the branch that is running in production.
    """
    lines = [line for _relative, text in tests if mentions(text, key) for line in text.splitlines()]
    on = any(mentions(line, key) and ON_VALUE.search(line) for line in lines)
    off = any(OFF_VALUE.search(line) for line in lines)
    return on, off


def git(*arguments: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", *arguments], cwd=ROOT, text=True, capture_output=True, check=True
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return completed.stdout


def declared_before() -> set[tuple[str, str]] | None:
    """What was already declared before this change, or None where there is no history to ask.

    On a branch that is the merge base with `main`; on `main` itself that is `HEAD`, so an uncommitted
    declaration is new. A repository with no history, and a shallow CI checkout with no base to compare
    with, are both treated as "cannot tell": rule 3 then says nothing rather than something false.
    """
    if git("rev-parse", "--is-inside-work-tree") is None:
        return None
    head = git("rev-parse", "HEAD")
    if head is None:
        return None
    base = head.strip()
    for candidate in ("origin/main", "main", "origin/master", "master"):
        merge_base = git("merge-base", "HEAD", candidate)
        if merge_base is not None:
            base = merge_base.strip()
            break
    earlier = git("show", f"{base}:{DECLARATION_NAME}")
    return set(declared(earlier or ""))


def seeds() -> dict[tuple[str, str], str]:
    """What this project declares now, keyed `(service, key)`."""
    return declared(DECLARATION.read_text()) if DECLARATION.is_file() else {}


def check() -> list[str]:
    if not DECLARATION.is_file():
        return [f"{DECLARATION_NAME} is missing. It is where a flag is declared; restore it from the factory."]
    seeded = seeds()
    services, sites = deployables()
    read_by: dict[str, set[str]] = {}
    tests: list[tuple[str, str]] = []
    # (file, key, suffix) for every read made by naming the variable — rule 5, reported per file and key
    # rather than per occurrence, because the fix is one edit however many times the file said it.
    bypasses: list[tuple[str, str, str]] = []
    # Files calling App Configuration directly. No key, because the source never names one.
    sdk_reads: list[str] = []
    for path in sources():
        relative = path.relative_to(ROOT).as_posix()
        text = COMMENTS.sub(" ", path.read_text(errors="ignore"))
        if is_test(path):
            # A test is not a read. Counted as one, a key declared, tested on both paths and never
            # actually consulted by the code would pass — which is the dead configuration rule 1 is for.
            tests.append((relative, text))
            continue
        for key in keys_in(text):
            read_by.setdefault(key, set()).add(owner_of(relative, services, sites) or "")
        bypasses += [(relative, key, path.suffix) for key in sorted(variables_in(text))]
        if READ_BY_SDK.search(text):
            sdk_reads.append(relative)

    violations: list[str] = []
    for relative, key, suffix in bypasses:
        call = READER_CALL.get(suffix, 'the reader, by key ("{key}")').format(key=key)
        violations.append(
            f"{relative}: reads {variable_of(key)} from the environment instead of asking the reader for "
            f"`{key}`. The reader is the only place this side touches the environment: it derives the "
            f"variable from the key in one spelling, so a typo cannot read as absent and absent as off; it "
            f"answers off for every value but `on`, including the window between this merge and the apply "
            f"that creates the secret; and it takes the environment as an argument, which is the seam "
            f"rule 4's two paths are driven through. A bare read has none of the three. Call {call} instead."
        )
    for relative in sdk_reads:
        violations.append(
            f"{relative}: reads App Configuration directly instead of asking the reader. Under "
            f"`flag_transport = \"appconfig\"` that store is where a value comes from, and the reader's "
            f"`defaultSource` is the one place that is allowed to know it — a slice that calls it directly "
            f"pins itself to one transport, loses the seam its tests drive both paths through, and names "
            f"no key at all, so nothing here can tell which flag it is reading or whether that flag is "
            f"declared. It also spreads the one cloud SDK this target puts in an image, which the reader "
            f"exists to confine. Ask by key through the reader and the transport stops being the slice's "
            f"business."
        )
    for key, owners in sorted(read_by.items()):
        # A read in shared code is satisfied by any service declaring the key; a read inside a service is
        # satisfied only by that service's own declaration, since that is the secret it is given.
        undeclared = [
            owner
            for owner in sorted(owners)
            if (owner, key) not in seeded
            and not (owner == "" and any(declared_key == key for _service, declared_key in seeded))
        ]
        if not undeclared:
            continue
        where = ", ".join(f"`{owner}`" if owner else "shared code under packages/" for owner in undeclared)
        service = next((owner for owner in undeclared if owner), "<service>")
        violations.append(
            f"{key}: read in {where} and declared nowhere, so it exists in no environment and can never "
            f"be turned on — which from the outside looks like a feature that shipped and was fine. "
            f'Declare it in {DECLARATION_NAME}: `{service} = {{ {key} = "off" }}`.'
        )
    before = declared_before()
    for (service, key), seed in sorted(seeded.items()):
        readers = read_by.get(key, set())
        if service not in readers and "" not in readers:
            violations.append(
                f"{service}/{key}: declared and read nowhere. A flag with nothing behind it is a secret "
                f"in every environment and a line in `make flags` that means nothing — delete the key, or "
                f"read it where the behaviour branches."
            )
            continue
        if before is not None and (service, key) not in before and seed != "off":
            violations.append(
                f'{service}/{key}: new in this change and seeded "{seed}". The seed is what a *new* '
                f"environment starts at, and a flag being introduced is not released yet — seed it "
                f'"off" and flip it with `make flag`, which is the only thing that can flip it: the '
                f"stack never touches a secret after creating it."
            )
        on, off = paths_tested(key, tests)
        if not (on and off):
            missing = "on or off" if not on and not off else ("on" if not on else "off")
            violations.append(
                f"{service}/{key}: no test appears to drive it {missing}. While a flag is off the branch "
                f"running in production is the one nothing covers, and the branch was inserted into that "
                f"path too — so both are this slice's to test. Drive the reader with the key set to `on` "
                f"and with it absent or `off`; the reader takes the environment as an argument for this."
            )
    return violations


def main() -> int:
    violations = check()
    if violations:
        print("check-flags: a feature flag is not held back the way it has to be\n", file=sys.stderr)
        for violation in violations:
            print(f"  {violation}", file=sys.stderr)
        print(file=sys.stderr)
        return 1
    total = len(seeds())
    if not total:
        print(f"check-flags: no flag is declared yet ({DECLARATION_NAME} is where the first one goes)")
    else:
        print(f"check-flags: {total} flag(s) declared, read, and tested on both paths")
    return 0


if __name__ == "__main__":
    sys.exit(main())
