"""The decision log: every decision this project took, readable, each with its own read receipt.

The board's only view of decisions was *N decision(s) nobody has read yet* under *Waiting on you*, opening
on the deck log's lines — `D95 (a): the source alone settles the item; no answer stored or parsed (as D68)`
— with a Mark read beside each. The line is the decision's id and its answer letter. The question, the
options, why, and what would reverse it are in `specs/<feature>/decisions.md`, which the board never showed,
and a person asked to say they had read a decision was shown the one form of it nobody can read.

**One entry per decision, from three places.** A deck `decision` line is what a read receipt names. The
`decisions.md` entry its `D<n>` names is what a person reads — taken from every checkout of the project,
because a slice in flight has written its decisions into its own branch's copy and trunk's is behind until
it merges. And the deck's `question` line with the same `id` is the question a person's own answer —
`decide for me` — was an answer to, which on its own reads as nothing at all.

**The receipt is the one the ceiling counts.** Mark read writes the deck `read` line, as before, so reading
here is what lets a stream parked at its decision ceiling go on. A decision taken before the fleet existed —
in clarify, in the chart — has no deck line and holds nothing up; its receipt is kept beside the logs in
`decisions-read.json`, so the log can still say which of those a person has read.
"""
from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .deck import entries, mark_read, streams
from .page_shell import esc

#: Where a decision with no deck line is marked read: beside the logs, which Git already ignores.
UPSTREAM_READ = ".slipwai/logs/decisions-read.json"
_HEAD = re.compile(r"^## (D\d+)\s*[—-]\s*(.*)$", re.MULTILINE)
_FIELD = re.compile(r"\*\*([^*:]+):\*\*\s*(.*?)(?=\s+·\s+\*\*[^*:]+:\*\*|$)")
_NUMBER = re.compile(r"^\s*(D\d+)\b")
#: The parts of an entry shown under its decision, in this order.
SHOWN = ("Question", "Options", "Why", "Read against", "Confidence", "Would reverse if", "Written to", "Status")


@dataclass
class Decision:
    """One decision as a person reads it, and how its read receipt is written."""

    key: str
    number: str
    title: str
    decision: str
    when: str
    slice: str = ""
    stream: str = ""
    decided_by: str = ""
    parts: dict[str, str] = field(default_factory=dict)
    read: bool = False
    yours: bool = False


def parse(text: str) -> dict[str, dict[str, str]]:
    """`decisions.md` as `D<n>` → its heading and each `**Label:** value`, several to a line where `·` joins them."""
    found: dict[str, dict[str, str]] = {}
    heads = list(_HEAD.finditer(text))
    for index, head in enumerate(heads):
        body = text[head.end():heads[index + 1].start() if index + 1 < len(heads) else len(text)]
        parts = {"title": head.group(2).strip()}
        for line in body.splitlines():
            if line.lstrip().startswith("- "):
                parts.update({label.strip(): value.strip() for label, value in _FIELD.findall(line)})
        found[head.group(1)] = parts
    return found


def checkouts(root: Path) -> list[Path]:
    """This checkout first, then every other worktree of the same repository: the berths."""
    done = subprocess.run(["git", "-C", str(root), "worktree", "list", "--porcelain"], capture_output=True,
                          text=True, check=False)
    others = [Path(line[9:]) for line in done.stdout.splitlines() if line.startswith("worktree ")]
    return [root, *(one for one in others if one.resolve() != root.resolve())]


def written(root: Path) -> dict[str, dict[str, str]]:
    """Every `decisions.md` entry in any checkout. Trunk's copy wins where both have one; a berth adds the ones
    its slice has taken since it branched."""
    found: dict[str, dict[str, str]] = {}
    for place in checkouts(root):
        for path in sorted(place.glob("specs/*/decisions.md")):
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for number, parts in parse(text).items():
                found.setdefault(number, parts)
    return found


