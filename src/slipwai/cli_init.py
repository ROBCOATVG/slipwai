"""What `adopt` says about the coding agent, and the `./init` run `adopt` and `generate` can each end with.

Brownfield adoption (#74; experimental as `AGENTS.md` defines the word). `harness.py` establishes which
harness the material is for and `init_script.py` generates the script; this is the edge between them — the
report's line about what was established and how, running the script once the adoption is committed, and
bringing the record up to what `./init` settled where `adopt` itself could not tell.

`generate` ends with the same run (`bootstrap`), so a new project is not a second command away from having
Spec Kit and its agent's skills. `./init` is a `/bin/sh` script, and a native Windows shell cannot run one:
there it goes through Git for Windows' `sh` when that is installed, and otherwise the run is not attempted
and the person is told which of WSL or Git Bash to reach for — never a failure half-way through.

What that setup needs is put on the machine rather than asked for: the coding agent is asked here, with no
answer preselected, instead of leaving Spec Kit's own list (which highlights Copilot) to ask it; and every
tool the choices imply — uv and Python for `./init`, each language's toolchain, the cloud's CLIs — is
installed through `host.ensure`, `sudo` included. On by default wherever somebody answered at a terminal;
`--install` asks for it from a script, `--no-install` turns it off, and `SLIPWAI_NO_INSTALL=1` carries that
into `./init` and every extension it runs.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

from .harness import Agent, from_environment, from_spec_kit, keys, name_of
from .host import TOOLCHAINS, Host, detect, disabled, ensure, install_hint, present


def add_setup_arguments(parser: argparse.ArgumentParser, script: str) -> None:
    """The flags `generate` and `adopt` share for what follows the files: the agent, `./init`, the installs."""
    parser.add_argument(
        "--integration", default=None, metavar="AGENT",
        help="which coding agent gets the skills and commands, by its key in the agent registry (default: the one "
        "this runs inside, or the one the tree reads; otherwise it is asked, with nothing preselected)",
    )
    init = parser.add_mutually_exclusive_group()
    # `default=None` on every half, so that "nobody said" is one value rather than two.
    init.add_argument(
        "--init", action="store_true", dest="run_init", default=None,
        help=f"run {script} once the files are committed (the default at a terminal): Spec Kit, the agent's "
        "skills and commands, and the extensions; it needs the network, and what it writes is left to commit",
    )
    init.add_argument("--no-init", action="store_false", dest="run_init", default=None,
                      help=f"do not run {script}; leave it as the next step")
    install = parser.add_mutually_exclusive_group()
    install.add_argument(
        "--install", action="store_true", dest="install", default=None,
        help="install every tool the answers need that is missing, through this machine's package manager (sudo "
        "included) or the publisher's download (the default at a terminal)",
    )
    install.add_argument("--no-install", action="store_false", dest="install", default=None,
                         help="install nothing; say what is missing instead")


def installing(flag: bool | None, attended: bool) -> bool:
    """Whether to install: as the flags said, else wherever somebody is at a terminal, and never under the
    environment's own opt-out."""
    if disabled():
        return False
    return flag if flag is not None else attended


def prompt_agent(candidates: tuple[str, ...] = ()) -> str:
    """Which coding agent gets the material, asked with no answer preselected — the candidates the tree reads
    for first, where there are any, then the rest of the registry in its own order."""
    from .cli_prompts import prompt_choice  # the question lives with the others; imported here to stay acyclic

    options = [*candidates, *(key for key in keys() if key not in candidates)]
    return prompt_choice(
        "Coding agent", options, None, name_of,
        question="Which coding agent gets the skills and commands? (↑/↓ and Enter; `./init --integration <agent>` "
        "changes it later)",
    )


def agent_for_setup(named: str | None, asking: bool) -> str | None:
    """The agent `generate`'s setup is for: named, else the one this runs inside, else asked, else nobody."""
    if named:
        return named
    inside = from_environment()
    if inside is not None:
        return inside.harness
    return prompt_agent() if asking else None


def tools_for(languages: list[str], *, base: tuple[str, ...] = ("git", "make", "uv", "python3")) -> list[str]:
    """What the setup and each language's own build need on the machine, in the order they are needed."""
    needed = list(base)
    for language in languages:
        needed += [tool for tool in TOOLCHAINS.get(language, ()) if tool not in needed]
    return needed


