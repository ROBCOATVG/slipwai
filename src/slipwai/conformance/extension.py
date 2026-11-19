"""The six obligations, run rather than described.

A language's conformance suite asks the package questions and checks the answers. An extension answers
nothing — it is a script that runs in a project and changes it — so its suite is the other shape: build a
scratch project, run the entry point in it, and look at what happened to the project.

**What it is run against is a scratch project, not a generated one.** Generating one needs a language
installed, which an extension's publisher has no reason to have, and the obligations are all about files an
extension touches rather than about any language's skeleton. So the scratch project is `project.json`, an
`AGENTS.md` with a person's paragraph in it, and the package's own files where `./init` would put them.

**Four of the six are run; two are read.** `idempotent`, `non-fatal`, `projects` and `merges` are facts
about what the entry point did, and they are checked by doing it twice. `gated` is a fact about what the
package ships. `recovers` is checked against what the entry point actually printed: a line reporting a
problem that carries no command is the failure that obligation exists to stop, and a line nobody printed is
not something this can check — so the suite says which lines it read rather than claiming more.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from ..assets import TOOLKIT_ROOT
from ..extension_directory import MANIFEST, absent, files
from ..extension_shape import obligations
from ..hooks import declared

#: The person's paragraph the scratch project starts with. Obligations 3 and 6 are both about this surviving.
PERSONS_WORDS = "This paragraph was written by a person and no install may take it away.\n"
#: What a line has to be saying for `recovers` to want a command in it.
TROUBLE = re.compile(r"\b(cannot|could not|couldn't|failed|failing|missing|not found|unavailable|no such"
                     r"|did not finish|exited [1-9])\b", re.IGNORECASE)
#: What counts as naming the way out: a backticked span, or something that reads like a command line.
#: `./init` is outside the `\b` on purpose. A word boundary needs a word character on one side, and the
#: character before `.` in `  ./init --extension uipro` is a space — so `\b\./init` could never match, and
#: the one remedy every extension names was the one this could not see.
REMEDY = re.compile(r"`[^`]+`"
                    r"|(?:\b(?:brew|npm|pip|pipx|uv|cargo|go|apt|dnf|make|slipwai)\b|\./init)[ \t]+\S")
BUDGET = 120.0
#: Held before the six and beside them: not something the entry point does, but whether the package is whole.
SHIPS = ("ships", "every hook and guard the manifest declares names a file the package ships")


@dataclass
class Report:
    """What each obligation found. Empty findings is a pass; `not_run` says why one was not checked."""

    key: str
    findings: dict[str, list[str]] = field(default_factory=dict)
    not_run: dict[str, str] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return not any(self.findings.values())

    def count(self) -> int:
        return sum(len(found) for found in self.findings.values())


def scratch(root: Path, key: str, package: Path) -> Path:
    """A project the way `./init` would leave one before the extension runs: the files, and a person's words.

    The toolkit's whole `scripts/` tree goes in with it. None of it is the package's, but an entry point is
    entitled to import it — `extensions/guidance.py` is how an extension records its election and writes
    each harness's MCP file — and a scratch project without it fails every obligation at the import line,
    which is a fact about the scratch project and not about the extension. What the toolkit does *not*
    carry is anything belonging to one extension: since slice 6.1c a tool's own pinned release, its CLI
    wrapper and its guard live in its package, so an entry point that imported one of those from here was
    importing a file the keel stopped shipping.
    """
    project = root / "project"
    place = project / "scripts/extensions" / key
    place.mkdir(parents=True)
    for shared in sorted((TOOLKIT_ROOT / "scripts").rglob("*")):
        if shared.is_file():
            target = project / "scripts" / shared.relative_to(TOOLKIT_ROOT / "scripts")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(shared.read_bytes())
    for relative in files(package):
        target = place / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((package / relative).read_bytes())
    (project / "project.json").write_text("{}\n", encoding="utf-8")
    (project / "AGENTS.md").write_text(f"# A project\n\n{PERSONS_WORDS}", encoding="utf-8")
    return project


def entry_point(manifest: dict) -> str:
    """The script the `init` hook names, which is the one an election runs."""
    hooks = declared(manifest)
    return str(hooks.get("init", {}).get("run", "init.py"))


def ran(project: Path, key: str, script: str, path: str | None = None) -> subprocess.CompletedProcess:
    """The entry point, in the project, as `./init` runs it. `path` empties `PATH` for the non-fatal check."""
    import os
    environment = {**os.environ, "SLIPWAI_INTEGRATION": "claude"}
    if path is not None:
        environment["PATH"] = path
    return subprocess.run([sys.executable, str(project / "scripts/extensions" / key / script)],
                          capture_output=True, text=True, cwd=project, timeout=BUDGET, env=environment)


def snapshot(project: Path) -> dict[str, bytes]:
    """Every file in the project, so two runs can be compared as a whole rather than file by file."""
    return {path.relative_to(project).as_posix(): path.read_bytes()
            for path in sorted(project.rglob("*")) if path.is_file()}


def differences(first: dict[str, bytes], second: dict[str, bytes]) -> list[str]:
    """What the second run changed that the first did not — which is what `idempotent` means."""
    found = [f"{name} appeared only on the second run" for name in sorted(set(second) - set(first))]
    found += [f"{name} was removed by the second run" for name in sorted(set(first) - set(second))]
    return found + [f"{name} differs between the first run and the second"
                    for name in sorted(set(first) & set(second)) if first[name] != second[name]]


def fenced(text: str, key: str) -> list[str]:
    """Whether the project's `AGENTS.md` carries one marker-fenced block for this extension.

    The markers are the toolkit's own — `<!-- extension:<key>:begin -->` — which `scripts/extensions/
    guidance.py` writes and reads. Matched on the inner spelling so a block written by hand around the
    same words passes too; what the obligation is about is one block, bounded, replaceable whole.
    """
    opens = len(re.findall(rf"extension:{re.escape(key)}:begin", text))
    closes = len(re.findall(rf"extension:{re.escape(key)}:end", text))
    if opens == 1 and closes == 1:
        return []
    if opens == 0 and closes == 0:
        return [f"AGENTS.md has no `<!-- extension:{key}:begin -->`/`:end` block. The next projection replaces "
                f"exactly what is between the markers, so an unfenced block is one nothing can replace"]
    return [f"AGENTS.md has {opens} begin marker(s) and {closes} end marker(s); one block is fenced by one pair"]


def messages(output: str) -> list[list[str]]:
    """What was printed, grouped into messages: a line reporting a problem and the lines under it.

    Per message and not per line, because that is how every one of these is actually written — the trouble,
    then `Install it:`, then the command, indented. Read line by line, the first line of every real message
    fails and the command two lines below it is never seen; read this way, a trouble line with nothing after
    it still fails, which is what the obligation is about.
    """
    found: list[list[str]] = []
    for line in output.splitlines():
        if TROUBLE.search(line):
            found.append([line])
        elif found:
            found[-1].append(line)
    return found


def unsaid(output: str) -> list[str]:
    """Every message reporting a problem without naming the command that fixes it."""
    return [f"said {message[0].strip()!r} and named no command to fix it"
            for message in messages(output) if not REMEDY.search("\n".join(message))]


def gated(package: Path, manifest: dict) -> list[str]:
    """A package that leaves local state ships the check that refuses a stale one.

    What the *package* ships, not what is in the project: a gate the keel happens to carry is a gate that
    goes away the moment the keel stops carrying it, and the obligation is the package's.
    """
    if not manifest.get("ignore"):
        return []
    key = manifest["key"]
    if any(path.name == f"check-{key}.py" for path in files(package)):
        return []
    if "check" in declared(manifest):
        return []
    return [f"`ignore` says this leaves state behind, and the package ships no check-{key}.py and declares no "
            f"`check` hook. State that can go stale and that nothing checks is state nobody trusts and "
            f"everybody rebuilds"]


def unshipped(package: Path, manifest: dict) -> list[str]:
    """A finding for each declared hook or guard whose script is not in the package, naming the point and the path.

    Only `init` used to be looked for, and a package missing that one was reported as not run, which is a pass. So a
    package could declare a hook at any point, not ship its file, pass here and be published: the hook then never
    runs in any project (#117).
    """
    return [f"the `{name}` {kind} names {path}, which the package does not ship. Nothing is run at `{name}` in "
            f"any project that elects this: add the file, or take the declaration out of {MANIFEST}"
            for kind, name, path in absent(package, manifest)]


def check(package: Path) -> Report:
    """Run the six against the package in `package`, and say what each found."""
    manifest = json.loads((package / MANIFEST).read_text(encoding="utf-8"))
    key = manifest["key"]
    report = Report(key)
    report.findings[SHIPS[0]] = unshipped(package, manifest)
    script = entry_point(manifest)
    with tempfile.TemporaryDirectory() as area:
        project = scratch(Path(area), key, package)
        if not (project / "scripts/extensions" / key / script).is_file():
            for name in obligations():
                report.not_run[name] = f"its `init` hook names {script}, which the package does not ship"
            return report
        try:
            first = ran(project, key, script)
            after_first = snapshot(project)
            second = ran(project, key, script)
            after_second = snapshot(project)
        except subprocess.TimeoutExpired:
            for name in obligations():
                report.not_run[name] = f"the entry point did not finish inside {BUDGET:.0f}s"
            return report
        said = first.stdout + first.stderr + second.stdout + second.stderr
        report.findings["idempotent"] = differences(after_first, after_second)
        words = (project / "AGENTS.md").read_text(encoding="utf-8")
        # An entry point that stopped before the block and said why, with the way forward, never got as far
        # as writing one — and that is obligation 2 working rather than obligation 3 failing. Said as `not
        # run`, so a publisher on a machine that has what it wanted sees the real answer.
        #
        # *Stopped and gave a way on*, not *its tool is missing*: a missing tool was the only case this
        # allowed for, and it was recognised by words like `not found`. The scratch project is deliberately
        # bare, so an extension that acts on a browser app correctly does nothing here and says so — `UI/UX
        # Pro Max designs screens, and this project has no browser app for it to design` — which reports no
        # trouble in those words and was failed for it. What makes a stop legitimate is that it names the
        # way on, which is the same thing obligation 6 asks of every line that does report trouble. An
        # entry point that writes no block and says nothing at all still fails, which is the case this is
        # for.
        if words == f"# A project\n\n{PERSONS_WORDS}" and REMEDY.search(said) and not unsaid(said):
            report.not_run["projects"] = ("it stopped before writing the block and said why, with the way "
                                          "on — which is obligation 2 working. Run this again where it has "
                                          "what it wanted to check obligation 3")
        else:
            report.findings["projects"] = fenced(words, key)
        report.findings["merges"] = ([] if PERSONS_WORDS.strip() in words
                                     else ["AGENTS.md lost what a person wrote in it"])
        report.findings["gated"] = gated(package, manifest)
        report.findings["recovers"] = unsaid(said)
    report.findings["non-fatal"] = non_fatal(package, key, script)
    return report


def non_fatal(package: Path, key: str, script: str) -> list[str]:
    """A second scratch project with nothing on `PATH`: whatever it cannot install, it may not be fatal.

    A fresh project rather than the one the other checks used, because what this is asking about is the first
    run on a machine that has none of the tools — not a second run over a project already set up.
    """
    with tempfile.TemporaryDirectory() as bare:
        try:
            run = ran(scratch(Path(bare), key, package), key, script, path="")
        except subprocess.TimeoutExpired:
            return [f"with nothing on PATH it did not finish inside {BUDGET:.0f}s"]
    if run.returncode == 0:
        return []
    return [f"with nothing on PATH it exited {run.returncode}. A dev tool that is not on this machine is not "
            f"a reason a project cannot be set up: say what is missing and leave the project working"]


__all__ = ["SHIPS", "Report", "check"]
