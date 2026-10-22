#!/usr/bin/env python3
"""Casting off: start the harbourmaster and one captain per fairway, and get out of the way.

`cruise.py` was a runner. It held the state of the run, decided what happened next, and died at iteration
two — after which seventeen iterations ran from interactive sessions and it knew about none of them. The
replacement is not a better runner. It is **no runner**: the state lives in the logs, the captains read them,
and the thing you type starts processes and exits.

That is the whole of this file, and the shortness is the point. Nothing here is in the loop, so nothing here
can be the thing that died.

**One captain per fairway the chart names**, under the telegraph's position — `boilers` is how many slice
sessions may run at once across them all, and a captain is at least one, so the rest wait for a berth rather
than all starting and competing for one machine. How the sessions are shared once they are lit is the
harbourmaster's, by `abreast.py`.

**Started detached, and recorded by their pid files.** `--stop` reads them back. A process this started that
is no longer running is said rather than cleaned up quietly: a captain that exited is a fact, and `stop`
pretending it tidied something is how a person stops believing the output.

**The two seat commands are here too, and they read the logs.** `watch` sits and prints every stream's lines
as they are written; `tell` writes one `told` line a stream reads at its next boundary. The runner had both,
reading and writing its own files — a single inbox, a single stream of output, one run's worth of state —
which is exactly what could not survive a second machine. Pointed at the deck logs they need nothing to be
running at all: a `told` written while nothing is lit is read by whatever is lit next.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import clearance  # noqa: E402
import logs  # noqa: E402


def project_root() -> Path:
    for candidate in HERE.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return HERE.parents[1]


ROOT = project_root()
RUNNING = ROOT / ".slipwai/running"
HARBOUR_CONFIG = ROOT / "harbour.json"


def config() -> dict:
    try:
        held = json.loads(HARBOUR_CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return {}
    return held if isinstance(held, dict) else {}


def fairways() -> list[str]:
    """Every fairway the chart names, in the order their captains are lit — slice 18.2.

    `clearance.py` owns the rule and this asks it, because the same order decides two things that must not
    disagree: which captain is lit when there are fewer berths than fairways, and which stream a scarce
    slot goes to once they are running. Two copies of it would be two answers to one question, found on the
    day a person moved a stream up and only half the run noticed.
    """
    charted, _ = clearance.chart()
    return clearance.fairway_order(charted, clearance.preferred_fairways(HARBOUR_CONFIG))


def alive(pid: int) -> bool:
    """Whether that process is still running. Asked, never acted on.

    **`os.kill(pid, 0)` is not a question on Windows.** There `os.kill` is `TerminateProcess`, so the
    signal number is the exit code and 0 is as fatal as any other — this function killed every process it
    was asked about, which is why `fleet list` and a second `fleet start` reported nothing running: they
    had just ended it. So Windows is asked through the process handle instead.

    A process that exited with code 259 reads as running on Windows, because that is the same value as
    `STILL_ACTIVE` and the API has no way to tell them apart. Nothing here exits 259.
    """
    if sys.platform == "win32":  # pragma: no cover - the other platform's branch
        import ctypes  # noqa: PLC0415 - only this branch needs it

        query_limited_information, still_active = 0x1000, 259
        kernel = ctypes.windll.kernel32
        handle = kernel.OpenProcess(query_limited_information, False, pid)
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            if not kernel.GetExitCodeProcess(handle, ctypes.byref(code)):
                return False
            return code.value == still_active
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except (OSError, ProcessLookupError):
        return False
    return True


def recorded() -> dict[str, int]:
    """What was started last time, from the pid files, whether or not it is still running."""
    found: dict[str, int] = {}
    for path in sorted(RUNNING.glob("*.pid")) if RUNNING.is_dir() else []:
        try:
            found[path.stem] = int(path.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            continue
    return found


def start(name: str, argv: list[str]) -> int:
    """One process, detached, with its own log, and its pid written down."""
    RUNNING.mkdir(parents=True, exist_ok=True)
    out = (RUNNING / f"{name}.out").open("a", encoding="utf-8")
    process = subprocess.Popen(argv, cwd=ROOT, stdout=out, stderr=subprocess.STDOUT,
                               start_new_session=True)
    (RUNNING / f"{name}.pid").write_text(f"{process.pid}\n", encoding="utf-8")
    return process.pid


#: Held while one process starts the harbourmaster again, so two captains that both find it gone start one
#: between them. A file made with `O_EXCL` rather than `flock`, because `flock` is not on Windows and this
#: file already pays for one platform's quirk in `alive`.
RESTARTING = RUNNING / "harbourmaster.restarting"
#: Seconds after which a `RESTARTING` nobody removed is a process that died holding it, not one starting.
#: Starting a process and writing its pid takes well under a second, so this is generous by two orders.
RESTART_STALE = 60.0


def relight_harbourmaster() -> int | None:
    """Start the harbourmaster again where its pid file names a process that has gone. Its new pid, or None.

    Called by every captain at the top of its turn and while it waits on a merge answer, because nothing
    else would: `relight` deliberately never starts one, and only the harbourmaster fills free berths, so
    a harbourmaster that died while any captain lived stayed dead — and the captain waiting on its answer
    sat out the wait bound and parked a slice that had passed its gate, for a person to restart a process.

    **Only a pid file naming a dead process is a harbourmaster to restart.** No pid file is a harbourmaster
    a person started by hand, or none ever started, and neither is this file's to answer: starting one
    beside a hand-started harbourmaster would be two writers to one machine's harbour log, the one rule the
    whole design rests on. The pid is read again under `RESTARTING`, so the second of two captains that
    both saw it gone finds the first one's harbourmaster alive and starts nothing.
    """
    def recorded_pid() -> int | None:
        try:
            return int((RUNNING / "harbourmaster.pid").read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            return None

    pid = recorded_pid()
    if pid is None or alive(pid):
        return None
    try:
        held = os.open(RESTARTING, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        # Another captain is starting it. Unless it died doing so, in which case the next turn tries again.
        try:
            if time.time() - RESTARTING.stat().st_mtime > RESTART_STALE:
                RESTARTING.unlink(missing_ok=True)
        except OSError:
            pass
        return None
    except OSError:
        return None
    try:
        pid = recorded_pid()
        if pid is not None and alive(pid):
            return None
        return start("harbourmaster", [sys.executable, str(HERE / "harbourmaster.py")])
    finally:
        os.close(held)
        RESTARTING.unlink(missing_ok=True)


def cast_off(limit: int | None) -> int:
    """Start the harbourmaster and up to `limit` captains. Returns how many processes were started."""
    standing = {name: pid for name, pid in recorded().items() if alive(pid)}
    started = 0
    if "harbourmaster" not in standing:
        pid = start("harbourmaster", [sys.executable, str(HERE / "harbourmaster.py")])
        print(f"harbourmaster started, pid {pid}")
        started += 1
    else:
        print(f"harbourmaster already running, pid {standing['harbourmaster']}")
    return started + relight(limit, say=True)


def relight(limit: int | None, say: bool = False, wanted: list[str] | None = None) -> int:
    """Light the captains that should be lit and are not, up to `limit`. Returns how many were started.

    **Captains only, never the harbourmaster** — which is what separates this from `cast_off`, and the
    reason it exists rather than the harbourmaster calling that: this is called from inside the
    harbourmaster once a pass, and a harbourmaster that started a second harbourmaster would be the
    one-writer rule broken in the file the whole design promises cannot conflict. It has no pid file of its
    own when a person started it by hand, so "already running" is not a question this can answer.

    Once a pass is what makes a fairway priority take effect on a run that is going — slice 18.2. A captain
    that has dropped below the lit line writes `yielded` at its next slice boundary and exits; the berth is
    then free and nothing else would ever fill it, so moving a stream up would stop a run rather than
    reorder it. Idempotent by construction: a captain already running is left alone, and `fairways()` is
    re-read every time, so the order it lights in is the order as it stands now and not as it was at
    cast-off.

    **A parked fairway is not lit.** Its captain would read the park, say so and exit, and the berth it left
    would be lit again on the next pass: three parked streams were relit every fifteen seconds for three
    and a half hours, each turn a process and a line in its log saying what the line before it said. A park
    is a person's to clear, and the pass after it is cleared lights the captain.

    `wanted` is the harbourmaster's plan: the fairways given a session this pass, which is every fairway
    with work before any is given a second (`abreast.py`). Given, only those are lit — a fairway with
    nothing ready is not lit to say so and exit — and in the priority order all the same. None is every
    fairway, as before there was a plan.
    """
    standing = {name: pid for name, pid in recorded().items() if alive(pid)}
    started = 0
    lit = len([name for name in standing if name != "harbourmaster"])
    for fairway in fairways():
        if wanted is not None and fairway not in wanted:
            continue
        name = f"captain-{fairway}"
        if name in standing:
            if say:
                print(f"{fairway}: captain already running, pid {standing[name]}")
            continue
        why = parked(fairway)
        if why:
            if say:
                lifting = paused_until(fairway)
                print(f"{fairway}: paused until {lifting}, so not lit — {why}" if lifting
                      else f"{fairway}: parked, so not lit — {why}")
            continue
        if limit is not None and lit >= limit:
            if say:
                print(f"{fairway}: waiting for a berth — the telegraph lights {limit} at once")
            continue
        pid = start(name, [sys.executable, str(HERE / "captain.py"), fairway])
        if say:
            print(f"{fairway}: captain started, pid {pid}")
        started, lit = started + 1, lit + 1
    return started


def parked(fairway: str) -> str:
    """Why that fairway is parked, from the latest park no `cleared` receipt answers. `""` where none is open.

    A log that cannot be read is not a park: lighting the captain is what gets that said, by the one process
    whose job is to read the log.
    """
    parks = open_fairway_parks(fairway)
    # A park naming one slice holds that slice, not the stream: its siblings are still work to light for.
    return (str(parks[-1].fields.get("why", "")) or "parked") if parks else ""


def open_fairway_parks(fairway: str) -> list[logs.Entry]:
    """The parks holding this whole fairway that no receipt has answered, oldest first. Empty where the log
    cannot be read: that is not a park, and lighting the captain is what gets it said."""
    where = deck_of(fairway)
    if where is None:
        return []
    try:
        deck = logs.fold(where.read_text(encoding="utf-8").splitlines())
        return logs.fairway_parks(logs.open_parks(deck, logs.harbour_fold(ROOT), fairway))
    except (logs.Unreadable, OSError, UnicodeDecodeError):
        return []


def paused_until(fairway: str) -> str:
    """When this fairway's pause lifts, as a clock on this machine, or `""` where it is parked on a person
    or not parked at all. Paused is every open park lifting by itself — a `limit`, or an `until` ahead."""
    parks = open_fairway_parks(fairway)
    lifting = logs.paused(parks) if parks else []
    if not parks or len(lifting) != len(parks):
        return ""
    latest = max(str(e.fields.get("until") or "") for e in lifting)
    if not latest:
        return "the harness says"
    try:
        when = datetime.strptime(latest, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError:
        return latest
    return when.astimezone().strftime("%H:%M")


def stop_all() -> int:
    """Ask every process this started to stop, and say which were already gone."""
    stopped = 0
    for name, pid in recorded().items():
        if not alive(pid):
            print(f"{name}: not running (pid {pid} is gone)")
            (RUNNING / f"{name}.pid").unlink(missing_ok=True)
            continue
        os.kill(pid, signal.SIGTERM)
        # True because the captain makes it so: its SIGTERM handler ends the running stage, writes
        # `stopped` naming the slice, and gives the claim back once that line has travelled.
        print(f"{name}: asked to stop (pid {pid}). A captain ends the stage it is on, writes `stopped` "
              f"naming its slice, and carries that slice on when it is lit again")
        stopped += 1
    return stopped


def listing() -> list[str]:
    """What is running, and what was started and is not. `slipwai fleet` is where the work is shown; this
    is only about the processes, which is a different question and one `fleet` deliberately does not ask."""
    found = recorded()
    if not found:
        return ["nothing has been started here"]
    return [f"  {name:<22} pid {pid:<8} {'running' if alive(pid) else 'gone'}"
            for name, pid in sorted(found.items())]


def logs_root() -> Path:
    return ROOT / logs.LOGS


def deck_files() -> list[Path]:
    """Every log a stream writes, plus every machine's harbour log. Sorted, so two runs print alike."""
    return logs.deck_logs(ROOT) + logs.harbour_logs(ROOT)