def install_tools(tools: list[str], install: bool) -> list[str]:
    """Put `tools` on the machine where `install` allows it; say what could not be, and return that."""
    if not install:
        return []
    missing = ensure(tools)
    for tool in missing:
        print(f"Could not install {tool} here; {install_hint(tool, 'its own install page')} is the line to try.")
    return missing


def agent_line(agent: Agent) -> str:
    """What the report says about which coding agent the material is for, and how that was established."""
    if agent.harness:
        established = "named" if agent.provenance == "overridden" else agent.evidence
        return (
            f"Agent: {name_of(agent.harness)} ({established}), recorded in project.json. `./init` projects the "
            f"skills and commands into it without asking; `--integration <agent>` there changes it."
        )
    if agent.candidates:
        named = ", ".join(name_of(key) for key in agent.candidates)
        return (
            f"Agent: not recorded — this tree reads for more than one ({named}), and which of them gets the "
            "material is a decision, not a guess. `./init` asks."
        )
    return (
        "Agent: not recorded — nothing here says which one, and this did not run from inside one. `./init` asks, "
        "or `./init --integration <agent>` names it."
    )


def record_agent(root: Path, agent: Agent) -> str:
    """`project.json`'s `agent`, brought up to what `./init` settled, and what to say about it.

    Only where `adopt` had nothing to record: an answer it already had is the one `./init` was given, and a
    record a person overrode is not something a later step gets to move.
    """
    if agent.harness:
        return f"The record already named {name_of(agent.harness)}, and `./init` was given it."
    settled = from_spec_kit(root)
    if settled is None or settled.harness is None:
        return "`./init` recorded no integration, so project.json's agent stays the open question it was."
    manifest = root / "project.json"
    document = json.loads(manifest.read_text(encoding="utf-8"))
    document["agent"] = settled.record()
    manifest.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8", newline="\n")
    return (
        f"Agent: {name_of(settled.harness)} — `./init` asked, and project.json now records the answer "
        "(`confirmed`). That is one more uncommitted change for you to read."
    )


def git_sh() -> str | None:
    """The `sh.exe` Git for Windows ships beside `git.exe`, which is on PATH even where its `bin/` is not."""
    git = shutil.which("git")
    if git is None:
        return None
    # `<Git>/cmd/git.exe` or `<Git>/bin/git.exe`; `sh.exe` lives in `<Git>/bin/` either way.
    candidate = Path(git).resolve().parent.parent / "bin" / "sh.exe"
    return str(candidate) if candidate.is_file() else None


def launcher(host: Host, install: bool = False) -> list[str] | str:
    """What runs a `/bin/sh` script on this machine, or why nothing here can — said with the way past it.

    `./init` needs `python3` whatever else it finds, for the agent projection it ends with, so its absence is
    said before the run rather than after Spec Kit has been fetched for nothing.
    """
    if not present("python3") and install:
        ensure(["python3"])  # missing, or too old for the gate scripts (a stock Mac's 3.9)
    if shutil.which("python3") is None:
        return (
            f"./init needs python3, and this machine ({host.name}) has none on PATH. Install it with "
            f"{install_hint('python3', 'https://www.python.org/downloads/', host)}, then run ./init."
        )
    if host.posix:
        return []
    sh = shutil.which("sh") or git_sh()
    if sh is None and install:
        ensure(["git"])  # Git for Windows is what brings `sh`
        sh = shutil.which("sh") or git_sh()
    if sh is None:
        return (
            "./init is a POSIX shell script, and this is a native Windows shell with no `sh` to run it. Run it "
            "inside WSL (`wsl --install`, then work from the Linux side), or from Git Bash — "
            f"{install_hint('git', 'https://git-scm.com/download/win', host)} installs it."
        )
    return [sh]


def bootstrap(root: Path, script: Path, integration: str | None, install: bool = False) -> bool:
    """Run `script` (`./init`, or `./<delivery>/init`) from `root`; whether it finished.

    Never raises for a script that could not run or did not finish: whatever called this has already written
    and committed its work, and that is the thing that must not be lost to a step that needs the network.
    """
    command = [f"./{script.as_posix()}", *(["--integration", integration] if integration else [])]
    shown = " ".join(command)
    how = launcher(detect(), install)
    if isinstance(how, str):
        print(f"\nNot running {shown}: {how}")
        return False
    # Flushed, because the script writes straight to the same stream: buffered, everything printed so far
    # would land after its output wherever stdout is a pipe.
    print(f"\nRunning {shown} — it installs Spec Kit, which needs the network.", flush=True)
    # Installing is decided once, here; `./init` and the extensions it runs honour it through the environment.
    environment = {**os.environ, **({} if install else {"SLIPWAI_NO_INSTALL": "1"})}
    finished = subprocess.run([*how, *command], cwd=root, check=False, env=environment)
    if finished.returncode != 0:
        print(f"`{shown}` exited {finished.returncode}.")
    return finished.returncode == 0


