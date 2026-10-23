"""The Try it card on the Voyage tab: trunk's newest merge, running for a person to use, from one button.

The Voyage tab linked to `localhost:5173` whether or not anything answered there, and what answered — when
somebody had started it — showed none of the voyage's work: flags off, nobody allowed to sign in, an empty
database. The project's `scripts/agents/try_it.py` is what starts it properly, and this card is its face:
what it is doing, who to sign in as, what is new to try, and the four things a person does to it.

**The state is the script's file, read here.** `.slipwai/try-it/state.json` is written by the script as it
works, and this card reads it on every poll rather than asking the script: a poll every few seconds that
started a Python and a login shell each time would cost more than the app it describes. What only a reader
can say — whether its processes are still alive, and how far trunk has moved since it started — is said here.

**Started detached.** The board hands the verb to the script and returns. The app outlives the board, as
the fleet does, so restarting the board never takes away the thing a person has open.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from urllib.parse import quote, unquote

from . import process_alive
from .feedback_card import opener
from .page_shell import esc

# budget: 440 — one card in four states and the routes' half of it: what Try it is doing, the app and who to
# sign in as, its example records grouped by that person, what to try, its switches and its recorded walks.

#: Where the demo hand's recordings are served from: `/walks/<feature>/<slice>/<example>.webm`.
WALK_ROUTE = "/walks/"
#: What a recording may be. A route that served the folder's anything would serve whatever lands in it.
VIDEOS = {".webm": "video/webm", ".mp4": "video/mp4"}
#: The one tab every link into the app opens in. An app that keeps its sign-in per tab — `sessionStorage`,
#: which hr-test-2's does on purpose — is signed out in every new tab, so a card whose links each opened one
#: said "your sign-in has ended" on every record a person had just signed in to see. Named rather than
#: `_blank`, and without `noopener`, which would make a browser open a new tab for the name every time.
APP_TAB = "try-it-app"
#: What each button asks the script to do.
VERBS = ("start", "refresh", "fresh", "stop", "flag")
#: How each state is said on the chip.
CHIPS = {"stopped": "stopped", "starting": "starting", "ready": "ready", "failed": "didn't start"}

STYLE = """
#try .head{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;justify-content:space-between}
#try .head h2{margin:0;display:flex;gap:10px;align-items:center}
#try .pill{font-size:.72rem;font-weight:500;padding:2px 9px;border-radius:999px;border:1px solid var(--rule);
  color:var(--ink-2);background:var(--rule-2)}
#try .pill.starting{border-color:var(--brass);color:var(--brass);background:var(--brass-soft)}
#try .pill.ready{border-color:var(--teal);color:var(--teal);background:var(--teal-soft)}
#try .pill.failed{border-color:#b4432f;color:#b4432f;background:transparent}
#try .buttons{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
#try .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin-top:12px}
#try .fact b{display:block;font-size:.72rem;font-weight:500;letter-spacing:.06em;text-transform:uppercase;
  color:var(--ink-3)}
#try .fact span{font-size:.88rem}
#try h3{font-size:.78rem;letter-spacing:.06em;text-transform:uppercase;color:var(--ink-3);margin:16px 0 6px}
#try table{border-collapse:collapse;font-size:.86rem;width:100%}
#try td{padding:4px 12px 4px 0;vertical-align:top}
#try td.who{white-space:nowrap}
#try ol.steps,#try ul.new{margin:0;padding-left:18px;display:grid;gap:4px;font-size:.84rem;color:var(--ink-2)}
#try ul.new{list-style:none;padding:0;gap:10px}
#try ul.new .sid{font-family:var(--mono);font-size:.74rem;padding:1px 6px;border-radius:4px;
  background:var(--teal-soft);color:var(--teal);margin-right:6px}