def harbour_log(path: Path) -> bool:
    return path.parent.name == Path(logs.HARBOUR_DIR).name or path.name == Path(logs.HARBOUR).name


def said(path: Path, entry: dict) -> str:
    """One line, in the words a person reads rather than the JSON a captain writes."""
    stream = str(entry.get("fairway") or (f"harbour/{path.stem}" if harbour_log(path) else path.stem))
    kind = str(entry.get("kind", "?"))
    rest = " ".join(f"{word}={value}" for word, value in entry.items()
                    if word not in ("v", "t", "kind", "fairway"))
    return f"{str(entry.get('t', ''))[11:19]}  {stream:<14} {kind:<13} {rest}".rstrip()


def watch(minutes: float) -> int:
    """Print every stream's lines as they are written, and return after `minutes`.

    What is watched is the logs, because the logs are the state: a captain that has died and one that is
    thinking hard look identical from the outside, and only the log tells them apart. The runner's `watch`
    read the runner's own output, so it could only ever see one machine's work — and when the runner died at
    iteration two it went on printing nothing, which is the same thing it printed when all was well.

    Nothing is held between calls: it starts at the end of every log and prints what arrives after. A person
    who wants what already happened reads `slipwai fleet <stream>`, which says the whole of one.
    """
    seen = {path: path.stat().st_size for path in deck_files() if path.is_file()}
    until = time.monotonic() + minutes * 60
    print(f"watching {len(seen) or 'no'} log(s) for {minutes:g} minute(s). Ctrl-C to stop; nothing is "
          f"interrupted by leaving.")
    while time.monotonic() < until:
        for path in deck_files():
            if not path.is_file():
                continue
            at = seen.get(path, 0)
            if path.stat().st_size <= at:
                continue
            with path.open("r", encoding="utf-8", errors="replace") as handle:
                handle.seek(at)
                for line in handle:
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                    except ValueError:
                        continue
                    if isinstance(entry, dict):
                        print(said(path, entry), flush=True)
                seen[path] = handle.tell()
        time.sleep(1.0)
    print("watch over. Nothing stopped — `slipwai fleet` is what is going on now.")
    return 0