def run_init(root: Path, delivery: str, agent: Agent, install: bool = False) -> None:
    """`./<delivery>/init`, run once the adoption is committed.

    Last, and never inside the commit: it is the one step that reaches the network, so a source that is
    unreachable costs the adoption nothing — the commit is already made — and what it writes is left in the
    tree for the person to read and commit, exactly as it is in a project the factory generated.
    """
    script = Path(delivery) / "init" if delivery != "." else Path("init")
    shown = f"./{script.as_posix()}"
    if bootstrap(root, script, agent.harness, install):
        # Where `adopt` could not tell which harness this was for, it handed the question to `./init` — and
        # `./init` has now asked it. The record catches up rather than staying behind the truth, which is the
        # difference between a fact nobody has established and one nobody has written down.
        print(record_agent(root, agent))
        print(
            f"`{shown}` is done; what it wrote is uncommitted, and yours to read and commit. "
            "`slipwai adopt --next` says what is left."
        )
        return
    print(
        f"The adoption is committed and unaffected: `{shown}` is a step of its own, which is why it runs "
        f"after. Run it again when whatever stopped it is fixed — `slipwai adopt --next` will keep saying that "
        f"it is the step you are on."
    )


def run_generated_init(destination: Path, integration: str | None, install: bool = False) -> None:
    """`./init` in a project `generate` has just written and committed, from the directory it lives in."""
    if bootstrap(destination, Path("init"), integration, install):
        # The agent only finds the project's commands when it starts in the project's root, so say where that is.
        where = "here" if destination == Path.cwd() else f"in {destination} (`cd {destination}`)"
        print(
            "./init is done; what it wrote is uncommitted: read it, and "
            "`git add -A && git commit -m \"Install Spec Kit\"`.\n"
            f"Start your coding agent {where}: it finds the project's commands only from the project's root."
        )
        return
    print(
        f"The project is written and committed, and unaffected. When whatever stopped it is fixed: "
        f"`cd {destination} && ./init`."
    )


# The project's own projectors, named rather than reached through `make`, so this cannot pick up an
# unrelated target a project has since defined. `.specify/integration.json` is what `./init` writes once a
# harness is installed: absent, nothing has been projected and there is nothing that could be out of step.
PROJECTORS = ("scripts/extensions/project.py", "scripts/agents/project.py")
PROJECTED = ".specify/integration.json"


def reproject(root: Path, delivery: str) -> str | None:
    """Re-derive the harness projections after the files they copy have been rewritten.

    Confirming a candidate changes which languages the record names, which changes the skills' prose, which
    makes every copy under `.claude/skills/` differ from its canonical source — and `check-agents` fails, so
    `make verify` is red the moment `/ground` finishes. Both real adoptions hit it and fixed it by hand. The
    factory writes the canonical files, so the factory re-derives what copies them, exactly as `migrate`
    does after a merge.

    A projector that cannot run is returned, not raised: the record is written and good either way, and
    losing it to a failure in a follow-up step would be much the worse outcome. Returns None when it ran, or
    when there was nothing to run.
    """
    if not (root / PROJECTED).is_file():
        return None
    for relative in PROJECTORS:
        script = f"{delivery}/{relative}" if delivery != "." else relative
        if not (root / script).is_file():
            continue
        done = subprocess.run(["python3", script], cwd=root, text=True, capture_output=True, check=False)
        if done.returncode != 0:
            return done.stderr.strip() or done.stdout.strip() or "no reason given"
    return None


def projection_line(failure: str | None, delivery: str) -> str:
    """What the report says about the projections, which is nothing where there was nothing to project."""
    make = "make" if delivery == "." else f"make -f {delivery}/Makefile"
    if failure is None:
        return ""
    return (
        f"  The harness projections could not be re-derived, so `{make} check-agents` will fail until they "
        f"are: {failure}. `{make} agents` re-runs it."
    )
