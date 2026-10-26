"""Deciding the strategy on the board: one question per line the decided strategy cannot start without.

A strategy was a radio button and a reason, and the ADR the board wrote said `Strategy: rewrite` and nothing else —
so nothing downstream knew where the new system lived or what it was built on, and the first feature went into the
old stack. The form now asks what `strategy_record.REQUIRED` names for the strategy picked, shows only those, and
writes each answer as its line on the ADR, so the record is complete the moment it is decided.

A rewrite is the one choice the form argues with: wanting a new stack is not a reason for a single cut-over, and a
strangler fig with its new home `beside` and `End: all` reaches the same place with the risk going down one
capability at a time. So picking it shows that suggestion, one press away, and the line that has to justify it.
"""
from __future__ import annotations

import datetime
from collections.abc import Mapping

from .errors import GenerationError
from .page_shell import esc
from .stack_proposal import Proposal, installed_backends, installed_frontends
from .strategy_record import missing

STRATEGIES = {
    "leave-it": "leave it — keep it as it is, reviewed, with the risk owned",
    "in-place": "in place — change the code where it stands",
    "strangler-fig": "strangler fig — a new home takes over one capability at a time",
    "rewrite": "rewrite — a new system replaces it in one cut-over",
}
TARGETS = ("modules in one deployable, hexagonal inside each", "modules in one deployable, as they are inside",
           "services, hexagonal inside each", "as-is")
PARITY = "every behaviour on docs/parity.md passes against both systems, or is marked fix or drop"


def months_ahead(months: int, today: datetime.date | None = None) -> str:
    day = today or datetime.date.today()
    year, month = divmod(day.month - 1 + months, 12)
    return day.replace(year=day.year + year, month=month + 1, day=min(day.day, 28)).isoformat()


def radios(name: str, options: Mapping[str, str], checked: str, only: Mapping[str, str] | None = None) -> str:
    """Radio buttons, each optionally shown only for some strategies (`only`: value -> space-separated list)."""
    return '<div class="checks">' + "".join(
        f'<label class="check"{f" data-for={chr(34)}{only[value]}{chr(34)}" if only and value in only else ""}>'
        f'<input type="radio" name="{name}" value="{esc(value)}"{" checked" if value == checked else ""}> '
        f"<span>{esc(said)}</span></label>" for value, said in options.items()) + "</div>"


def field(name: str, label: str, value: str = "", kind: str = "text", hint: str = "") -> str:
    box = (f'<textarea id="{name}" name="{name}" rows="2" placeholder="{esc(hint)}">{esc(value)}</textarea>'
           if kind == "area" else
           f'<input id="{name}" name="{name}" type="{kind}" value="{esc(value)}" placeholder="{esc(hint)}">')
    return f'<div class="q"><label for="{name}">{esc(label)}</label>{box}</div>'


def select(name: str, label: str, options: list[str], chosen: str | None) -> str:
    rows = "".join(f'<option value="{esc(one)}"{" selected" if one == chosen else ""}>{esc(one)}</option>'
                   for one in options)
    return (f'<div class="q"><label for="{name}">{esc(label)}</label>'
            f'<select id="{name}" name="{name}">{rows}</select></div>')


def stack(proposal: Proposal | None) -> str:
    """The new home's stack, proposed from the survey and changeable; a missing language package is said."""
    if proposal is None:
        return ""
    backends = installed_backends()
    chosen = proposal.backend if proposal.backend in backends else (backends[0] if backends else None)
    said = "".join(f"<li>{esc(reason)}</li>" for reason in proposal.because)
    lacking = "".join(
        f'<p class="said bad">The proposal is in {esc(name)}, which this machine has no package for: '
        f"<code>slipwai language install {esc(name)}</code> adds it, or pick another below.</p>"
        for name in proposal.missing)
    return ('<div data-for="strangler-fig rewrite" data-when="home=beside,new-repo">'
            f'<h3>The new home\'s stack</h3><ul class="lines">{said}</ul>{lacking}'
            + select("backend", "Backend", backends, chosen)
            + select("frontend", "Browser app", installed_frontends(), proposal.frontend)
            + select("persistence", "Persistence", ["memory", "sqlite", "postgres"], proposal.persistence) + "</div>")