def deck_of(stream: str) -> Path | None:
    """The one log that stream writes, or None where it has not written yet."""
    return next((path for path in logs_root().glob(f"*/{stream}.jsonl")), None)


def tell(streams: list[str], words: list[str]) -> int:
    """Write one `told` line into each named stream's deck log, which its captain reads at its next boundary.

    Into the deck log and nowhere else, which is the rule the bridge already keeps: the log is what a captain
    reads, so a message anywhere else is a message nothing is watching. Not the harbour log — that has one
    writer, the harbourmaster, and one shared file with two writers is how a log stops being evidence.

    The message is the words given, or standard input where there are none, so a command file hands it over
    in a heredoc and no quote inside it reaches the shell.

    Nothing has to be running. A `told` is a line in a log, not a signal to a process: the runner's version
    pushed onto a queue only its own iteration drained, so a message queued while nothing was running waited
    on a run that might never come. This one is read by whatever is lit next, on whichever machine.
    """
    message = " ".join(words).strip() if words else ("" if sys.stdin.isatty() else sys.stdin.read().strip())
    if not message:
        raise SystemExit("tell takes the message as its words, or on standard input")
    # A session a captain dispatched runs this too, to say something to a person; only a person's line may
    # answer a park, so whose it is travels with it. The captain sets `SLIPWAI_FAIRWAY` on every session.
    by = "session" if os.environ.get("SLIPWAI_FAIRWAY") else "person"
    written: list[str] = []
    for stream in streams:
        where = deck_of(stream)
        if where is None:
            raise SystemExit(f"`{stream}` has no deck log here, so there is nowhere for this to go. A stream "
                             f"gets a log when its captain writes its first line.")
        with where.open("a", encoding="utf-8") as handle:
            handle.write(logs.entry("told", fairway=stream, message=message, by=by).line())
        written.append(stream)
    print(f"told {', '.join(written)}. Each reads it at its next boundary and answers with a `read` line; "
          f"`slipwai bridge` is where the answer comes back.")
    return 0


