#!/usr/bin/env python3
"""Re-project elected extension guidance without rerunning extension setup.

The projection itself is the `project` point of `hooks.py`'s closed set, fired through the registry like
every other point — which is what slice 6.1e closed. Until then this script imported each extension's
`init.py` and called a function called `project_guidance()` by name, so an extension that declared a
different script at that point was ignored: installed, valid, and silently never run.

What is still read from the module is `GUIDANCE`, and that is *data* rather than a point — the canonical
text of the block, which `--check` compares against what is in `AGENTS.md`. A drift check has to know what
the block should say, and a subprocess that writes it cannot answer that question.

Last, `guard_offer.py` says which elected extension has a guard nobody has agreed to, with the command that
agrees — and asks, where somebody is at a terminal. It never agrees for anybody.

And after the point has fired, a block still drifted is written from that same data (`rewrite_drifted`), so
an extension that attaches nothing to `project` is re-projected too and the fix `--check` names is one.
"""
from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

sys.dont_write_bytecode = True
from guidance import ROOT, adopted_extensions, canonical_block, installed_block, replace_block

HERE = Path(__file__).resolve().parent
HOOKS = HERE / "hooks.py"


def extension_module(key: str) -> ModuleType:
    script = HERE / key / "init.py"
    if not script.is_file():
        raise ValueError(f"{key}: elected extension has no {script.relative_to(ROOT)}")
    spec = importlib.util.spec_from_file_location(f"slipwai_extension_{key.replace('-', '_')}", script)
    if spec is None or spec.loader is None:
        raise ValueError(f"{key}: cannot load {script.relative_to(ROOT)}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # before it runs: a `@dataclass` in it looks its own module up by name
    spec.loader.exec_module(module)
    return module


def fire_project() -> list[str]:
    """The `project` point, through the registry. Never fatal, as a hook never is: `hooks.py` exits 0
    whatever a hook did, and what a failure produces is a `hook` line on stderr naming the extension."""
    try:
        subprocess.run([sys.executable, str(HOOKS), "project"], cwd=ROOT, check=False)
    except OSError as error:
        return [f"the project point could not be fired ({type(error).__name__})"]
    return []


def rewrite_drifted(adopted: list[str]) -> None:
    """Write each elected extension's block from its `GUIDANCE` where the `project` point left it drifted.

    The point is still fired first and still the extension's own. But an extension need not attach to it —
    `codegraph` 1.0.0 declares `init`, `after-stage` and `check` — and for one that does not, nothing here
    rewrote its block: `--check` named `make agents` as the fix and `make agents` changed nothing, so the
    only way out was to run the extension's whole set-up again. The block is the factory's region and its
    text is already read as data below, so the command the gate names now does what the gate says. An
    extension with no `GUIDANCE`, or one that cannot be loaded, is `--check`'s to report, never a reason the
    others go unwritten."""
    for key in adopted:
        try:
            guidance = extension_module(key).GUIDANCE
            if installed_block(key) != canonical_block(key, guidance):
                replace_block(key, guidance)
        except Exception:  # noqa: BLE001 — an extension's own module, run at import: anything may be raised
            continue


def project(check: bool) -> list[str]:
    findings: list[str] = []
    try:
        adopted = adopted_extensions(persist_legacy=not check)
    except (OSError, ValueError) as error:
        return [str(error)]
    if not check:
        said = fire_project()
        rewrite_drifted(adopted)
        return said
    for key in adopted:
        try:
            # `GUIDANCE` is the block's canonical text, read as data: the drift check has to know what the
            # block should say, which is not something the point that writes it can be asked.
            canonical = canonical_block(key, extension_module(key).GUIDANCE)
            if installed_block(key) != canonical:
                findings.append(
                    f"AGENTS.md: the {key} extension block has drifted from the GUIDANCE in "
                    f"{(HERE / key / 'init.py').relative_to(ROOT)}; `make agents` rewrites it, as "
                    "`slipwai migrate` does after a clean merge"
                )
        except (AttributeError, OSError, ValueError) as error:
            findings.append(str(error))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    findings = project(arguments.check)
    if findings:
        print("\n".join(f"check-extensions: {finding}" for finding in findings), file=sys.stderr)
        return 1
    adopted = adopted_extensions(persist_legacy=False)
    if not adopted:
        print("check-extensions: no extension elected; nothing to project")
    elif arguments.check:
        print(f"check-extensions: {len(adopted)} elected extension block(s) match")
    if not arguments.check:
        offer_guards()
    return 0


def offer_guards() -> None:
    """Say which elected extension has a guard nobody agreed to, and ask where somebody is at a terminal.

    `guard_offer.py` says the line and the command and changes nothing unless a person answers yes; it is
    its own script, with this process's terminal, and never a reason `make agents` fails."""
    script = HERE / "guard_offer.py"
    if not script.is_file():
        return
    try:
        subprocess.run([sys.executable, str(script), "--ask"], cwd=ROOT, check=False)
    except OSError:
        return


if __name__ == "__main__":
    raise SystemExit(main())