def upstream_read(root: Path) -> set[str]:
    try:
        held = json.loads((root / UPSTREAM_READ).read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return set()
    return {str(one) for one in held} if isinstance(held, list) else set()


def decisions(root: Path) -> list[Decision]:
    """Every decision, newest first."""
    book = written(root)
    used: set[str] = set()
    found: list[Decision] = []
    for feature, fairway in streams(root):
        lines, _ = entries(root, fairway, feature)
        asked = {str(e.fields.get("id")): str(e.fields.get("what", "")) for e in lines if e.kind == "question"}
        receipts = {str(e.fields.get("told")) for e in lines if e.kind == "read"}
        for line in (e for e in lines if e.kind == "decision"):
            what, ident = str(line.fields.get("what", "")), str(line.fields.get("id", ""))
            named = _NUMBER.match(what)
            number = named.group(1) if named else ""
            entry = book.get(number, {})
            used.add(number)
            by = str(line.fields.get("decided_by", ""))
            yours = by == "human"
            parts = {key: entry[key] for key in SHOWN if entry.get(key)}
            if ident in asked and "Question" not in parts:
                parts["Question"] = asked[ident]
            title = entry.get("title") or asked.get(ident) or (f"{ident} (not in decisions.md)" if ident else what)
            found.append(Decision(f"deck:{fairway}:{line.t}", number or ident, title,
                                  entry.get("Decision") or what, line.t, str(line.fields.get("slice", "")), fairway,
                                  "you" if yours else by or entry.get("Decided by", ""), parts,
                                  yours or line.t in receipts, yours))
    marked = upstream_read(root)
    for number, entry in book.items():
        if number in used:
            continue
        parts = {key: entry[key] for key in SHOWN if entry.get(key)}
        found.append(Decision(f"md:{number}", number, entry.get("title", ""), entry.get("Decision", ""),
                              entry.get("When", ""), entry.get("Slice", "").strip("— ").strip(),
                              entry.get("Stream", ""), entry.get("Decided by", ""), parts, number in marked))
    return sorted(found, key=lambda one: (one.when, one.number), reverse=True)


def mark(root: Path, keys: list[str]) -> str:
    """Write the read receipt for each decision named: the deck `read` line, or the upstream file."""
    by_stream: dict[str, list[str]] = {}
    upstream: list[str] = []
    for key in keys:
        kind, _, rest = key.partition(":")
        if kind == "deck" and ":" in rest:
            fairway, _, stamp = rest.partition(":")
            by_stream.setdefault(fairway, []).append(stamp)
        elif kind == "md" and re.fullmatch(r"D\d+", rest):
            upstream.append(rest)
        else:
            raise ValueError(f"{key!r} names no decision")
    said = [mark_read(root, fairway, stamps) for fairway, stamps in by_stream.items()]
    if upstream:
        known = {one.number for one in decisions(root) if one.key.startswith("md:")}
        wanted = sorted(upstream_read(root) | (set(upstream) & known))
        path = root / UPSTREAM_READ
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(wanted, indent=0) + "\n", encoding="utf-8")
        said.append(f"marked {len(set(upstream) & known)} earlier decision(s) read")
    return "; ".join(said) or "nothing to mark"


STYLE = """
#decisions .bar{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;margin:0 0 10px}
#decisions .bar label{font-size:.86rem;color:var(--ink-2)}
#decisions article{border:1px solid var(--rule);border-left:3px solid var(--brass);border-radius:8px;
  padding:10px 14px;margin:10px 0;display:grid;gap:6px}
#decisions article.read{border-left-color:var(--rule);opacity:.82}
#decisions article.yours{border-left-color:var(--teal)}
#decisions article[hidden]{display:none}
#decisions .top{display:flex;flex-wrap:wrap;gap:6px 10px;align-items:baseline;justify-content:space-between}
#decisions .top h3{margin:0;font-size:.98rem;text-transform:none;letter-spacing:0;color:var(--ink)}
#decisions .num{font-family:var(--mono);font-size:.78rem;color:var(--ink-3);margin-right:6px}
#decisions .meta{display:flex;flex-wrap:wrap;gap:6px;font-size:.76rem;color:var(--ink-3)}
#decisions .meta span{border:1px solid var(--rule);border-radius:999px;padding:1px 8px}
#decisions .answer{font-size:.92rem}
#decisions dl{display:grid;grid-template-columns:max-content 1fr;gap:4px 12px;margin:0;font-size:.86rem}
#decisions dt{color:var(--ink-3)}
#decisions dd{margin:0;color:var(--ink-2)}
@media (max-width:620px){#decisions dl{grid-template-columns:1fr}#decisions dt{margin-top:4px}}
"""

