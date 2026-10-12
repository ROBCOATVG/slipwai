"""The conformance profile a target package is held to: four checks, in the order a publisher meets them.

A language's suite asks the package questions and checks the answers against a generated project. An
extension's builds a scratch project and runs the entry point in it. A target's is a third shape again,
because what a target owes is neither a generated skeleton nor a script that runs in one: it is a
declaration the catalog can take a row from, a `TARGET` answering the protocol, and the files those answers
name.

1. **declaration** — `target.json` is a manifest this keel reads, and the name in it is the directory it
   is in. Nothing after this runs if it fails: a package the catalog could not take a row from is a package
   whose answers nobody would ever ask for.
2. **protocol** — the module imports, exports `TARGET`, and a managed target answers every required member
   with the kind the protocol wants. Run in a child (`target_probe`), because importing a package runs its
   code and a suite that ran it in its own process would be one a package could change the verdict of.
3. **shapes** — both stacks and every script are made of files the package actually ships. A stack made of
   files nobody ships applies nothing, and the first anybody would know of it is an apply that failed
   halfway through somebody's account.
4. **version** — `VERSION`, `CHANGELOG.md` and `changelog.d/` agree, which is the same rule every package
   of every kind is held to and the one nothing but a command can satisfy.

What is **not** here, deliberately: anything that reaches the cloud. A conformance suite that needed an
account would be one no contributor could run and no fork could gate on, and what it would prove is that
somebody's credentials work.
"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from ..target_shape import validate
from . import child
from .run import CORE_PATH
from .version_rule import problems

MANIFEST = "target.json"
#: The checks, in the order they run and are reported.
CHECKS = ("declaration", "protocol", "shapes", "version")
#: The two the probe runs: both need the package's own module imported.
PROBED = ("protocol", "shapes")
#: Why the probed checks did not run, when the declaration they would be read against is not one.
UNDECLARED = "its target.json is not one this keel reads, so there is nothing to read its answers against"


@dataclass
class Report:
    """What each check found. Empty findings is a pass; `not_run` says why one was not checked."""

    name: str
    findings: dict[str, list[str]] = field(default_factory=dict)
    not_run: dict[str, str] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return not self.not_run and not any(self.findings.values())

    def count(self) -> int:
        return sum(len(found) for found in self.findings.values())


def declaration(package: Path) -> tuple[dict | None, list[str]]:
    """The manifest this keel reads, or the one line saying why it is not one."""
    path = package / MANIFEST
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except OSError:
        return None, [f"{package} holds no {MANIFEST}, so it is not a target package"]
    except (ValueError, UnicodeDecodeError) as error:
        return None, [f"{path} is not valid JSON: {error}"]
    try:
        validate(manifest)
    except ValueError as error:
        return None, [str(error)]
    if manifest["name"] != package.name:
        return None, [f"{MANIFEST}'s name is {manifest['name']}, and its directory is {package.name}. The two "
                      f"are one thing: the catalog lists a target under the name its directory is called"]
    return manifest, []


def probed(package: Path, name: str, managed: bool) -> tuple[dict[str, list[str]], dict[str, str]]:
    """Run the two checks that need the package imported, in an interpreter of their own.

    A probe that cannot report — a crash of the suite itself, or a package that ended the process while it
    was imported — is both checks not run, naming the last line it printed. Never a pass, and never a
    finding about the package: the suite does not know which it would be.
    """
    path = os.pathsep.join([str(CORE_PATH), *filter(None, [os.environ.get("PYTHONPATH")])])
    with tempfile.TemporaryDirectory(prefix="slipwai-target-") as scratch:
        destination = Path(scratch) / "report.json"
        done = child.run("slipwai.conformance.target_probe",
                         [str(package), name, "managed" if managed else "unmanaged", str(destination)],
                         {**os.environ, "PYTHONPATH": path})
        try:
            said = json.loads(destination.read_text(encoding="utf-8", errors="replace"))
        except (OSError, ValueError):
            said = None
    if not isinstance(said, dict) or not all(isinstance(said.get(key), dict) for key in ("findings", "not_run")):
        why = (f"the probe for {name} did not report (exit {done.returncode}); the package's import is the "
               f"likely cause if it ended the process. Last line: {done.last_line()}")
        return {}, dict.fromkeys(PROBED, why)
    findings = {key: value for key, value in said["findings"].items() if key in PROBED}
    return findings, {key: str(value) for key, value in said["not_run"].items() if key in PROBED}


def check(package: Path) -> Report:
    """Run the four against the package in `package`, and say what each found."""
    whole = package.resolve()
    report = Report(whole.name)
    manifest, refused = declaration(whole)
    report.findings["declaration"] = refused
    if manifest is None:
        report.not_run.update(dict.fromkeys(PROBED, UNDECLARED))
    else:
        findings, not_run = probed(whole, manifest["name"], bool(manifest.get("managed")))
        report.findings.update(findings)
        report.not_run.update(not_run)
    report.findings["version"] = problems(whole)
    return Report(report.name, {name: report.findings[name] for name in CHECKS if name in report.findings},
                  {name: report.not_run[name] for name in CHECKS if name in report.not_run})


__all__ = ["CHECKS", "Report", "check"]
