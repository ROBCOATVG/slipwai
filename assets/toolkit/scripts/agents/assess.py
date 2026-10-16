#!/usr/bin/env python3
"""`/assess`: one idea handed to `/sail`, decided by Spec Kit and specified only on a go.

The session does the writing. This starts it, and refuses to start when the idea has not been captured or
nobody has agreed it is a new feature — the two facts that have to be on disk before assessment runs.
"""
from __future__ import annotations

import hashlib
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import harness  # noqa: E402

ROOT = harness.ROOT
COMMAND = ROOT / "commands/assess.md"
VERDICT = re.compile(r"(?im)^[\s*]*verdict[\s*:]*\s*(go|needs-clarification|kill)\b")


def digest_of(folder: Path) -> str:
    """The same bytes `slipwai.project.intake.digest_of` hashes, so a receipt written here still matches."""
    hasher = hashlib.sha256()
    files = sorted(
        path for path in folder.rglob("*")
        if path.is_file() and path.name not in ("specified.json", "confirmed")
        and not any(part.startswith(".") for part in path.relative_to(folder).parts)
    )
    for path in files:
        hasher.update(path.relative_to(folder).as_posix().encode())
        hasher.update(b"\0")
        hasher.update(path.read_bytes())
        hasher.update(b"\0")
    return hasher.hexdigest()


def main(argv: list[str]) -> int:
    if not argv or not argv[0].strip():
        print("assess: name the idea, as `make assess SLUG=<slug>`", file=sys.stderr)
        return 2
    slug = argv[0].strip()
    folder = ROOT / "docs/intake" / slug
    if not (folder / "brief.md").is_file():
        print(f"assess: docs/intake/{slug}/brief.md is not there; hand the feature to /sail first",
              file=sys.stderr)
        return 2
    if not (folder / "confirmed").is_file():
        print(f"assess: docs/intake/{slug}/confirmed is not there; a person, or the skipper under /cruise, "
              f"agrees it is a new feature before this runs. Write that file as `yes` and who answered, "
              f"then `make assess SLUG={slug}`", file=sys.stderr)
        return 2
    try:
        chosen, said = harness.choose()
    except harness.NoHarness as refusal:
        print(f"assess: {refusal}", file=sys.stderr)
        return 2
    template, why = harness.template(chosen)
    prompt = harness.prompt_for(chosen, "assess", COMMAND, slug)
    line = template.replace("{prompt}", shlex.quote(prompt))
    print(f"{said}; {why}", flush=True)
    print(f"+ {line}", flush=True)
    environment = {**harness.child_environment(chosen), "SLIPWAI_STAGE": "assess"}
    done = subprocess.run(shlex.split(line), cwd=ROOT, env=environment, check=False)
    if done.returncode:
        print(f"assess: the session exited {done.returncode}; whatever it wrote is on the current branch",
              file=sys.stderr)
        return done.returncode
    decision = ROOT / ".specify/assessments" / slug / "decision.md"
    if not decision.is_file():
        print(f"assess: the session ended without .specify/assessments/{slug}/decision.md; read its last "
              f"lines and run `make assess SLUG={slug}` again", file=sys.stderr)
        return 1
    found = VERDICT.search(decision.read_text(encoding="utf-8", errors="replace"))
    verdict = found.group(1).lower() if found else ""
    if verdict != "go":
        print(f"assessed: {slug} — {verdict or 'no verdict'}; specification was not written")
        return 0
    receipt = folder / "specified.json"
    if not receipt.is_file():
        print(f"assess: the verdict is go and docs/intake/{slug}/specified.json was not written; write it "
              f"as the feature directory and the digest, then `make assess SLUG={slug}` is done",
              file=sys.stderr)
        return 1
    try:
        held = json.loads(receipt.read_text(encoding="utf-8"))
    except ValueError:
        held = {}
    if not isinstance(held, dict) or held.get("digest") != digest_of(folder):
        print(f"assess: docs/intake/{slug}/specified.json does not match the sources; rewrite the digest "
              f"and run `make assess SLUG={slug}` only if the specification still needs writing",
              file=sys.stderr)
        return 1
    print(f"assessed: {slug} — {held.get('feature', 'specified')}; read it, then Continue the build")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
