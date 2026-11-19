#!/usr/bin/env python3
"""Rule copies: every place that restates a rule of the method, held to the sentence that owns the rule.

A rule of the method has one owner — a rung of the ladder, a constant, one passage of a page — and is
restated wherever a session might arrive without having read the owner: the `AGENTS.md` template, other
passages of `/sail`, the tasks template, a hook's prompt, an agent's brief, the guides. Nothing tied those
copies to the owner. On 2026-11-18 the rule for when a slice is converged, walked and attacked was changed
in the rung that owns it; thirteen sentences elsewhere went on stating the old one in other words, and
lean-coffee-club's sessions followed them. An audit the next day found six more rules in the same state.

So each rule here names its owner — a file and the first and last words of the passage — and a pattern that
recognises a mention of it. `tests/fixtures/rule-copies.txt` records, for every file that mentions the
rule, how many times, beside a digest of the owner's passage. `--check` fails where:

- the owner's passage changed: every file that restates the rule is listed, to be read again;
- a file mentions the rule more or fewer times than recorded: a copy was added or removed;
- the owner's passage can no longer be found: it moved, and the rule here has to follow it.

None of that is a judgement on what a copy says. It makes changing a rule list its copies, which is what
did not happen. Record the reading with `--reread`, which rewrites that rule's rows and appends the reason.

    python3 scripts/rule-copies.py --check
    python3 scripts/rule-copies.py --list push-when
    python3 scripts/rule-copies.py --reread push-when --why "the push now waits for the review too; all read"

A copy that can be replaced by a pointer to the owner, or rendered from it, should be: a row that goes is a
copy nobody has to read again.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "tests/fixtures/rule-copies.txt"
#: Where a session, or a person setting one up, reads the method.
SCANNED = ("assets", "docs/guide", "src/slipwai/project")
SUFFIXES = (".md", ".yml", ".yaml", ".py", ".txt")
REREAD = "# reread: "


@dataclass(frozen=True)
class Rule:
    """One rule: its name, the passage that owns it, and what a mention of it looks like."""

    key: str
    owner: str
    begins: str
    ends: str
    mention: str


RULES = (
    Rule("readings", "src/slipwai/project/capability_gates.py",
         "**Nothing is read per slice unless the project asks for it.**", "absent, it is `capability`.",
         r'"readings"|reads each slice|read per slice|per slice as well|release mode is `open`'),
    Rule("gates-when", "src/slipwai/project/capability_gates.py",
         "The gates run **once per", "lights the entry point.",
         r"last slice has merged|last slice merges|that slice merges|capability is whole|"
         r"last slice's branch|every slice under it"),
    Rule("push-when", "src/slipwai/project/ladder.py",
         "That record is what lets the", "the hand's verdict stood.",
         r"demo acceptance|accepted the demo|after acceptance|first implementation push|"
         r"[Pp]ush once its examples|examples are proven"),
    Rule("release-modes", "src/slipwai/project/flags.py",
         "- **open** (pre-launch:", "only what passes the promotion gate.",
         r"release mode|\*\*(?:open|keystone|flagged)\*\*|[Uu]nder `(?:open|keystone|flagged)`|"
         r"no flag, or a flag"),
    Rule("slice-hardening", "src/slipwai/project/ladder.py",
         "**Nothing is\n   attacked here**", "and spawns nothing.",
         r"attack(?:s|ed|ing)? nothing|[Nn]othing is attacked|trigger record|adversarial pass|"
         r"[Mm]utation (?:testing|pass|analysis|evidence) "),
    Rule("walk-bound", "assets/toolkit/commands/sail.md",
         "**A capability — and a slice,", "opens a walk past the bound.",
         r'walked twice|"walks"|`walks`|walk \d of'),
)


def flat(text: str) -> str:
    """Text with its line breaks and indentation folded, so a phrase is found wherever it wraps."""
    return " ".join(text.split())


def passage(rule: Rule) -> str:
    """The owner's passage, folded, or `""` where it is not where the rule says."""
    path = ROOT / rule.owner
    if not path.is_file():
        return ""
    text = flat(path.read_text(encoding="utf-8"))
    start = text.find(flat(rule.begins))
    end = text.find(flat(rule.ends), start) if start >= 0 else -1
    return text[start:end + len(flat(rule.ends))] if end >= 0 else ""


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def files() -> list[Path]:
    found: list[Path] = []
    for top in SCANNED:
        found += [path for path in (ROOT / top).rglob("*")
                  if path.is_file() and path.suffix in SUFFIXES and "node_modules" not in path.parts]
    return sorted(found)


def counts(rule: Rule, among: list[Path]) -> dict[str, int]:
    """How many times each file mentions the rule, for the files that do."""
    pattern = re.compile(rule.mention)
    found = {}
    for path in among:
        try:
            said = len(pattern.findall(flat(path.read_text(encoding="utf-8"))))
        except UnicodeDecodeError:
            continue
        if said:
            found[path.relative_to(ROOT).as_posix()] = said
    return found