#try ul.new ol{margin-top:4px}
#try pre.said{max-height:180px;overflow:auto}
#try .flag{display:flex;gap:10px;align-items:center;font-size:.86rem;margin:4px 0}
#try .flag code{flex:1}
#try .warn{color:#b4432f;font-size:.86rem}
#try .as-group{border-left:3px solid var(--teal);padding:2px 0 2px 12px;margin:8px 0 12px}
#try .as{margin:0 0 6px;font-size:.88rem}
"""

SCRIPT = """
// Try it: the card repaints itself from /try.json, faster while it is starting, and its buttons hand the
// verb to the project's script and come straight back.
(function(){
  const card = () => document.getElementById('try');
  if (!card()) return;
  const poll = async () => {
    let found;
    try { found = await (await fetch('/try.json')).json(); }
    catch (fault) { setTimeout(poll, 10000); return; }
    const now = card();
    if (now && found.html && now.dataset.said !== found.said) {
      const open = [...now.querySelectorAll('details[open]')].map(one => one.id);
      now.outerHTML = found.html;
      open.forEach(id => { const one = document.getElementById(id); if (one) one.open = true; });
    }
    setTimeout(poll, found.state === 'starting' ? 2000 : 8000);
  };
  setTimeout(poll, 2000);
  document.addEventListener('click', async event => {
    const verb = event.target.dataset && event.target.dataset.try;
    if (!verb) return;
    event.target.disabled = true;
    const answer = await fetch('/try', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({verb, key: event.target.dataset.key || '', value: event.target.dataset.value || ''})});
    if (!answer.ok) { event.target.disabled = false; alert(await answer.text()); return; }
    setTimeout(poll, 500);
  });
})();
"""


def script_of(root: Path) -> Path | None:
    """The project's own Try it script, where it has one: a project generated before it has the old link."""
    try:
        manifest = json.loads((root / "project.json").read_text(encoding="utf-8"))
        delivery = str((manifest.get("layout") or {}).get("delivery") or ".")
    except (OSError, ValueError, UnicodeDecodeError, AttributeError):
        delivery = "."
    script = root / delivery / "scripts/agents/try_it.py"
    return script if script.is_file() and script.resolve().is_relative_to(root.resolve()) else None


def alive(pid: object) -> bool:
    """Whether the process the state names is still running, asked through `process_alive` and never with
    `os.kill(pid, 0)`: signal 0 is a Ctrl-C to the whole console on Windows, and the board asking after a
    try-it process ended the suite that asked."""
    try:
        return process_alive.alive(int(str(pid)))
    except ValueError:
        return False


def trunk_head(root: Path) -> str:
    for candidate in ("main", "master", "origin/main", "origin/master"):
        done = subprocess.run(["git", "-C", str(root), "rev-parse", "--verify", "--quiet", candidate],
                              capture_output=True, text=True, check=False)
        if done.returncode == 0 and done.stdout.strip():
            return done.stdout.strip()
    return ""


