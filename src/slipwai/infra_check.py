"""Whether the stacks under `infra/` still parse, asked once, after a crossing has written its merge.

A generated project's own gate deliberately cannot do this. `make verify` runs with no cloud credential and
no provider plugins, by design — the gate a person runs twenty times a day may not reach a network — so the
first thing that ever reads these files for real is the deploy, on a runner, after a merge to trunk. That is
a long way to carry a syntax error.

A crossing is the one moment that is neither: a person is at the machine, it has just rewritten a tree, and
whatever is wrong is one command old. So it looks, with whatever is installed, and *says* — it never
refuses. The merge is already committed by the time this runs; a crossing that failed over a stack it was
not allowed to touch would be a worse answer than the one it is reporting.

**Two readings, and the cheap one is the one that always runs.** `tofu validate` is the real answer and it
needs the providers initialised, which needs a network and a `tofu init` this must not run on somebody's
behalf. The structural reading needs nothing: duplicate `locals`, `variable`, `output` and resource
addresses across the files of one stack directory, which is exactly the class of fault a factory that wrote
into somebody's infrastructure produces — one block implemented twice, under two names.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

#: Where a stack is: a directory of `.tf` files is one module, and names must be unique within a module.
SUFFIX = "*.tf"
#: `locals { a = 1 }` — every assignment at the top level of a locals block. Blocks are not nested in
#: practice and a value's own `{` is on the same line as its `=`, so one level of depth is enough to find
#: the names: a line that assigns at depth one inside `locals` declares a local.
LOCALS = re.compile(r"^\s*locals\s*\{", re.MULTILINE)
ASSIGNED = re.compile(r"^\s{1,4}([A-Za-z_][A-Za-z0-9_-]*)\s*=")
#: `resource "aws_x" "y"`, `variable "z"`, `output "w"` — the other three kinds of name a module may not
#: repeat. The quoted words are the address, whatever product they name: this reads them and knows none.
DECLARED = re.compile(r'^\s*(resource|data|variable|output|module)\s+((?:"[^"]+"\s*)+)\{', re.MULTILINE)


def locals_of(text: str) -> list[str]:
    """Every local this file declares, in order."""
    found = []
    for block in LOCALS.finditer(text):
        depth = 0
        for line in text[block.end():].splitlines():
            # The line is read at the depth it *starts* at: `web_environment = {` declares a local and
            # opens an object, and counting its own brace first would hide every local whose value is one.
            named = ASSIGNED.match(line)
            if named and depth == 0:
                found.append(named.group(1))
            depth += line.count("{") - line.count("}")
            if depth < 0:
                break
    return found


def declared_in(text: str) -> list[str]:
    """Every addressable name this file declares: `resource aws_x.y`, `variable z`, and the rest."""
    return [f"{found.group(1)} {' '.join(part.strip() for part in found.group(2).split())}"
            for found in DECLARED.finditer(text)]


def duplicates(stack: Path) -> list[str]:
    """Every name two files of one stack both declare, said with both files.

    One module, one namespace: OpenTofu refuses the whole stack over any of these, which is why a
    duplicate is worth finding before a runner finds it.
    """
    seen: dict[str, str] = {}
    said = []
    for path in sorted(stack.glob(SUFFIX)):
        text = path.read_text(encoding="utf-8", errors="replace")
        for name in [f"local {one}" for one in locals_of(text)] + declared_in(text):
            if name in seen and seen[name] != path.name:
                said.append(f"{stack}: `{name}` is declared in both {seen[name]} and {path.name}")
            seen.setdefault(name, path.name)
    return said


def stacks(root: Path, where: str = "infra") -> list[Path]:
    """Every directory under `infra/` that holds a stack, which is every one that holds a `.tf`."""
    place = root / where
    if not place.is_dir():
        return []
    return sorted({path.parent for path in place.rglob(SUFFIX)})


def validated(stack: Path, run: Callable[..., subprocess.CompletedProcess] = subprocess.run) -> str | None:
    """What `tofu validate` said about this stack, or None where it could not be the one to say.

    Not initialised and not installed are the same answer here — *this did not check* — and neither is a
    finding. Running `init` would reach a network and write provider plugins into somebody's tree, which is
    not a thing a crossing may do on its own.
    """
    tool = shutil.which("tofu") or shutil.which("terraform")
    if tool is None:
        return None
    done = run([tool, "validate", "-no-color"], cwd=stack, capture_output=True, text=True, check=False)
    if done.returncode == 0:
        return None
    said = (done.stderr or done.stdout or "").strip()
    if "init" in said.lower() and "run" in said.lower():
        return None  # it is asking to be initialised, which is not a verdict on the files
    return f"{stack}: `{Path(tool).name} validate` refused it.\n" + "\n".join(
        f"    {line}" for line in said.splitlines()[:12])


def check(root: Path, run: Callable[..., subprocess.CompletedProcess] = subprocess.run) -> list[str]:
    """Everything wrong with this project's stacks that could be read without a network. Nothing refuses."""
    found: list[str] = []
    for stack in stacks(root):
        found.extend(duplicates(stack))
        said = validated(stack, run)
        if said is not None:
            found.append(said)
    return found