def lines_of(rule: Rule, where: str) -> list[str]:
    """Each line of a file that mentions the rule, as `path:line: text`, for whoever reads them again."""
    pattern = re.compile(rule.mention)
    text = (ROOT / where).read_text(encoding="utf-8").splitlines()
    found = [f"  {where}:{number}: {line.strip()[:150]}" for number, line in enumerate(text, 1)
             if pattern.search(line)]
    return found or [f"  {where}: (the mention wraps across lines)"]


def rows() -> list[str]:
    """The record's rows as the tree stands: `rule  owner digest  count  path`."""
    among = files()
    found = []
    for rule in RULES:
        owner = digest(passage(rule))
        found += [f"{rule.key}  {owner}  {said}  {path}" for path, said in sorted(counts(rule, among).items())]
    return found


def recorded() -> list[str]:
    if not RECORD.is_file():
        return []
    return [line for line in RECORD.read_text(encoding="utf-8").splitlines() if line and not line.startswith("#")]


def problems() -> list[str]:
    """What differs between the tree and the record, said so that the next step is plain. `[]` is agreement."""
    was: dict[str, dict[str, tuple[str, int]]] = {}
    for line in recorded():
        key, owner, said, path = line.split("  ")
        was.setdefault(key, {})[path] = (owner, int(said))
    among = files()
    found: list[str] = []
    for rule in RULES:
        text = passage(rule)
        if not text:
            found.append(f"{rule.key}: its owning passage is no longer in {rule.owner} between "
                         f"{rule.begins!r} and {rule.ends!r}. Point the rule in scripts/rule-copies.py at "
                         f"where it is now")
            continue
        now, held = counts(rule, among), was.get(rule.key, {})
        owners = {owner for owner, _ in held.values()}
        if held and owners != {digest(text)}:
            found.append(f"{rule.key}: the passage that owns this rule changed ({rule.owner}). "
                         f"{len(now)} file(s) restate it; read each of these against the new passage:")
            for path in sorted(now):
                found += lines_of(rule, path)
            found.append(f"  then: python3 scripts/rule-copies.py --reread {rule.key} --why '<what changed>'")
            continue
        for path in sorted(set(now) | set(held)):
            before, after = held.get(path, ("", 0))[1], now.get(path, 0)
            if before == after:
                continue
            found.append(f"{rule.key}: {path} mentions this rule {after} time(s), and {before} are recorded. "
                         f"A copy was added or removed; the owner is {rule.owner}:")
            found += lines_of(rule, path) if after else []
            found.append(f"  then: python3 scripts/rule-copies.py --reread {rule.key} --why '<what you checked>'")
    known = {rule.key for rule in RULES}
    found += [f"{key}: the record has rows for a rule scripts/rule-copies.py no longer names"
              for key in sorted(set(was) - known)]
    return found


def reread(keys: list[str], why: str) -> None:
    """Rewrite the rows of the rules named, keep every other row, and append the reason."""
    kept = [line for line in recorded() if line.split("  ")[0] not in keys]
    fresh = [line for line in rows() if line.split("  ")[0] in keys]
    order = {rule.key: place for place, rule in enumerate(RULES)}
    body = sorted(kept + fresh, key=lambda line: (order.get(line.split("  ")[0], len(order)), line.split("  ")[3]))
    reasons = ([line for line in RECORD.read_text(encoding="utf-8").splitlines() if line.startswith(REREAD)]
               if RECORD.is_file() else [])
    today = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d")
    reasons.append(f"{REREAD}{today} {', '.join(keys)}: {' '.join(why.split())}")
    head = ("# Every file that restates a rule of the method: rule, digest of the passage that owns it, how\n"
            "# many times the file mentions it, the file. Written by scripts/rule-copies.py, never by hand.\n")
    RECORD.write_text(head + "\n".join(body) + "\n" + "\n".join(reasons) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    doing = parser.add_mutually_exclusive_group(required=True)
    doing.add_argument("--check", action="store_true", help="fail where the tree and the record differ")
    doing.add_argument("--list", metavar="RULE", help="every line that mentions this rule")
    doing.add_argument("--reread", metavar="RULE", help="record that this rule's copies were read (or `all`)")
    parser.add_argument("--why", help="with --reread: what changed, or what was checked")
    args = parser.parse_args(argv)
    named = {rule.key: rule for rule in RULES}
    if args.check:
        found = problems()
        print("\n".join(found) if found else f"rule-copies: {len(recorded())} copies of {len(RULES)} rules "
                                             f"are as recorded")
        return 1 if found else 0
    wanted = args.list or args.reread
    if wanted != "all" and wanted not in named:
        parser.error(f"no rule {wanted!r}; there are {', '.join(named)}")
    keys = list(named) if wanted == "all" else [wanted]
    if args.list:
        for key in keys:
            rule = named[key]
            print(f"{key}: owned by {rule.owner}")
            for path in sorted(counts(rule, files())):
                print("\n".join(lines_of(rule, path)))
        return 0
    if not args.why:
        parser.error("--reread needs --why: what changed, or what you checked")
    reread(keys, args.why)
    print(f"rule-copies: {', '.join(keys)} recorded as read, with the reason")
    return 0


if __name__ == "__main__":
    sys.exit(main())
