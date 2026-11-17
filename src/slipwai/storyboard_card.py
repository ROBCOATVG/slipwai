"""The storyboard on the Voyage's Screens tab: the drawing, what it found, a verdict, and a conversation about it.

The surfaces stage ran eight minutes headless on the first real run and nobody looking at the Screens tab
could tell; the card appeared when it was done. It had reviewed seven pages and written eighty-four findings
and a list of questions, and the person's two moves were to approve all forty-nine states or redraw them
all. So the tab now says a stage is drawing while it draws — a card in the storyboard's place with what it
is doing and for how long, and a mark on the tab — and once it is drawn the findings are under it, Blockers
first, each a way into a conversation with the session that drew it.

**Talking never approves.** The conversation resumes the stage's kept session, which already holds the
research and the review; it may change a page when asked, and a page it changes loses its verdict
(`drawn.withdraw`). Approve and Disapprove are the only verdicts there are, and stay buttons.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from . import stage_talk
from .drawn import decided_states, withdrawn_parts
from .init_run import outside_session, resumed
from .page_shell import esc
from .passage import surface_pages
from .review_reading import RESEARCH, reading
from .stage_session import kept_stage
from .storyboard_script import SCRIPT as SCRIPT  # the card's look and script, read by name by the Voyage page
from .storyboard_script import STYLE as STYLE
from .upstream import NAMED, advancing, held_by

#: The stages whose result has a tab of its own, by the step the board's run is on and the command it runs.
WATCHED = {"surfaces": "mockups", "model": "model"}
SAYS = {"surfaces": ("Storyboard", "Being drawn: the research, the surfaces and the storyboard. The storyboard "
                                   "appears here when the drawing ends, and is listed under Waiting on you."),
        "model": ("The model", "Being modelled from the approved storyboard. The model appears here when the "
                               "stage ends.")}


def live(board: Any) -> dict[str, Any]:
    """Which stage with a tab of its own is running now — `surfaces`, `model` or nothing — for how long, what
    it is doing, and whether the storyboard has a session a conversation can carry on. A turn of
    conversation is not the stage running: it is the person, talking."""
    fitting = board.fitting
    said = fitting.said(max(fitting.said()["at"] - 1, 0)) if fitting is not None else None
    stage = getattr(fitting, "stage", None)
    running, seconds, doing = "", 0.0, ""
    if said is not None and not said["done"]:
        if not said.get("talking") and said["step"] in WATCHED:
            running, seconds = said["step"], float(said["seconds"])
            doing = (stage.doing() if stage is not None else "") or (said["lines"] or [""])[-1]
    elif (outside := outside_session(board.root)) is not None and outside["step"] in WATCHED:
        running, seconds, doing = outside["step"], float(outside["seconds"]), outside["lines"][0]
    mine = stage is not None and stage.command == "mockups"
    return {"running": running, "seconds": seconds, "doing": doing,
            "talk": mine or stage_talk.kept(board.root, "mockups")}


def payload(board: Any, command: str, since: int) -> dict[str, Any]:
    """`/stage/talk.json`: the conversation with `command`'s stage after `since`, and its live state."""
    root = board.root
    command = command if stage_talk.known(command) else ""
    turns = stage_talk.turns(root, command) if command else []
    shown = turns[since:] if since else turns[-stage_talk.SHOWN:]
    fitting = board.fitting
    stage: Any = getattr(fitting, "stage", None)
    said = fitting.said(10 ** 9) if fitting is not None else {}
    mine = stage is not None and stage.command == command
    # A turn of this stage's conversation under way: the person's, so what it is doing is said in the log.
    busy = bool(mine and not said.get("done", True) and said.get("talking"))
    # Kept and not yet said: queued where a run of this stage is going and will say it at its end; otherwise —
    # after a Stop, or a restart — not delivered, and the page says so and offers to say it now.
    going = {one["id"] for one in stage.queue} if mine and not said.get("done", True) else set()
    kept = [one for one in stage_talk.undelivered(root, command) if one.get("id")] if command else []
    now = live(board)
    why, _ = held_by(board)
    return {"turns": shown, "at": len(turns), "busy": busy, "running": WATCHED.get(now["running"]) == command,
            "seconds": now["seconds"], "doing": (stage.doing() if busy else now["doing"]) if command else "",
            "for": int(said.get("seconds") or 0) if busy else 0,
            "thinking": bool(busy and stage.agent is not None and stage.agent.thinking),
            "queued_ids": [one["id"] for one in kept if one["id"] in going],
            "undelivered": [{"id": one["id"], "text": one["text"]} for one in kept if one["id"] not in going],
            "held": why, "carry": bool(advancing(root) and stage_talk.held(root)),
            "discarded_ids": [one["id"] for one in turns if one.get("discarded")],
            "unkept": stage_talk.unignored(root), "waiting_all": waiting_said(board)}


