#!/usr/bin/env python3
"""Check once, in a fresh worktree, that an increment can run here — before any delegate finds out for itself.

    python3 scripts/agents/preflight.py          # every check, one line each; exit 1 on any FAIL
    python3 scripts/agents/preflight.py --json   # the same as a record

One run's delegates discovered the same environment in series: Go's build cache was not writable, then
Staticcheck's was not, then a test could not bind a local socket, then the browser harness was missing and a
suite crashed while trying to skip, and several delegates in unindexed checkouts tried the code index route
that was not there. Each cost a dispatch, a return and a host repair, and none of it was about the product.
A worktree is made once per slice; this is the moment to ask those questions, once, and fix the answers
before a delegate meets them.

The checks are read off `project.json`: each deployable's language names a toolchain and a cache, the elected
extensions say whether an index should be present, and the rest — a Python the gate scripts can run on, a
socket a test may bind — is every project's. A language nobody here has a check for is said so, not skipped
silently: *no check recorded* is an honest line and *ok* would be a lie.

Standalone and dependency-free: this ships inside a generated project, which has no slipwai to import.
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

try:
    import harness  # noqa: E402
except ImportError:  # pragma: no cover - a checkout holding this script and not its siblings
    # Carried on without, rather than crashed on. Every other check here is about whether an increment can
    # run, and a missing sibling is a reason to say one question could not be asked — never a reason to
    # stop asking the rest.
    harness = None  # type: ignore[assignment]


def project_root(script: Path) -> Path:
    here = script.resolve().parent
    for candidate in (here, *here.parents):
        if (candidate / "project.json").is_file():
            return candidate
    return script.resolve().parents[2]


ROOT = project_root(Path(__file__))
MANIFEST = ROOT / "project.json"
EXTENSIONS = ROOT / ".slipwai/extensions.json"
#: What `--record` writes and `dispatch.py` reads. This checkout's own answer, never committed and never
#: travelled: another machine's preflight is not evidence about this one.
RECORD = ROOT / ".slipwai/preflight.json"
#: Extensions whose election says a directory should be in the checkout for a delegate to query it.
INDEXED = {"codegraph": ".codegraph"}


def run(*command: str) -> tuple[int, str]:
    try:
        done = subprocess.run(list(command), capture_output=True, text=True, timeout=60, cwd=ROOT)
    except (OSError, subprocess.TimeoutExpired) as error:
        return 1, f"{type(error).__name__}: {error}"
    return done.returncode, (done.stdout or done.stderr).strip()


def check(name: str, ok: bool | None, what: str, fix: str = "") -> dict:
    """One line of the report. `ok` None is *no check recorded* — said, never counted as a pass."""
    return {"check": name, "ok": ok, "what": what, "fix": fix}


def writable(path: str) -> bool:
    target = Path(path).expanduser()
    try:
        target.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=target):
            pass
    except OSError:
        return False
    return True


def python_checks() -> list[dict]:
    found = [check("python", sys.version_info >= (3, 10), f"{sys.executable} is Python {sys.version.split()[0]}",
                   "put a python3 of 3.10 or newer first on PATH (a non-interactive macOS shell finds /usr/bin/python3 first)")]
    try:
        import yaml  # noqa: F401
        found.append(check("pyyaml", True, "PyYAML imports, so clearance and the chart can be read"))
    except ImportError:
        found.append(check("pyyaml", False, "PyYAML is not installed in this Python, and clearance.py reads the chart with it",
                           f"{sys.executable} -m pip install PyYAML"))
    return found


def socket_check() -> dict:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as held:
            held.bind(("127.0.0.1", 0))
            held.listen(1)
            port = held.getsockname()[1]
    except OSError as error:
        return check("socket", False, f"a test cannot bind a localhost socket here ({error})",
                     "run the increment outside the sandbox that refuses local sockets, or allow them in its policy")
    return check("socket", True, f"a test may bind a localhost socket (tried port {port})")


def go_checks(path: str) -> list[dict]:
    if shutil.which("go") is None:
        return [check(f"go:{path}", False, "`go` is not on PATH", "install Go, or put it first on PATH")]
    _code, version = run("go", "version")
    found = [check(f"go:{path}", True, version or "go is on PATH")]
    for variable in ("GOCACHE", "GOMODCACHE"):
        code, where = run("go", "env", variable)
        if code or not where:
            found.append(check(f"go-{variable.lower()}:{path}", False, f"`go env {variable}` answered nothing",
                               "run `go env` by hand and read what it says"))
            continue
        found.append(check(f"go-{variable.lower()}:{path}", writable(where), f"{variable} is {where}",
                           f"chmod -R u+w {where}, or point {variable} somewhere this user can write"))
    return found


def node_checks(path: str) -> list[dict]:
    if shutil.which("node") is None:
        return [check(f"node:{path}", False, "`node` is not on PATH", "install Node, or put it first on PATH")]
    _code, version = run("node", "--version")
    found = [check(f"node:{path}", True, f"node {version}")]
    modules = next((where for where in (ROOT / path / "node_modules", ROOT / "node_modules") if where.is_dir()), None)
    found.append(check(f"node_modules:{path}", modules is not None,
                       f"dependencies installed at {modules.relative_to(ROOT)}" if modules else "no node_modules beside the app or at the root",
                       "make install (npm ci)"))
    return found


TOOLCHAINS = {"go": go_checks, "typescript": node_checks, "javascript": node_checks}


def deployable_checks(manifest: dict) -> list[dict]:
    found: list[dict] = []
    for name, deployable in (manifest.get("deployables") or {}).items():
        if not isinstance(deployable, dict):
            continue
        language = str(deployable.get("language") or "")
        path = str(deployable.get("path") or name)
        checker = TOOLCHAINS.get(language)
        if checker is None:
            found.append(check(f"{language or 'unknown'}:{path}", None, f"no check recorded for a {language or 'unnamed'} deployable"))
            continue
        found.extend(checker(path))
    return found


def index_checks() -> list[dict]:
    try:
        elected = json.loads(EXTENSIONS.read_text(encoding="utf-8")).get("extensions") or []
    except (OSError, ValueError, AttributeError):
        elected = []
    found = []
    for extension, directory in INDEXED.items():
        if extension in elected:
            present = (ROOT / directory).is_dir()
            found.append(check(f"index:{extension}", present,
                               f"{directory}/ is {'present' if present else 'missing'} in this checkout, and {extension} is elected",
                               f"bring the index up in this worktree before dispatching, or every delegate will try the route and fall back to text search"))
    return found


def method_checks() -> list[dict]:
    """Whether the method itself can run in this checkout, which no other gate asks.

    `project.py --check` deliberately passes where the projections are absent — *not drift, a clone
    `./init` has not run in* — and it is right to, because it cannot tell a clone nobody will run `/sail`
    in from one somebody is about to. Here that distinction is gone: this runs because a slice is about to
    start. So absence is a failure here and nowhere else.

    One run asked a method built on delegates to fan out in a checkout holding none of them, decided it was
    working alone, and spent eleven hours proving it. Neither half of that is a judgement either — both are
    one question to the registry and one to the filesystem, and they are these two lines.
    """
    if harness is None:
        return [check("delegates", None, "harness.py is not beside this script, so nothing here can say "
                                         "whether this session may delegate",
                      "run this from a project's own scripts/agents/, where its siblings are")]
    answer = harness.can_delegate()
    where, declared = answer.get("where") or "", answer.get("declared") or []
    if answer["able"]:
        return [check("delegates", True, answer["why"])]
    if not where or not declared:
        # Thirty of the registry's thirty-six rows have no sub-agents at all, so *cannot delegate* is the
        # ordinary answer here and not a broken checkout. Recorded, never failed: a gate that refused every
        # harness without delegates would refuse most of them, and be turned off in a week.
        return [check("delegates", None, answer["why"],
                      "run the ready set one slice at a time, and let the dispatch ledger carry this reason")]
    return [check("delegates", False, answer["why"], "run `make agents`, then start a new session")]


def checks() -> list[dict]:
    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        manifest = {}
    return [*python_checks(), socket_check(), *deployable_checks(manifest if isinstance(manifest, dict) else {}),
            *index_checks(), *method_checks()]


def record(found: list[dict], failed: list[dict]) -> dict:
    """What this run answered, as the file `dispatch.py` reads before it will write a ledger line.

    Under `.slipwai/`, so it is this checkout's and never committed: what a *different* machine's preflight
    found is not evidence about this one, and a record that travelled would be exactly the wrong thing to
    trust. The timestamp is the whole point — a dispatch stands on an answer from this checkout, now.
    """
    answer = {"v": 1, "at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
              "root": str(ROOT), "checks": found, "failed": len(failed),
              "delegates": next((row["ok"] for row in found if row["check"] == "delegates"), None),
              "why": next((row["what"] for row in found if row["check"] == "delegates"), "")}
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    RECORD.write_text(json.dumps(answer, indent=1) + "\n", encoding="utf-8")
    return answer


def main(argv: list[str]) -> int:
    found = checks()
    failed = [row for row in found if row["ok"] is False]
    if "--record" in argv:
        record(found, failed)
    if "--json" in argv:
        print(json.dumps({"v": 1, "root": str(ROOT), "checks": found, "failed": len(failed)}))
        return 1 if failed else 0
    for row in found:
        word = {True: "ok  ", False: "FAIL", None: "none"}[row["ok"]]
        fix = f" — {row['fix']}" if row["ok"] is False and row["fix"] else ""
        print(f"preflight: {word} {row['check']}: {row['what']}{fix}")
    if failed:
        print(f"preflight: {len(failed)} check(s) failed in {ROOT}; fix them here, once, before any delegate meets them")
        return 1
    print(f"preflight: {len(found)} check(s), nothing failed in {ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