def status(root: Path) -> dict:
    """The script's state, with what only a reader can tell: a process that has gone, and how far behind
    trunk the running copy is."""
    try:
        state = json.loads((root / ".slipwai/try-it/state.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        state = {}
    if not isinstance(state, dict) or state.get("state") not in CHIPS:
        state = {"state": "stopped"}
    if state["state"] == "ready":
        gone = [name for name, pid in (state.get("pids") or {}).items() if not alive(pid)]
        if gone:
            state.update(state="failed", error=f"{', '.join(gone)} stopped; its log is in .slipwai/try-it/")
    if state["state"] == "starting" and not alive(state.get("runner")):
        state.update(state="failed", error=f"stopped while {state.get('step') or 'starting'}")
    head, commit = trunk_head(root), str(state.get("commit", ""))
    behind = 0
    if head and commit and head != commit:
        done = subprocess.run(["git", "-C", str(root), "rev-list", "--count", f"{commit}..{head}"],
                              capture_output=True, text=True, check=False)
        behind = int(done.stdout.strip() or 0) if done.returncode == 0 else 0
    state["behind"] = behind
    return state


def act(root: Path, verb: str, key: str = "", value: str = "") -> str:
    """Hand one verb to the project's script, detached, and say that it was handed."""
    from .fleet import project_python
    from .shell_environment import login_environment

    if verb not in VERBS:
        raise ValueError(f"Try it has no {verb!r}; it can {', '.join(VERBS)}")
    script = script_of(root)
    if script is None:
        raise ValueError("this project has no scripts/agents/try_it.py. Run `slipwai migrate` to add it")
    if verb != "stop" and status(root)["state"] == "starting":
        raise ValueError("Try it is still starting; wait for it to finish")
    argv = [project_python(), "-B", str(script), verb]
    if verb == "flag":
        if not key or value not in ("on", "off"):
            raise ValueError("a flag needs its name and on or off")
        argv += [key, value]
    home = root / ".slipwai/try-it"
    home.mkdir(parents=True, exist_ok=True)
    with (home / "board.log").open("a", encoding="utf-8") as out:
        subprocess.Popen(argv, cwd=root, env=login_environment(), stdout=out, stderr=subprocess.STDOUT,
                         stdin=subprocess.DEVNULL, start_new_session=True)
    return f"Try it: {verb}"


def button(verb: str, face: str, primary: bool = False, **data: str) -> str:
    extra = "".join(f' data-{name}="{esc(value)}"' for name, value in data.items())
    kind = "go" if primary else "install"
    return f'<button type="button" class="{kind}" data-try="{verb}"{extra}>{esc(face)}</button>'


def credentials(person: dict) -> str:
    return (f'<code>{esc(person.get("username", ""))}</code> · password '
            f'<code>{esc(person.get("password", ""))}</code>')


def people_html(state: dict) -> str:
    """Everyone the example data does not already sign in as: the people a story leaves out are the ones a
    person tries a refusal with, and the card should not make them look up a realm file to find them."""
    used = {str(one.get("as", "")) for one in state.get("links") or []}
    rest = [one for one in state.get("people") or [] if one.get("username") not in used]
    if not rest:
        return ""
    rows = "".join(f'<tr><td class="who"><b>{esc(one.get("name", ""))}</b></td><td>{credentials(one)}</td></tr>'
                   for one in rest)
    heading = "Also there to sign in as" if used - {""} else "Sign in as"
    return f"<h3>{heading}</h3><table>{rows}</table>"


def into_app(url: str, path: str, slice_id: str, who: str, commit: str) -> str:
    """A link into the app carrying its context — the slice, who the person is signed in as, trunk's commit
    — so what a person types after clicking it lands with the slice it was about (`feedback.CONTEXT`)."""
    held = {"slice": slice_id.rsplit("/", 1)[-1], "as": who, "trunk": commit[:7]}
    query = "&".join(f"{key}={quote(value, safe='')}" for key, value in held.items() if value)
    joiner = "&" if "?" in path else "?"
    return esc(f"{url}{path}{joiner}{query}" if query else f"{url}{path}")


def links_html(state: dict) -> str:
    """The records the example data made, grouped by who to sign in as to see them — the person each
    slice's story was told as, since a record one person owns may be refused to another — each a link into
    the app, which is the only way to reach a record in an app with no list of them yet. A record the story
    *gave* rather than made says so: the upstream slice is not built, and what the person is looking at is
    this slice seeded to a state."""
    url, commit = str(state.get("url", "")), str(state.get("commit", ""))
    people = {str(one.get("username", "")): one for one in state.get("people") or []}
    groups: dict[str, list[dict]] = {}
    for one in state.get("links") or []:
        groups.setdefault(str(one.get("as", "")), []).append(one)
    blocks = ""
    for who, links in groups.items():
        person = people.get(who, {"name": who, "username": who})
        head = (f'<p class="as">Sign in as <b>{esc(person.get("name") or who)}</b> · {credentials(person)}</p>'
                if who else '<p class="as">Signed in as the person the slice\'s story names</p>')
        rows = "".join(f'<li><span class="sid">{esc(str(one.get("slice", "")).rsplit("/", 1)[-1])}</span>'
                       f'<a href="{into_app(url, str(one.get("path", "")), str(one.get("slice", "")), who, commit)}" '
                       f'target="{APP_TAB}">{esc(one.get("label") or one.get("path", ""))}</a>'
                       + (' <span class="empty">· given, not made: its upstream is not built</span>'
                          if one.get("given") else "") + "</li>" for one in links)
        blocks += f'<div class="as-group">{head}<ul class="new">{rows}</ul></div>'
    if not blocks:
        return ""
    return ('<h3>Example data, by who to sign in as</h3><p class="empty">Sign in once, in the app\'s tab: every '
            "link on this card opens in that same tab, which keeps the sign-in.</p>" + blocks)


def new_html(state: dict) -> str:
    """What to try, and what merged dark. *New to try* lists the slices whose story seeded — each with its
    links first and its quickstart steps under a disclosure; *Merged but dark* lists the rest, each with
    the one line that says why: the step that refused and what it said, or the need that keeps it dark. A
    card that listed fifteen slices' curl commands over fifteen stories answering 401 was telling a person
    there was something to try (recap, 2026-10-22)."""
    found = state.get("new") or []
    if not found:
        return ""
    first = not state.get("previous")
    people = {str(one.get("username", "")): one for one in state.get("people") or []}
    url, commit = str(state.get("url", "")), str(state.get("commit", ""))
    links: dict[str, list[dict]] = {}
    for one in state.get("links") or []:
        links.setdefault(str(one.get("slice", "")).rsplit("/", 1)[-1], []).append(one)
    # An older state.json has no `dark` on its rows and no `seeded` list: every new slice reads as dark then,
    # until the next `make try-update` writes a state that says which seeded.
    lit = [one for one in found if not one.get("dark") and (state.get("seeded") is not None or "dark" in one)]
    dark = [one for one in found if one not in lit]

    def who(one: dict) -> str:
        person = people.get(str(one.get("as", "")))
        return (f' <span class="empty">· sign in as {esc(person.get("name") or person.get("username", ""))}'
                f"</span>") if person else ""

    def steps(one: dict) -> str:
        listed = "".join(f"<li>{esc(step)}</li>" for step in one.get("steps") or [])
        return (f'<details><summary class="empty">its quickstart\'s steps</summary><ol class="steps">{listed}</ol>'
                f"</details>") if listed else ""

    def opens(one: dict) -> str:
        mine = links.get(str(one.get("slice", "")), [])
        slice_id = str(one.get("slice", ""))
        return "".join(
            f' <a href="{into_app(url, str(link.get("path", "")), slice_id, str(link.get("as", "")), commit)}"'
            f' target="{APP_TAB}">{esc(link.get("label") or link.get("path", ""))}</a>' for link in mine)

    lit_items = "".join(
        f'<li><span class="sid">{esc(one.get("slice", ""))}</span><b>{esc(one.get("title", ""))}</b>{who(one)}'
        + (' <span class="empty">· given, not made</span>' if one.get("given") else "")
        + opens(one) + steps(one) + "</li>" for one in lit)
    dark_items = "".join(
        f'<li class="warn"><span class="sid">{esc(one.get("slice", ""))}</span><b>{esc(one.get("title", ""))}</b> '
        f'<span>— {esc(one.get("dark") or "its story did not seed")}</span></li>' for one in dark)
    when = "" if first else " since the last update"
    shown = ""
    if lit:
        shown += (f'<details id="try-new" open><summary><h3 style="display:inline">New to try{esc(when)} · {len(lit)}'
                  f'</h3></summary><ul class="new">{lit_items}</ul></details>')
    if dark:
        shown += (f'<details id="try-dark"{" open" if not lit else ""}><summary><h3 style="display:inline">Merged but '
                  f'dark{esc(when)} · {len(dark)}</h3></summary><p class="empty">Merged, and nothing a person can '
                  f'try yet: each line says what refused its story, or what it still needs on trunk.</p>'
                  f'<ul class="new">{dark_items}</ul></details>')
    return shown


def flags_html(state: dict) -> str:
    flags = state.get("flags") or {}
    if not flags:
        return ""
    rows = "".join(
        f'<div class="flag"><code>{esc(key)}</code><span>{esc(value)}</span>'
        + button("flag", "Turn off" if value == "on" else "Turn on", key=key,
                 value="off" if value == "on" else "on") + "</div>"
        for key, value in sorted(flags.items()))
    on = sum(1 for value in flags.values() if value == "on")
    return (f'<details id="try-flags"><summary><h3 style="display:inline">Unreleased work shown · {on} of '
            f'{len(flags)} switches on</h3></summary>{rows}</details>')


def walks_of(root: Path, seat: str = "") -> list[dict]:
    """Every recording the demo hand left, newest walk of each example, in slice and example order."""
    home = root / ".slipwai/walks"
    found = []
    for path in sorted(home.glob("*/*/*")) if home.is_dir() else []:
        if path.suffix.lower() not in VIDEOS or not path.is_file():
            continue
        feature, slice_id = path.parent.parent.name, path.parent.name
        where = "/".join(quote(part, safe="") for part in (feature, slice_id, path.name))
        query = "&".join(([f"seat={quote(seat, safe='')}"] if seat else []) + [f"v={path.stat().st_mtime_ns}"])
        found.append({"feature": feature, "slice": slice_id, "example": path.stem,
                      "href": f"{WALK_ROUTE}{where}?{query}"})
    return found


def walk_file(root: Path, where: str) -> Path | None:
    """The recording a `/walks/<feature>/<slice>/<name>` request names, or nothing where it names anything
    else — a path out of the folder, or a file that is not a video."""
    feature, _, rest = unquote(where).partition("/")
    slice_id, _, name = rest.partition("/")
    if not feature or not slice_id or not name or "/" in name or Path(name).suffix.lower() not in VIDEOS:
        return None
    home = (root / ".slipwai/walks").resolve()
    try:
        path = (home / feature / slice_id / name).resolve()
    except OSError:
        return None
    return path if path.is_relative_to(home) and path.is_file() else None


def walks_html(found: list[dict]) -> str:
    """The recordings, a row per slice: what a person watches before they have time to use the thing."""
    if not found:
        return ""
    rows, slices = "", []
    for one in found:
        if one["slice"] not in slices:
            slices.append(one["slice"])
    for slice_id in slices:
        mine = [one for one in found if one["slice"] == slice_id]
        links = " · ".join(f'<a href="{esc(one["href"])}" target="_blank" rel="noopener">{esc(one["example"])}</a>'
                           for one in mine)
        rows += f'<li><span class="sid">{esc(slice_id)}</span>{links}</li>'
    return (f'<details id="try-walks" open><summary><h3 style="display:inline">Watch it work · {len(found)} '
            f'walked example{"s" if len(found) != 1 else ""}</h3></summary><ul class="new">{rows}</ul></details>')


def card(root: Path, seat: str = "") -> str:
    """The card, or nothing where the project has no Try it script yet."""
    if script_of(root) is None:
        return ""
    return card_html(status(root), walks_of(root, seat))


def card_html(state: dict, walks: list[dict] | None = None) -> str:
    kind = state["state"]
    chip = CHIPS[kind] + (f" · {state.get('step')}" if kind == "starting" and state.get("step") else "")
    commit = str(state.get("commit", ""))[:7]
    if kind == "stopped":
        body = ('<p class="empty">Runs trunk\'s newest merge on this machine, on ports of its own beside the '
                "fleet, with every merged slice switched on and each slice's example data loaded. A few "
                "minutes the first time; its data is kept between runs.</p>")
        buttons = button("start", "Start", primary=True)
    elif kind == "starting":
        steps = state.get("steps") or []
        lines = "\n".join(f"✓ {one}" for one in steps[:-1]) + (f"\n› {steps[-1]}" if steps else "")
        body = f'<pre class="said">{esc(lines.strip())}</pre>'
        buttons = button("stop", "Stop")
    elif kind == "failed":
        log = "\n".join(state.get("log") or [])
        body = (f'<p class="warn">{esc(state.get("error", ""))}</p>'
                + (f'<pre class="said">{esc(log)}</pre>' if log else "")
                + '<p class="empty">The whole log is in .slipwai/try-it/.</p>')
        buttons = button("start", "Start again", primary=True) + button("stop", "Stop")
    else:
        url = str(state.get("url", ""))
        behind = int(state.get("behind", 0) or 0)
        newer = f"{behind} newer commit{'s' if behind != 1 else ''} on trunk" if behind else "up to date"
        failed = state.get("seed_failed") or []
        first_reason = f" — {failed[0].get('said', '')}"[:80] if failed else ""
        facts = (("Showing", f"trunk at {commit}"), ("Trunk", newer), ("Address", url.removeprefix("http://")),
                 ("Example data", f"{len(state.get('seeded') or [])} slices loaded"
                  + (f", {len(failed)} dark{first_reason}" if failed else "")))
        body = ('<div class="grid">'
                + "".join(f'<div class="fact"><b>{esc(a)}</b><span>{esc(b)}</span></div>' for a, b in facts)
                + "</div>" + links_html(state) + people_html(state) + new_html(state)
                + flags_html(state))
        buttons = (f'<a class="quiet" href="{esc(url)}" target="{APP_TAB}">Open the app ↗</a>'
                   + opener("What did using it show?", {"from": "try-it", "trunk": commit,
                                                       "slice": str((state.get("new") or [{}])[0].get("slice", ""))
                                                       if len(state.get("new") or []) == 1 else ""}, primary=True)
                   + (button("refresh", "Update to newest") if behind else "")
                   + button("fresh", "Start over with fresh data") + button("stop", "Stop"))
    said = said_of(state, walks or [])
    return (f'<div class="card" id="try" data-said="{esc(said)}"><div class="head"><h2>Try it '
            f'<span class="pill {esc(kind)}">{esc(chip)}</span></h2><div class="buttons">{buttons}</div></div>'
            f"{body}{walks_html(walks or [])}</div>")


def said_of(state: dict, walks: list[dict]) -> str:
    """What the card shows, in one line: a poll that finds the same line leaves the card alone."""
    return json.dumps([state["state"], state.get("step"), str(state.get("commit", ""))[:7], state.get("behind"),
                       state.get("flags"), len(state.get("seeded") or []), len(state.get("steps") or []),
                       [one["href"] for one in walks]])


def payload(root: Path, seat: str = "") -> str:
    if script_of(root) is None:
        return json.dumps({"state": "stopped", "said": "", "html": ""})
    state, walks = status(root), walks_of(root, seat)
    return json.dumps({"state": state["state"], "said": said_of(state, walks), "html": card_html(state, walks)})