def waiting_said(board: Any) -> list[dict[str, Any]]:
    """Every message to any stage not yet said, each with whether the turn under way will say it (`live`): the
    stage card and Waiting on you draw it with Say it now and Discard where it will not."""
    fitting = board.fitting
    stage = getattr(fitting, "stage", None)
    going = ({one["id"] for one in getattr(stage, "queue", [])} if stage is not None and fitting is not None
             and not fitting.said(10 ** 9)["done"] else set())
    return [{**one, "live": one["id"] in going, "named": NAMED.get(one["command"], one["command"])}
            for one in stage_talk.waiting_anywhere(board.root)]


def verdict_refused(board: Any) -> str:
    """Why Approve or Disapprove cannot be given now: a turn with the drawing under way, or a message to it
    waiting to be said — a verdict given then is a verdict on pages about to change."""
    fitting = board.fitting
    said = fitting.said(10 ** 9) if fitting is not None else {}
    if getattr(getattr(fitting, "stage", None), "command", "") == "mockups" and said.get("talking") \
            and not said.get("done", True):
        return "the drawing is answering what you said; give your verdict once it has, on what it then shows"
    if stage_talk.undelivered(board.root, "mockups"):
        return ("something you said to the drawing has not been said to it yet; let it answer, or say it now, "
                "before you give your verdict")
    return ""


def talking_to(board: Any, command: str) -> str:
    """The run something said to `command`'s stage goes through — the one the board holds where it is that
    stage's, else that stage's kept session carried on, where nothing else is running — or why there is none.
    With no command, the stage of the board's own run, or the one kept from before a restart."""
    fitting = board.fitting
    command = command or ("" if fitting is not None else kept_stage(board.root))
    if command and not stage_talk.known(command):
        return f"{command!r} is not a stage of this board"
    if refused := stage_talk.unignored(board.root):
        return refused
    if not command or getattr(getattr(fitting, "stage", None), "command", "") == command:
        return ""
    if fitting is not None and not fitting.said()["done"]:
        return f"the {fitting.said()['step'] or 'board'} stage is running; say this to it once it has ended"
    if not stage_talk.kept(board.root, command):
        return f"no session of the {command} stage is kept here, so there is nothing to say that to"
    said = fitting.said() if fitting is not None else None
    # A later stage that failed stays failed: the conversation with an earlier one is not its retry.
    earlier = (said["step"], said["code"]) if said and said["code"] else getattr(fitting, "earlier", None)
    board.fitting = resumed(board.root, command, said["lines"] if said else None, earlier)
    return ""


def placeholder(step: str, now: dict[str, Any]) -> str:
    """The card in a running stage's result's place: what it is doing, and for how long."""
    title, words = SAYS[step]
    seconds = int(now.get("seconds") or 0)
    return (f'<div class="card stage-running" id="{esc(step)}-running" data-stage-watch="{esc(WATCHED[step])}">'
            f'<h2>{esc(title)} <span class="chip running" data-clock data-seconds="{seconds}">running · '
            f'{seconds // 60}:{seconds % 60:02d}</span></h2><p class="empty">{esc(words)}</p>'
            f'<p class="doing" data-doing>{esc(now.get("doing") or "")}</p></div>')


def marker(step: str, now: dict[str, Any] | None) -> str:
    """The mark on a tab's label while its stage runs."""
    running = bool(now and now.get("running") == step)
    word = "drawing" if step == "surfaces" else "modelling"
    return (f'<span class="count running" data-stage-marker="{esc(WATCHED[step])}"{"" if running else " hidden"}>'
            f"{word}</span>")