def telling(named: str | None, everyone: bool) -> list[str]:
    """Which streams a `tell` goes to, or a refusal naming the ones there are.

    A message with no stream is refused rather than guessed at: the runner had one inbox because it was one
    run, and the thing that replaced it is several captains who are each somewhere different in their work.
    `--everyone` is the deliberate broadcast, and it is spelled out because telling four streams the same
    thing is rarely what somebody means and always what they get by accident.
    """
    known = fairways()
    if everyone:
        return [name for name in known if deck_of(name) is not None] or known
    if not named:
        raise SystemExit(f"tell takes the stream first, then the message. There are {len(known)}: "
                         f"{', '.join(known) or 'none charted'}. `--everyone` tells all of them.")
    if named not in known:
        raise SystemExit(f"`{named}` is not a stream the chart names. There are {len(known)}: "
                         f"{', '.join(known) or 'none charted'}.")
    return [named]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="fleet", description="Start the harbourmaster and a captain per fairway, and exit",
        epilog="This is not a runner. The state of the run is in the logs, the captains read them, and this "
               "starts processes and gets out of the way — so nothing here can be the thing that died.")
    parser.add_argument("verb", nargs="?", choices=("start", "relight", "stop", "list", "watch", "tell"),
                        default="start",
                        help="`relight` lights whatever should be lit now and starts no harbourmaster — "
                             "what the harbourmaster itself calls once a pass, so a fairway moved up while "
                             "a run is going gets the berth the captain below it gave up")
    parser.add_argument("words", nargs="*", help="for `tell`: the stream, then the message")
    parser.add_argument("--boilers", type=int, default=None,
                        help="how many captains may run at once (default: the telegraph's)")
    parser.add_argument("--minutes", type=float, default=1.5,
                        help="for `watch`: how long to sit before returning (default: 1.5)")
    parser.add_argument("--everyone", action="store_true",
                        help="for `tell`: the message goes to the harbour log, which every captain reads")
    parsed = parser.parse_args(argv)
    if parsed.verb == "stop":
        stop_all()
        return 0
    if parsed.verb == "list":
        print("\n".join(listing()))
        return 0
    if parsed.verb == "watch":
        return watch(parsed.minutes)
    if parsed.verb == "tell":
        words = list(parsed.words)
        named = words.pop(0) if words and not parsed.everyone else None
        return tell(telling(named, parsed.everyone), words)
    held = config()
    limit = parsed.boilers if parsed.boilers is not None else held.get("boilers")
    if isinstance(limit, int) and limit <= 0:
        print(f"the telegraph is at {held.get('position', 'stop')}, which lights no captains. "
              f"`slipwai telegraph half-ahead` casts off again")
        return 0
    bound = limit if isinstance(limit, int) else None
    if parsed.verb == "relight":
        started = relight(bound, say=True)
        print(f"relight: {started} captain(s) started" if started else "relight: nothing to light")
        return 0
    cast_off(bound)
    print("`slipwai fleet` shows what they are doing; `slipwai bridge` is the page you answer from")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
