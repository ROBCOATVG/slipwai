#!/usr/bin/env python3
"""Put recorded moments to the captain agent and score the orders it gives. An eval, not a test.

A test says whether code does what it must, and gates a merge. This says how often an agent's judgement
matches a person's on moments that really happened, and gates nothing: it is run on demand, or nightly,
and its score is advice (decision 22). `docs/captain-evals.md` says how to add a case and sign one off.

    python3 scripts/evals.py run [--decision D] [--runs N] [--bound S] [--project P | --captain CMD]
    python3 scripts/evals.py rescore evals/captain/runs/<stamp>
    python3 scripts/evals.py check

`run` lays each case out as a throwaway project under a temporary directory — never inside a real project
— writes the event, puts it to the captain under test `--runs` times, keeps every order it wrote, and
prints the report per decision, writing it beside the orders under `evals/captain/runs/<stamp>/`.
`rescore` judges a saved run again against the labels as they are now, calling no agent. `check` reads
every case and says what is wrong with any of them.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import eval_cases
import eval_score
from eval_captains import CannotRun, Captain, named

RUNS = eval_cases.ROOT / "evals/captain/runs"
BRIEF = eval_cases.TOOLKIT / "agents/drive-captain.md"
#: How long after the bound an order file may be dated and still count: a file's time is the filesystem's,
#: and an order written in the bound's last instant is not late.
LATE = 1.0


def run_once(case: dict[str, Any], captain: Captain, bound: float, keep: Path,
             integration: Path | None, brief: Path) -> dict[str, Any]:
    """One run of one case: lay it out, wake the captain, keep what it ordered. The run's record."""
    # A parent of its own: a harness row may name the project's parent as a second working directory, and
    # that must not be a folder other runs, or anything else, share.
    with tempfile.TemporaryDirectory(prefix="slipwai-eval-") as scratch:
        project = Path(scratch) / "project"
        project.mkdir()
        event = eval_cases.lay_out(case, project, integration, brief)
        orders = event.parents[2] / "orders" / event.parent.name
        started = time.monotonic()
        wall = time.time()
        ran = captain(project, event, bound)
        seconds = time.monotonic() - started
        (keep / "orders").mkdir(parents=True, exist_ok=True)
        late = []
        for path in eval_score.order_files(orders):
            # An order the program would have met after its bound is one the fixed rule had already
            # overtaken; it is kept for a person to read and not scored.
            if path.stat().st_mtime > wall + bound + LATE:
                late.append(path.name)
                shutil.copy(path, keep / f"late-{path.name}")
                continue
            shutil.copy(path, keep / "orders" / path.name)
    record = {"case": case["id"], "decision": case["event"]["kind"], "seconds": round(seconds, 3),
              "timed_out": ran.timed_out, "exit": ran.exit, "tokens": ran.tokens, "late": late,
              "may": eval_cases.event_of(case)["may"]}
    (keep / "run.json").write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
    return record


def judged_row(case: dict[str, Any], runs: list[tuple[dict[str, Any], Path]]) -> dict[str, Any]:
    """A case's runs judged against its label as it is now: the report's row for it."""
    known, free = eval_cases.context_of(case)
    judged = [eval_score.judge(case["label"], record["may"], eval_score.order_files(keep / "orders"), known, free)
              for record, keep in runs]
    event = eval_cases.event_of(case)
    fixed = {verb: eval_score.fixed(case["label"], event["may"], verb, str(event.get("slice") or ""), known, free)
             for verb in event["may"]}
    return {"case": case["id"], "decision": case["event"]["kind"],
            "signed_off": case["label"].get("signed_off", ""),
            "outcomes": [one.outcome for one in judged], "agreement": eval_score.agreement(judged),
            "seconds": [record["seconds"] for record, _ in runs], "tokens": [record["tokens"] for record, _ in runs],
            "answers": [one.answer for one in judged], "texts": [one.texts for one in judged],
            "faults": [one.malformed + one.refused for one in judged], "fixed": fixed}


def percent(part: int, whole: int) -> str:
    return f"{100 * part / whole:.0f}%" if whole else "-"


def baseline(words: str, rows: list[dict[str, Any]]) -> str:
    """The best a captain that always gave the same order would do on these cases, and what silence does."""
    verbs = sorted({verb for row in rows for verb in row["fixed"]})
    right = {verb: sum(1 for row in rows if row["fixed"].get(verb) == "right") for verb in verbs}
    best = max(verbs, key=lambda verb: right[verb], default="none")
    return (f"  {words}: always `{best}` is right on {right.get(best, 0)} of {len(rows)}; always silent is right "
            f"on none, every run a fallback")


def report(rows: list[dict[str, Any]], header: str) -> str:
    """The report a person reads: a line per decision, then a line per case, then what the score is."""
    decisions = eval_score.summarise(rows)
    lines = [header, "", f"{'decision':<42} {'cases':>5} {'runs':>5} {'right':>6} {'wrong':>6} {'unjudged':>8} "
                         f"{'fallback':>8} {'agree':>6} {'s/run':>6}  tokens"]
    for decision, words in eval_cases.DECISIONS.items():
        held = decisions.get(decision)
        if not held:
            continue
        runs = held["runs"]
        tokens = f"{held['tokens']} from {held['costed']} of {runs} runs" if held["costed"] else "unknown"
        lines.append(f"{words:<42} {held['cases']:>5} {runs:>5} {percent(held['right'], runs):>6} "
                     f"{percent(held['wrong'], runs):>6} {percent(held['unjudged'], runs):>8} "
                     f"{percent(held['fallback'], runs):>8} {held['agreement'] * 100:>5.0f}% "
                     f"{held['seconds'] / runs if runs else 0:>6.1f}  {tokens}")
    lines += ["", "Read against what a captain with no judgement scores on the same cases:"]
    lines += [baseline(words, [row for row in rows if row["decision"] == decision])
              for decision, words in eval_cases.DECISIONS.items() if decisions.get(decision)]
    lines += ["", "Each case (outcome per run; the notes and reasons it wrote are in report.json):"]
    for row in rows:
        counted = ", ".join(f"{row['outcomes'].count(o)} {o}" for o in eval_score.OUTCOMES if o in row["outcomes"])
        signed = f"signed off by {row['signed_off']}" if row["signed_off"] else "label unsigned"
        lines.append(f"  {row['case']}: {counted}; agreed {row['agreement'] * 100:.0f}%; {signed}")
    confirmed = sum(1 for row in rows if row["signed_off"])
    lines += ["", f"This score is advice, not a gate. {confirmed} of {len(rows)} labels are signed off by a person; "
                  f"an unsigned label is a draft from what happened next, and a score against it is a draft too. "
                  f"Fallback is a run that gave no order the program could use, where today's fixed rule applies."]
    return "\n".join(lines) + "\n"