def talk_card() -> str:
    """The conversation with the session that drew the storyboard, its turns drawn by the script above."""
    return ('<div class="card" id="storyboard-talk" data-command="mockups"><h2>Talk about the storyboard</h2>'
            '<p class="empty">Ask about a finding, ask to see or change a state, or answer one of its questions: '
            "the session that drew it answers, and writes down what you decide. Talking never approves anything "
            "— Approve and Disapprove are the verdicts — and a page changed here waits on yours again.</p>"
            '<p class="held" hidden></p><p class="unkept held" hidden></p>'
            '<div class="log turns" role="log" aria-live="polite"></div>'
            '<form class="ask"><input placeholder="Ask about it, or say what to change…" autocomplete="off" '
            'aria-label="Say something about the storyboard"><button class="go" type="submit">Say</button>'
            '<button class="stop" type="button" hidden>Stop</button>'
            '<button type="button" class="install" data-carry-on hidden>Carry on</button></form></div>')


def findings_html(root: Path, feature: str, base: str) -> str:
    """What the drawing found, collapsed: the drawing's own count first, then the Blockers and the open questions
    as far as they could be read off its files, each a way into the conversation, and every file linked. What is
    listed here decides nothing: where it differs from the drawing's own count, it says so."""
    found = reading(root, feature)
    if not found.files and not found.research:
        return ""
    names = [*found.files, *([RESEARCH] if found.research else [])]
    files = " · ".join(f'<a href="{esc(base)}/{esc(name)}" target="_blank" rel="noopener">{esc(name)}</a>'
                       for name in names)
    words = {"blocker": "Blocker", "should": "Should-address", "nice": "Nice-to-have"}
    own = (f"its own count: {found.blockers_open} Blocker{'' if found.blockers_open == 1 else 's'} and "
           f"{found.questions_open} question{'' if found.questions_open == 1 else 's'} open"
           if found.blockers_open is not None and found.questions_open is not None
           else "it has not declared its own count")
    listed = [f"{sum(one.severity == key for one in found.findings)} {word}" for key, word in words.items()
              if any(one.severity == key for one in found.findings)]
    differ = ((found.blockers_open is not None and found.blockers_open != len(found.blockers))
              or (found.questions_open is not None and found.questions_open != len(found.questions)))
    note = (f"{len(found.blockers)} Blocker{'' if len(found.blockers) == 1 else 's'} and {len(found.questions)} "
            f"question{'' if len(found.questions) == 1 else 's'} listed here, as far as the files could be read; "
            "the count the board goes by is the drawing's own." if differ or found.blockers_open is None else "")
    blockers = "".join(f'<li><span class="where">{esc(one.where)}</span>{esc(one.text)}<button type="button" '
                       f'class="install" data-talk-about="{esc(about(one.where, one.text))}">Ask about this'
                       "</button></li>" for one in found.blockers)
    asked = "".join(f'<li>{esc(one)}<button type="button" class="install" data-talk-about="'
                    f'{esc(f"Answering “{one}”: ")}">Answer this</button></li>' for one in found.questions)
    body = ((f'<p class="empty">{esc(note)}</p>' if note else "")
            + (f"<h3>Blockers</h3><ul>{blockers}</ul>" if blockers else "")
            + (f"<h3>Open questions only you can answer</h3><ul>{asked}</ul>" if asked else "")
            + f'<p class="empty">{files}</p>')
    return (f'<details class="findings" id="findings-{esc(feature)}"><summary>What the drawing found · '
            f'{esc(" · ".join([own, *listed]))}</summary>{body}</details>')


def about(where: str, text: str) -> str:
    return f"About the Blocker{f' on {where}' if where else ''}: “{text}” — "


