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

`--only <key>...` is that projection for the extensions it names and nothing more, and is what
`guards.py --elect` and `--remove` run: an extension's block may say whether its guard is agreed to, so the
command that changes the agreement brings that extension's guidance up to date before it returns, and a
person who did what they were told is not left with a red `make check-extensions`. It says, per extension,
what it did, and exits 0 whatever a hook did — the agreement is the registry, never this.
"""
from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

sys.dont_write_bytecode = True
from guidance import AGENTS, ROOT, adopted_extensions, canonical_block, installed_block, replace_block

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


def drifted(key: str) -> bool | None:
    """Whether this extension's block differs from its `GUIDANCE` now. None where nothing can say: no
    `AGENTS.md`, or no `GUIDANCE` that can be read."""
    if not AGENTS.is_file():
        return None
    try:
        return installed_block(key) != canonical_block(key, extension_module(key).GUIDANCE)
    except Exception:  # noqa: BLE001 — an extension's own module, run at import: anything may be raised
        return None


def only(keys: list[str]) -> int:
    """Bring the guidance of each extension `keys` names up to date, as `make agents` would, and say so.

    Its `project` hook where it attaches one — fired for it alone, with what `make agents` hands it, so it
    reads the agreement as it is now — and then its block from its `GUIDANCE` where that is still drifted.
    A hook that crashed or ran out its budget is `hooks.py`'s `hook` line and a sentence here naming the
    command that runs it again; it is never an exit code, because what called this has already recorded a
    person's answer and a hook is not a reason that answer failed."""
    try:
        adopted = adopted_extensions(persist_legacy=False)
    except (OSError, ValueError) as error:
        print(f"guards: which extensions are elected here could not be read ({error})", file=sys.stderr)
        return 1
    import hooks  # beside this script; asked for here so a plain projection still runs it as its own process
    attached = {body.get("extension") for body in hooks.read(hooks.REGISTRY).get("points", {}).get("project", [])
                if isinstance(body, dict)}
    for key in sorted(set(keys)):
        if key not in adopted:
            print(f"guards: {key} is not elected here, so it has no guidance to bring up to date")
            continue
        failed = key in attached and hooks.fire("project", {}, fatal=True, only=key) != 0
        sys.stdout.flush()
        behind = drifted(key)
        rewrite_drifted([key])
        stale = drifted(key)
        hook = f"guards: {key}'s `project` hook did not finish (the `hook {key} project` line above)"
        if failed and stale is False:
            print(f"{hook}. The agreement is recorded and stands, and {key}'s AGENTS.md block was written from "
                  "its GUIDANCE, so it is current; `make agents` runs the hook again for anything else it does.",
                  file=sys.stderr)
        elif failed:
            print(f"{hook}, so what {key} says in AGENTS.md may be as it was before this agreement changed. "
                  "The agreement is recorded and stands; `make agents` runs the hook again.", file=sys.stderr)
        elif stale:
            print(f"guards: {key}'s AGENTS.md block still differs from its GUIDANCE, and nothing here could "
                  "write it. The agreement is recorded and stands; `make check-extensions` says what is wrong "
                  "with the block.", file=sys.stderr)
        elif key in attached:
            print(f"guards: {key}'s guidance is up to date with this agreement: its `project` hook ran")
        elif stale is False:
            how = "was written from" if behind else "already matches"
            print(f"guards: {key}'s guidance is up to date with this agreement: its AGENTS.md block {how} "
                  "its GUIDANCE")
        else:
            print(f"guards: {key} attaches nothing to `project` and has no block to write, so it had no "
                  "guidance to bring up to date")
    return 0


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
    parser.add_argument("--only", nargs="+", metavar="KEY")
    arguments = parser.parse_args()
    if arguments.only:
        return only(arguments.only)
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

    First `guard_harness.py` has the harness tell an agreed guard about the tools it declared it `sees`,
    which is a row of a file a clone does not have until this runs. Then `guard_offer.py` says the line and the command and changes nothing unless a person answers yes; it is
    its own script, with this process's terminal, and never a reason `make agents` fails.

    **Asked last, after the projection, and a yes is still in this run's guidance.** A yes runs the command
    the line names — `guards.py --elect` — and that command brings the agreeing extension's guidance up to
    date itself (`--only`), so the block is not one step behind what was just answered. Asking first would
    do it too, and would put a question that waits for a person above everything this run then prints, and
    make a run with nobody there differ from one with somebody for no gain."""
    for name, arguments in (("guard_harness.py", []), ("guard_offer.py", ["--ask"])):
        script = HERE / name
        if not script.is_file():
            continue
        try:
            subprocess.run([sys.executable, str(script), *arguments], cwd=ROOT, check=False)
        except OSError:
            continue


if __name__ == "__main__":
    raise SystemExit(main())