def form(recommended: str | None, proposal: Proposal | None = None, name: str = "next") -> str:
    """The whole decide step: the strategy, then the lines it needs, each shown only where it applies."""
    pick = recommended if recommended in STRATEGIES else "in-place"
    picked = radios("strategy", {key: said + (" (recommended)" if key == recommended else "")
                                 for key, said in STRATEGIES.items()}, pick)
    rewrite_note = (
        '<div data-for="rewrite"><p class="said">Wanting a new stack, or the old system gone, is not on its own a '
        "reason for one cut-over: a strangler fig with its new home beside it and <b>End: all</b> gets the same "
        'result, with the risk going down one capability at a time.</p><div class="ask"><button type="button" '
        'class="install" id="use-strangler">Use a strangler fig instead</button></div>'
        + field("why_cutover", "Why one cut-over, and not a strangler fig", kind="area",
                hint="e.g. the old system cannot be put behind a seam; its data cannot be split; "
                     "it is switched off on a fixed date")
        + field("cutover_by", "Who decides the cut-over", hint="a named person")
        + field("rollback", "How the cut-over is rolled back", kind="area",
                hint="how, within what window, and what happens to writes made after the switch") + "</div>")
    leave = ('<div data-for="leave-it">'
             + radios("variant", {"retain": "retain — keep it running", "sunset-by-date": "sunset by a date",
                                  "sunset-to-product": "sunset to a product that replaces it"}, "retain")
             + field("variant_said", "The date, or the product", hint="only for a sunset")
             + field("risk_owner", "Who owns the risk", hint="a named person with authority to accept it")
             + field("review", "Review by", months_ahead(6), kind="date") + "</div>")
    freeze = ('<div data-for="strangler-fig rewrite"><h3>The freeze</h3>'
              + radios("freeze", {"agreed": "agreed — no new features in the old system, fixes only",
                                  "absent": "absent — nobody will agree to one"}, "agreed")
              + field("freeze_said", "Who agreed it and when — or what is done instead") + "</div>")
    home = ('<div data-for="strangler-fig rewrite"><h3>Where the new home lives</h3>'
            + radios("home", {"inside": "inside — new modules in the same deployable",
                              "beside": "beside — a new deployable in this repository",
                              "new-repo": "a new repository"}, "beside",
                     only={"inside": "strangler-fig", "new-repo": "rewrite"})
            + field("home_path", "Its name or path", f"apps/{name}") + "</div>")
    end = ('<div data-for="strangler-fig"><h3>How much moves</h3>'
           + radios("end", {"all": "all — the old app is deleted at the end (the incremental rewrite)",
                            "partial": "partial — only what has to change moves; the rest stays, frozen"}, "all")
           + "</div>")
    # A rewrite always owes these; a strangler fig only when everything moves.
    owed = ('<div data-when="end=all" data-for="strangler-fig rewrite">'
            + field("checkpoint", "Checkpoint", months_ahead(6), kind="date")
            + field("parity", "What “the same” means", PARITY) + "</div>")
    target = ('<div data-for="in-place strangler-fig rewrite">'
              + select("target", "Target shape", list(TARGETS), TARGETS[0]) + "</div>")
    return (f'<form class="ask-page" id="step-form">{picked}{rewrite_note}{leave}{freeze}{home}{end}{owed}'
            f"{stack(proposal)}{target}"
            + field("why", "Why this one, in your words", kind="area", hint="the business trigger, and what it answers")
            + '</form><div class="ask"><button class="go" data-step="strategy">Decide</button></div>'
            f"<script>{SCRIPT}</script>")