def verdict_form(root: Path, feature: str) -> str:
    """Approve marks every drawn state approved. Disapprove parks them, and has to say why.

    Only where there is a page per surface to mark: a storyboard with the surfaces drawn inside it has no state
    a verdict can name, and buttons for one were buttons the server refused. That feature is told what is
    missing and what draws it, instead. A verdict a conversation withdrew by changing a page is said by surface,
    and the buttons are back: the storyboard waits on a verdict again.
    """
    home = root / "specs" / feature / "mockups"
    if not surface_pages(home):
        return ('<p class="empty">This storyboard has no page per surface, so there is nothing to approve: '
                "each surface is drawn as its own page, which the storyboard links. Draw the storyboard draws it "
                "again.</p>")
    path = home / "mock-states.md"
    note = "Nothing on this storyboard is approved yet."
    text = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
    parked = next((line.split("parked:", 1)[1].strip()
                   for line in text.splitlines() if "— parked:" in line), "")
    seen, since = withdrawn_parts(root, feature)
    gone = [*seen, *since]
    if gone:
        # "In the conversation" only where the board saw the turn change the page.
        said = [*(f"{one} (in the conversation)" for one in seen), *since]
        note = ("Changed since your verdict, so not approved: " + "; ".join(said)
                + ". Approve or disapprove the storyboard again.")
    elif parked:
        note = (f"Disapproved: {parked}. It is being drawn again from that, and the new drawing waits on a "
                f"verdict of its own.")
    elif "— approved" in text:
        note = "Approved."
    # Where the pages say who chose each state, the note says how many a person decided and how many the
    # tool put in: the person approving knows which states they have already seen.
    who = [one for page in surface_pages(home) for _, one in decided_states(page)[1]]
    if any(who):
        proposed = sum(one.lower() == "proposed" for one in who)
        note += (f" {len(who)} states: {sum(bool(one) for one in who) - proposed} decided by a person, "
                 f"{proposed} proposed.")
    # Either verdict locks both. A refusal (a disapproval with no reason) turns them back on in the page.
    held = " disabled" if (parked or "— approved" in text) and not gone else ""
    return (f'<form class="verdict" onsubmit="return false"><p class="empty{" verdict-gone" if gone else ""}">'
            f"{esc(note)} Approving marks every drawn state approved. Disapproving draws it again from your "
            f'reason.</p><div class="ask"><input id="why-{esc(feature)}" type="text" maxlength="240" '
            f'placeholder="Why, if you disapprove"{held}>'
            f'<button type="button" class="go" data-storyboard="{esc(feature)}" data-verdict="approved"{held}>'
            f'Approve storyboard</button>'
            f'<button type="button" class="install" data-storyboard="{esc(feature)}" data-verdict="parked"{held}>'
            f"Disapprove</button></div></form>")


def mockups_card(found: list[dict[str, str]], root: Path | None = None) -> str:
    """The storyboard the mock-up stage wrote, where it wrote one — every mock-up is reached from it, which
    is what it is for — else the wireframes themselves, shown small; under each feature's verdict, what the
    drawing found. Nothing where the stage has not run."""
    if not found:
        return ""
    features: list[str] = []
    for row in found:
        if row["feature"] not in features:
            features.append(row["feature"])
    base = {row["feature"]: row["href"].rsplit("/", 1)[0] for row in found}
    forms = "".join(verdict_form(root, feature) + findings_html(root, feature, base[feature])
                    for feature in features) if root is not None else ""
    boards = [row for row in found if row["name"] == "storyboard.html"]
    if boards:
        tiles = "".join(
            f'<a class="mock board" href="{esc(row["href"])}" target="_blank" rel="noopener">'
            f'<iframe src="{esc(row["href"])}" loading="lazy" tabindex="-1" title="{esc(row["title"])}"></iframe>'
            f'<b>{esc(row["title"])}</b><span class="fw">{esc(row["feature"])} · '
            f'{sum(1 for one in found if one["feature"] == row["feature"]) - 1} mock-ups, from the storyboard'
            "</span></a>"
            for row in boards)
        return (f'<div class="card" id="mockups"><h2>Storyboard</h2><div class="mocks">{tiles}</div>'
                f"{forms}</div>")
    tiles = "".join(
        f'<a class="mock" href="{esc(row["href"])}" target="_blank" rel="noopener">'
        f'<iframe src="{esc(row["href"])}" loading="lazy" tabindex="-1" title="{esc(row["title"])}"></iframe>'
        f'<b>{esc(row["title"])}</b><span class="fw">{esc(row["feature"])} · {esc(row["name"])}</span></a>'
        for row in found)
    return (f'<div class="card" id="mockups"><h2>Mockups · {len(found)}</h2><div class="mocks">{tiles}</div>'
            f"{forms}</div>")


def screens_band(root: Path, found: list[dict[str, str]], now: dict[str, Any] | None) -> str:
    """The storyboard's part of the Screens tab: a card saying it is being drawn while it is, the storyboard
    once it is, and the conversation with the session that drew it wherever that session is kept."""
    now = now or {}
    drawing = placeholder("surfaces", now) if now.get("running") == "surfaces" else mockups_card(found, root)
    return drawing + (talk_card() if now.get("talk") else "")
