#!/usr/bin/env python3
"""Copy the modules both runtimes need from the keel into the toolkit, and refuse a copy that has drifted.

Two things read the logs and the berth allocation. The **keel** does — `slipwai fleet` folds what the logs
hold, `slipwai berth` writes the records — and so does the **toolkit**, inside a generated project, where
the harbourmaster and the captain write every line there is.

A generated project has no slipwai to import. That rule has been learned twice here, and the usual answer is
to move the module to where it runs — which is what slice 5.5b did with `clearance.py`. It does not work for
these two: both runtimes genuinely need them, and a module that lived in only one of them would leave the
other hand-rolling the format, which is how a log reader and a log writer stop agreeing about what a line is.

So there is one source and a generated copy, which is `scripts/glossary.py`'s pattern and
`render-fairways.py`'s: the keel's module is the source, the toolkit's is written from it, and `--check`
refuses one that differs. The copies are byte-identical, so the gate is an equality and there is no template
to get wrong. Both modules import nothing but the standard library, which is what makes that possible and is
the one thing to preserve when either changes — a keel import in one of them breaks the project's copy at the
import line, in a process that has no way to say why.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
#: Keel module → where the toolkit carries it. Both run in a generated project and in this one.
SHARED = {
    "src/slipwai/logs.py": "assets/toolkit/scripts/agents/logs.py",
    "src/slipwai/berths.py": "assets/toolkit/scripts/agents/berths.py",
    "src/slipwai/telegraph.py": "assets/toolkit/scripts/agents/telegraph.py",
    # The Agent Client Protocol's client half: the board's sessions in the keel, the captain's drives in the toolkit.
    "src/slipwai/acp.py": "assets/toolkit/scripts/agents/acp.py",
}
BANNER = """# Written by scripts/shared-modules.py from {source}. Do not edit: edit the keel's module,
# run `make shared`, and commit both. A generated project has no slipwai to import, and both runtimes need
# this one — so there is one source and this copy, and `make check-shared` refuses a copy that has drifted.
"""


def rendered(source: Path, origin: str) -> str:
    """The toolkit's copy: the keel's module with one banner above it saying where it came from."""
    return BANNER.format(source=origin) + source.read_text(encoding="utf-8")


def imports_only_the_standard_library(text: str, origin: str) -> list[str]:
    """Why this module cannot be carried into a project, or nothing.

    A relative import is the fault that matters: it works in the keel and fails at the import line in a
    project, in a process whose whole job is to be the thing that can say what happened.
    """
    found = [line.strip() for line in text.splitlines()
             if line.startswith("from .") or line.startswith("import .")]
    return [f"{origin} has {line!r}, and a project has no slipwai to import it from" for line in found]


def main(argv: list[str]) -> int:
    checking = "--check" in argv
    findings: list[str] = []
    for origin, destination in SHARED.items():
        source, target = ROOT / origin, ROOT / destination
        if not source.is_file():
            findings.append(f"{origin} is not in this repository, and {destination} is written from it")
            continue
        text = source.read_text(encoding="utf-8")
        findings += imports_only_the_standard_library(text, origin)
        whole = rendered(source, origin)
        if not checking:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(whole, encoding="utf-8")
            print(f"shared-modules: {destination} from {origin}")
        elif not target.is_file():
            findings.append(f"{destination} is not there; `make shared` writes it from {origin}")
        elif target.read_text(encoding="utf-8") != whole:
            findings.append(f"{destination} is not what {origin} renders to; `make shared` rewrites it")
    if findings:
        print("check-shared: a module both runtimes need is not carried correctly", file=sys.stderr)
        for finding in findings:
            print(f"  {finding}", file=sys.stderr)
        return 1
    if checking:
        print(f"check-shared: {len(SHARED)} module(s) carried into the toolkit, each what its source renders to")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