SCRIPT = """
// The decision log: filtered in place, and Mark read writes the receipt and greys the entry without a reload.
(function(){
  const log = document.getElementById('decisions');
  if (!log) return;
  const all = () => [...log.querySelectorAll('article')];
  const filter = () => {
    const unread = log.querySelector('[name=decisions-show]:checked').value === 'unread';
    const slice = log.querySelector('select[name=decisions-slice]').value;
    let shown = 0;
    all().forEach(one => {
      one.hidden = (unread && one.classList.contains('read')) || (slice && one.dataset.slice !== slice);
      if (!one.hidden) shown += 1;
    });
    log.querySelector('.shown').textContent = shown ? ''
      : 'Nothing here: every decision this filter shows has been read.';
  };
  const count = () => {
    const left = all().filter(one => !one.classList.contains('read')).length;
    document.querySelectorAll('[data-decisions-unread]').forEach(one => {
      one.textContent = left ? left + ' unread' : ''; one.hidden = !left;
    });
  };
  const read = async keys => {
    const answer = await fetch('/decisions/read', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({keys})});
    if (!answer.ok) { alert(await answer.text()); return; }
    // A deck receipt is per instant, so every decision written in that second shares the key and is read with it.
    const stamps = new Set(keys);
    all().forEach(one => { if (stamps.has(one.dataset.key)) {
      one.classList.add('read'); const b = one.querySelector('[data-decision-read]'); if (b) b.remove(); } });
    count(); filter();
  };
  log.addEventListener('change', filter);
  log.addEventListener('click', event => {
    const one = event.target.closest('[data-decision-read]');
    if (one) { one.disabled = true; read([one.dataset.decisionRead]); }
    if (event.target.closest('[data-decisions-all]')) {
      read(all().filter(a => !a.hidden && !a.classList.contains('read')).map(a => a.dataset.key));
    }
  });
  filter(); count();
})();
"""


def entry_html(one: Decision) -> str:
    kind = "yours" if one.yours else "read" if one.read else "unread"
    meta = [one.slice and f"Slice {one.slice}", one.parts.get("Stage") or "", one.when[:16].replace("T", " "),
            f"Decided by {one.decided_by}" if one.decided_by else ""]
    chips = "".join(f"<span>{esc(word)}</span>" for word in meta if word)
    rows = "".join(f"<dt>{esc(label)}</dt><dd>{esc(one.parts[label])}</dd>" for label in SHOWN
                   if one.parts.get(label) and not (label == "Question" and one.parts[label] == one.title))
    button = ("" if one.read else f'<button type="button" class="go" data-decision-read="{esc(one.key)}">'
              "Mark read</button>")
    said = "Your answer" if one.yours else "Decision"
    return (f'<article class="{kind}" data-key="{esc(one.key)}" data-slice="{esc(one.slice)}">'
            f'<div class="top"><h3><span class="num">{esc(one.number)}</span>{esc(one.title)}</h3>{button}</div>'
            f'<div class="meta">{chips}</div><div class="answer"><b>{said}:</b> {esc(one.decision)}</div>'
            + (f"<details><summary>Question, options and why</summary><dl>{rows}</dl></details>" if rows else "")
            + "</article>")


def card(root: Path) -> tuple[str, int]:
    """The log as a card, and how many decisions in it nobody has read."""
    found = decisions(root)
    if not found:
        return "", 0
    unread = sum(1 for one in found if not one.read)
    slices = sorted({one.slice for one in found if one.slice})
    options = "".join(f'<option value="{esc(one)}">{esc(one)}</option>' for one in slices)
    bar = ('<div class="bar"><label><input type="radio" name="decisions-show" value="unread" checked> Unread</label>'
           '<label><input type="radio" name="decisions-show" value="all"> All</label>'
           f'<label>Slice <select name="decisions-slice"><option value="">every slice</option>{options}</select>'
           '</label><button type="button" class="install" data-decisions-all>Mark every one shown as read</button>'
           "</div>")
    return (f'<div class="card" id="decisions"><h2>Decisions · {len(found)}</h2>'
            '<p class="empty">Every decision taken with nobody at the wheel, newest first. Reading one here is the '
            "receipt the decision ceiling counts.</p>"
            f'{bar}<p class="empty shown"></p>{"".join(entry_html(one) for one in found)}</div>', unread)
