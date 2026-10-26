"""The lines a strategy ADR records beside its `Strategy:` line, and which of them each strategy cannot be acted on
without.

A strategy is three decisions, not one (`docs/strategies/README.md`): how the change happens, where a new home
lives, and the shape the system is heading for. A `Strategy:` line alone said only the first, and every step after
it — the board, the draft, the specification, the gate — then had to guess the other two; a rewrite decided with
nothing else on its ADR had its first feature specified for the old stack. So each strategy names the lines its
playbook needs before anything can follow from it, and an ADR missing one still decides — the decision is the
person's — but is *incomplete*, and says which lines it is missing until somebody writes them.

The playbooks hold more lines than these. Those are guidance a phase reads when it gets there; these are the ones
nothing can start without.
"""
from __future__ import annotations

import datetime
import re

#: What each strategy cannot be acted on without, in the order the board asks for them.
REQUIRED: dict[str, tuple[str, ...]] = {
    "leave-it": ("Variant", "Risk-owner", "Review"),
    "in-place": ("Target",),
    "strangler-fig": ("Freeze", "New home", "End", "Target"),
    "rewrite": ("Freeze", "Home", "Stack", "Why single cut-over", "Cut-over", "Rollback", "Parity", "Checkpoint",
                "Target"),
}
#: A strangler fig that moves everything is an incremental rewrite, and owes what a rewrite owes before it starts.
END_ALL = ("Parity", "Checkpoint")
#: Lines that are not required but that steps after the decision read, spelled as they read them.
READ = ("Why", "New home stack", "Build", "Seam", "Data", "Variant")
#: What a strategy name an older factory wrote meant, in the lines it implies. A modular monolith grew new modules
#: inside the one deployable, which is a strangler fig whose new home is `inside` and whose target is modular.
IMPLIED: dict[str, dict[str, str]] = {
    "modular-monolith": {"New home": "inside", "Target": "modules in one deployable"},
}
# A whole `Name: value` line, however it is emphasised. A value still in angle brackets is the template's, not an
# answer: `Review: <date>` is a line nobody has written.
LINE = re.compile(r"^[\s*_>`-]*([A-Za-z][A-Za-z -]*?)[\s*_`]*:[\s*_`]*(.*?)[\s*_`]*$", re.MULTILINE)
DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")


def lines_of(text: str, spelled: str | None = None) -> dict[str, str]:
    """Every `Name: value` line the ADR answers, by name, the first of each; with what an older strategy name implies
    where the ADR does not say it."""
    found: dict[str, str] = {}
    for match in LINE.finditer(text):
        name, value = match.group(1).strip(), match.group(2).strip()
        if value and not value.startswith("<") and name.lower() not in found:
            found[name.lower()] = value
    for name, value in IMPLIED.get(spelled or "", {}).items():
        found.setdefault(name.lower(), value)
    # Keyed as the strategy asks for them, whatever case the ADR wrote them in.
    spelling = {name.lower(): name for wanted in (*REQUIRED.values(), END_ALL, READ) for name in wanted}
    return {spelling.get(name, name): value for name, value in found.items()}


def required(strategy: str, lines: dict[str, str]) -> tuple[str, ...]:
    """The lines this strategy needs, given what is written: `End: all` adds what an incremental rewrite owes."""
    needed = REQUIRED.get(strategy, ())
    if strategy == "strangler-fig" and str(lines.get("End", "")).lower().startswith("all"):
        needed = (*needed, *(name for name in END_ALL if name not in needed))
    return needed


def missing(strategy: str, lines: dict[str, str]) -> list[str]:
    """The required lines the ADR does not answer. A freeze is answered only by `agreed` or `absent`."""
    gaps = [name for name in required(strategy, lines) if not lines.get(name)]
    freeze = lines.get("Freeze", "")
    if "Freeze" in required(strategy, lines) and freeze and not re.match(r"(agreed|absent)\b", freeze.lower()):
        gaps.append("Freeze")
    return gaps


def review_in_date(lines: dict[str, str], today: datetime.date | None = None) -> bool:
    """Whether a left system's review is still ahead of it. No date is a review nobody set, so never in date."""
    found = DATE.search(lines.get("Review", ""))
    if not found:
        return False
    try:
        return datetime.date.fromisoformat(found.group(1)) >= (today or datetime.date.today())
    except ValueError:
        return False