def lines(answers: Mapping[str, str], today: datetime.date | None = None) -> tuple[str, dict[str, str]]:
    """The strategy picked and the ADR lines its answers make, refused where one it cannot start without is empty."""
    said = {key: str(value).strip() for key, value in answers.items() if isinstance(value, str)}
    strategy = said.get("strategy", "")
    if strategy not in STRATEGIES:
        raise GenerationError(f"pick one of the four strategies: {', '.join(STRATEGIES)}")
    out: dict[str, str] = {}
    if said.get("why"):
        out["Why"] = said["why"]
    if strategy == "leave-it":
        variant = said.get("variant") or "retain"
        out["Variant"] = f"{variant} {said.get('variant_said', '')}".strip() if variant != "retain" else "retain"
        out["Risk-owner"] = said.get("risk_owner", "")
        out["Review"] = said.get("review", "")
        out["Target"] = "as-is"
        out["Build"] = "pinned, the toolset current only where it does not change what is produced"
    else:
        out["Target"] = said.get("target", "")
    if strategy in ("strangler-fig", "rewrite"):
        freeze = said.get("freeze") or "agreed"
        out["Freeze"] = f"{freeze} — {said['freeze_said']}" if said.get("freeze_said") else ""
        place = said.get("home") or "beside"
        place = "beside" if strategy == "rewrite" and place == "inside" else place
        where = said.get("home_path", "")
        if strategy == "strangler-fig":
            place = "beside" if place == "new-repo" else place
            out["New home"] = f"{place} {where}".strip()
            by = f" by {said['checkpoint']}" if said.get("checkpoint") else ""
            out["End"] = (f"all — the old app is deleted{by}" if (said.get("end") or "all") == "all"
                          else "partial — only the capabilities that need to change move; the old home stays, frozen")
        else:
            out["Home"] = f"{place} {where}".strip()
            out["Why single cut-over"] = said.get("why_cutover", "")
            out["Cut-over"] = f"single — decided by {said['cutover_by']}" if said.get("cutover_by") else ""
            out["Rollback"] = said.get("rollback", "")
        if place != "inside" and said.get("backend"):
            out["Stack" if strategy == "rewrite" else "New home stack"] = (
                f"backend {said['backend']} · frontend {said.get('frontend') or 'none'} · "
                f"persistence {said.get('persistence') or 'memory'}")
        if strategy == "rewrite" or out.get("End", "").startswith("all"):
            out["Parity"] = said.get("parity") or PARITY
            out["Checkpoint"] = said.get("checkpoint", "")
        out["Build"] = ("up-to-date: the toolset current, the target raised to its ceiling" if place == "inside" else
                        "pinned as-is: the old build in a container with its old toolchain")
    if strategy == "in-place":
        out["Build"] = "up-to-date: the toolset current, the target raised to its ceiling"
    answered = {name: value for name, value in out.items() if value}
    gaps = missing(strategy, answered)
    if gaps:
        raise GenerationError("still to say: " + ", ".join(gaps) + " — the strategy cannot start without them")
    return strategy, answered


#: The page half: show only the questions the strategy picked, and the parts of them its answers call for.
SCRIPT = """
(() => {
  const form = document.getElementById('step-form');
  if (!form || !form.querySelector('[name=strategy]')) return;
  const value = name => (form.querySelector(`[name=${name}]:checked`)
                         || form.querySelector(`[name=${name}]`) || {}).value;
  const show = () => {
    const strategy = value('strategy');
    // `display` rather than `hidden`: a `.check` label's own display would win over the attribute.
    const set = (part, off) => { part.hidden = off; part.style.display = off ? 'none' : ''; };
    form.querySelectorAll('[data-for]').forEach(part => set(part, !part.dataset.for.split(' ').includes(strategy)));
    form.querySelectorAll('[data-when]').forEach(part => {
      if (part.dataset.for && part.hidden) return;
      const [name, wanted] = part.dataset.when.split('=');
      const now = value(name);
      set(part, !wanted.split(',').includes(now) && !(name === 'end' && strategy === 'rewrite'));
    });
  };
  form.addEventListener('change', show);
  const instead = document.getElementById('use-strangler');
  if (instead) instead.addEventListener('click', () => {
    form.querySelector('[name=strategy][value=strangler-fig]').checked = true;
    form.querySelector('[name=home][value=beside]').checked = true;
    form.querySelector('[name=end][value=all]').checked = true;
    show();
  });
  show();
})();
"""
