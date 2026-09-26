"""What `adopt` says about the coding agent, and the `./init` run it can end with.

Brownfield adoption (#74; experimental as `AGENTS.md` defines the word). `harness.py` establishes which
harness the material is for and `init_script.py` generates the script; this is the edge between them — the
report's line about what was established and how, running the script once the adoption is committed, and
bringing the record up to what `./init` settled where `adopt` itself could not tell.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .harness import Agent, from_spec_kit, name_of


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
    document = json.loads(manifest.read_text())
    document["agent"] = settled.record()
    manifest.write_text(json.dumps(document, indent=2) + "\n")
    return (
        f"Agent: {name_of(settled.harness)} — `./init` asked, and project.json now records the answer "
        "(`confirmed`). That is one more uncommitted change for you to read."
    )


def run_init(root: Path, delivery: str, agent: Agent) -> None:
    """`./<delivery>/init`, run once the adoption is committed.

    Last, and never inside the commit: it is the one step that reaches the network, so a source that is
    unreachable costs the adoption nothing — the commit is already made — and what it writes is left in the
    tree for the person to read and commit, exactly as it is in a project the factory generated.
    """
    script = Path(delivery) / "init" if delivery != "." else Path("init")
    command = [f"./{script.as_posix()}", *(["--integration", agent.harness] if agent.harness else [])]
    print(f"\nRunning {' '.join(command)} — it installs Spec Kit, which needs the network.")
    finished = subprocess.run(command, cwd=root, check=False)
    if finished.returncode == 0:
        # Where `adopt` could not tell which harness this was for, it handed the question to `./init` — and
        # `./init` has now asked it. The record catches up rather than staying behind the truth, which is the
        # difference between a fact nobody has established and one nobody has written down.
        print(record_agent(root, agent))
        print(
            f"`{' '.join(command)}` is done; what it wrote is uncommitted, and yours to read and commit. "
            "`slipwai adopt --next` says what is left."
        )
        return
    print(
        f"`{' '.join(command)}` exited {finished.returncode}, and the adoption is committed and unaffected: it is "
        f"a step of its own, which is why it runs after. Run it again when whatever stopped it is fixed — "
        f"`slipwai adopt --next` will keep saying that it is the step you are on."
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