def write_report(rows: list[dict[str, Any]], header: str, where: Path, name: str = "report") -> str:
    text = report(rows, header)
    (where / f"{name}.txt").write_text(text, encoding="utf-8")
    held = {"header": header, "cases": rows, "decisions": eval_score.summarise(rows)}
    (where / f"{name}.json").write_text(json.dumps(held, indent=1) + "\n", encoding="utf-8")
    return text


def chosen_cases(cases: Path, decision: str | None) -> list[dict[str, Any]]:
    found = []
    for path in eval_cases.every(cases, decision):
        case = eval_cases.load(path)
        faults = eval_cases.faults(case, path.parent.name)
        if faults:
            raise SystemExit(f"evals: {eval_cases.case_id(path)} cannot be run: {'; '.join(faults)}")
        found.append(case)
    return found


def run(cases: list[dict[str, Any]], captain: Captain, said: str, runs: int, bound: float, out: Path,
        integration: Path | None = None, brief: Path = BRIEF) -> str:
    """Every case `runs` times; the report, which is also written under `out`."""
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for case in cases:
        done = []
        for number in range(1, runs + 1):
            keep = out / case["id"] / str(number)
            done.append((run_once(case, captain, bound, keep, integration, brief), keep))
        rows.append(judged_row(case, done))
    header = (f"captain evals at {datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')}: {len(cases)} case(s), "
              f"{runs} run(s) a case, a bound of {bound:g}s, the captain under test {said}")
    about = {"header": header, "runs": runs, "bound": bound}
    (out / "about.json").write_text(json.dumps(about) + "\n", encoding="utf-8")
    return write_report(rows, header, out)


def rescore(out: Path, cases: Path = eval_cases.CASES) -> str:
    """A saved run judged again against the labels as they are now. No agent is called."""
    about = json.loads((out / "about.json").read_text(encoding="utf-8"))
    rows = []
    for path in eval_cases.every(cases):
        case = eval_cases.load(path)
        home = out / case["id"]
        saved = sorted((one for one in home.glob("*") if (one / "run.json").is_file()),
                       key=lambda one: int(one.name) if one.name.isdigit() else 0) if home.is_dir() else []
        if saved:
            rows.append(judged_row(case, [(json.loads((keep / "run.json").read_text(encoding="utf-8")), keep)
                                          for keep in saved]))
    header = f"{about['header']}; scored again at {datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')}"
    return write_report(rows, header, out, "rescored")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="evals.py", description=__doc__.split("\n\n")[0])
    verbs = parser.add_subparsers(dest="verb", required=True)
    go = verbs.add_parser("run", help="put the cases to the captain under test")
    go.add_argument("--decision", choices=sorted(eval_cases.DECISIONS))
    go.add_argument("--runs", type=int, default=3, help="runs a case (default 3)")
    go.add_argument("--bound", type=float, default=60.0, help="seconds the captain has (default 60)")
    go.add_argument("--project", type=Path, help="a project whose initialised harness is the one used; only "
                                                 "its .specify/integration.json is read")
    go.add_argument("--captain", help="a command that is the captain under test, run with the event's path")
    go.add_argument("--brief", type=Path, default=BRIEF, help="the captain's brief (default the toolkit's)")
    go.add_argument("--model", help="the model the harness is asked for, where its row can name one")
    again = verbs.add_parser("rescore", help="judge a saved run again; no agent is called")
    again.add_argument("run", type=Path)
    verbs.add_parser("check", help="read every case and say what is wrong with any")
    args = parser.parse_args(argv)
    if args.verb == "check":
        problems = [f"{eval_cases.case_id(path)}: {fault}" for path in eval_cases.every()
                    for fault in eval_cases.faults(eval_cases.load(path), path.parent.name)]
        print("\n".join(problems) or f"evals: {len(eval_cases.every())} case(s), every one readable")
        return 1 if problems else 0
    if args.verb == "rescore":
        print(rescore(args.run), end="")
        return 0
    integration = args.project / ".specify/integration.json" if args.project else None
    if not args.captain and (integration is None or not integration.is_file()):
        print("evals: name a project whose harness is initialised (--project <path>) or a captain command "
              "(--captain <command>)", file=sys.stderr)
        return 2
    captain, said = named(args.captain, f"agents/{args.brief.name}", args.model)
    out = RUNS / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    try:
        print(run(chosen_cases(eval_cases.CASES, args.decision), captain, said, args.runs, args.bound, out,
                  integration, args.brief), end="")
    except CannotRun as refusal:
        print(f"evals: {refusal}", file=sys.stderr)
        return 2
    print(f"evals: the report and every order are under {out.relative_to(eval_cases.ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
