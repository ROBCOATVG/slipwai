"""`/cruise-tell`: a person's word to a run under way. Queued in `.specify/cruise-inbox.jsonl`, carried by the
iteration the runner starts next as `told: …` in its argument — never pushed into the one in flight, unless
`--now` ends it for the message — and asked for between stages by the iteration itself (`told`). The runner is
run for real against the fake harness, which stands in for the person: it queues, interrupts and answers a park
from inside its own iterations, so nothing here depends on a timer racing the loop.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

from support import FactoryTestCase
from test_cruise_runner import cruise, enable, fake_harness, logged

from slipwai.project.cruise import LOG
from slipwai.project.cruise_record import INBOX, TOLD


class CruiseTellTest(FactoryTestCase):
    def test_the_command_says_a_message_rides_the_next_iteration_and_the_seat_queues_one(self) -> None:
        """`commands/cruise.md` names the third argument beside the kick-off and `unblock:`, has the iteration ask
        between stages, and has the watch seat queue what a person types for the run rather than act on it."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "told", "standard", "python")
            command = (repo / "commands/cruise.md").read_text()
            refuse = command.split("## Before anything: refuse, or start")[1].split("## Run the ladder")[0]
            self.assertIn("A third is a person's: `told: <message>`\nis what somebody queued for the run through "
                          "`/cruise-tell` (`python3 scripts/agents/cruise.py tell`)", refuse)
            self.assertIn("never the one in flight, unless they ended it for the message", refuse)
            self.assertIn("A message\nnever changes a setting; say so and point at `/cruise-settings`", refuse)
            self.assertIn("queue it with `python3 scripts/agents/cruise.py tell <<'EOF'` … `EOF` (`/cruise-tell`)",
                          command)
            self.assertIn("At the same boundaries run `python3 scripts/agents/cruise.py told`", command)
            self.assertIn("| told: <a person's message>", command.splitlines()[2])

    def test_a_person_tells_the_run_something_and_it_is_queued_never_pushed(self) -> None:
        """`tell` queues a message; the runner hands it to the iteration it starts next as `told: …` in the
        argument, the route the kick-off takes, and the iteration in flight is left alone. An iteration can ask
        for what was queued since it started (`told`), which takes it so the next is not given it again, and
        whichever read took a message, the iteration's log entry carries it. `--now` is the interrupt: the
        iteration in flight ends for the message, is logged as interrupted, is not counted as no progress, and
        the next starts at once with the message. A parked run resumes on a message within the second."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "tell", "standard", "python")
            enable(repo, stuck_after="2")
            idle = cruise(repo, "tell", "use", "the", "PRD", "in", "docs/prd.md")
            self.assertEqual(idle.returncode, 0, idle.stderr)
            self.assertIn("cruise: queued; no runner is running here — the first iteration of the next run carries "
                          "it (`/cruise` starts one)", idle.stdout)
            self.assertEqual([json.loads(line)["text"] for line in (repo / INBOX).read_text().splitlines()],
                             ["use the PRD in docs/prd.md"])
            self.assertIn("cruise: 1 message(s) queued for the next iteration (.specify/cruise-inbox.jsonl):\n"
                          "cruise:   use the PRD in docs/prd.md", cruise(repo, "status").stdout)
            empty = cruise(repo, "tell")
            self.assertEqual(empty.returncode, 1)
            self.assertIn("tell takes the message as its words, or on standard input", empty.stderr)
            # The fake harness stands in for the person: iteration 1 queues one for the next, iteration 2 queues one
            # and asks for it between its stages, iteration 3 queues nothing and is given nothing.
            env = fake_harness(Path(directory), """mkdir -p specs && touch "specs/progress-$n"
case "$n" in
  1) python3 scripts/agents/cruise.py tell "take the payments feature next"; echo "cruise: continue";;
  2) printf 'skip the demo on %s\\n' "slice 3" | python3 scripts/agents/cruise.py tell
     python3 scripts/agents/cruise.py told; python3 scripts/agents/cruise.py told; echo "cruise: continue";;
  *) echo "cruise: done";;
esac""")
            run = cruise(repo, "run", "--feature", "001-campaign", "kick", "off", env=env)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            prompts = (Path(directory) / "prompts").read_text().splitlines()
            self.assertEqual(prompts, ["/cruise 001-campaign kick off told: use the PRD in docs/prd.md",
                                       "/cruise 001-campaign told: take the payments feature next",
                                       "/cruise 001-campaign"])
            self.assertIn("cruise: queued for the next iteration; the one in flight ends first", run.stdout)
            self.assertIn("cruise: iteration 2 carries 1 message(s) from a person", run.stdout)
            self.assertIn("cruise: 1 message(s) from a person since this iteration started; act on each before the "
                          "next stage, and write down what must outlive this iteration\n", run.stdout)
            self.assertIn("  cruise: told: skip the demo on slice 3\n", run.stdout)
            self.assertEqual(run.stdout.count("cruise: told: skip the demo on slice 3"), 1, "taken once")
            self.assertEqual([entry.get("told") for entry in logged(repo)],
                             [["use the PRD in docs/prd.md"],
                              ["take the payments feature next", "skip the demo on slice 3"], None])
            self.assertEqual([entry.get("attempt") for entry in logged(repo)], ["kick-off", None, None])
            self.assertFalse((repo / INBOX).exists())
            self.assertFalse((repo / TOLD).exists())
            # `--now`: the iteration in flight is ended for the message, and the next starts with it at once.
            (repo / LOG).unlink()
            (Path(directory) / "calls").unlink()
            (Path(directory) / "prompts").unlink()
            env = fake_harness(Path(directory), """mkdir -p specs
case "$n" in
  1) python3 scripts/agents/cruise.py tell --now "stop: the demo is against the wrong build"; sleep 30
     echo "cruise: continue";;
  *) echo "cruise: done";;
esac""")
            began = time.monotonic()
            now = cruise(repo, "run", "--no-park", env=env)
            self.assertEqual(now.returncode, 0, now.stdout + now.stderr)
            self.assertLess(time.monotonic() - began, 20, "the iteration was not ended for the message")
            # What `tell --now` printed is lost with the group it ran in; the runner's own lines are the evidence.
            self.assertRegex(now.stdout, r"cruise: iteration 1 ended — interrupted: a person's message \(")
            self.assertNotIn("left a process running", now.stdout)
            self.assertEqual((Path(directory) / "prompts").read_text().splitlines(),
                             ["/cruise", "/cruise told: stop: the demo is against the wrong build"])
            first, second = logged(repo)
            self.assertEqual((first["last_line"], first.get("interrupted"), first.get("told")),
                             ("interrupted: a person's message", True, None))
            self.assertEqual((second["last_line"], second.get("told")),
                             ("cruise: done", ["stop: the demo is against the wrong build"]))
            # What the interrupted iteration had been given is not spent: it goes to the next, ahead of the message
            # that ended it — and so does what a run that died under an iteration had given it.
            (repo / LOG).unlink()
            (Path(directory) / "calls").unlink()
            (Path(directory) / "prompts").unlink()
            cruise(repo, "tell", "first")
            env = fake_harness(Path(directory), """mkdir -p specs
case "$n" in
  1) python3 scripts/agents/cruise.py tell --now "second"; sleep 30; echo "cruise: continue";;
  *) echo "cruise: done";;
esac""")
            again = cruise(repo, "run", "--no-park", env=env)
            self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
            self.assertEqual((Path(directory) / "prompts").read_text().splitlines(),
                             ["/cruise told: first", "/cruise told: first told: second"])
            self.assertEqual([entry.get("told") for entry in logged(repo)], [["first"], ["first", "second"]])
            (repo / TOLD).write_text(json.dumps({"at": "then", "text": "unspent", "now": False}) + "\n")
            (repo / LOG).unlink()
            (Path(directory) / "calls").unlink()
            (Path(directory) / "prompts").unlink()
            unspent = cruise(repo, "run", "--no-park", env=fake_harness(Path(directory), 'echo "cruise: done"'))
            self.assertEqual(unspent.returncode, 0, unspent.stdout + unspent.stderr)
            self.assertEqual((Path(directory) / "prompts").read_text().splitlines(), ["/cruise told: unspent"])
            # An interrupted iteration changed nothing, and the one after it changed nothing either: two identical
            # fingerprints, and `stuck_after` is 2 — but an interruption is a person's doing, not the run's.
            self.assertNotIn("no progress", now.stdout)
            # A parked run resumes with a message, within the second, and the message resuming it is what the
            # next iteration is given.
            (repo / LOG).unlink()
            (Path(directory) / "calls").unlink()
            (Path(directory) / "prompts").unlink()
            env = fake_harness(Path(directory), """mkdir -p specs
if [ "$n" -eq 1 ]; then echo "cruise: parked: which region the tenant lives in"; else echo "cruise: done"; fi""")
            cruise(repo, "--set", "poll_minutes=10")
            runner = subprocess.Popen(["python3", "scripts/agents/cruise.py", "run"], cwd=repo, text=True,
                                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                      env={**os.environ, **env, "CRUISE_POLL_SECONDS": "600"})
            assert runner.stdout is not None
            seen: list[str] = []
            for line in runner.stdout:
                seen.append(line)
                if line.startswith("cruise: waiting;"):
                    break
            self.assertIn("a message (`python3 scripts/agents/cruise.py tell …`) resumes it", seen[-1])
            told = cruise(repo, "tell", "eu-west-1")
            self.assertEqual(told.returncode, 0, told.stderr)
            self.assertIn("cruise: queued; the run parked after iteration 1 and resumes with it within the second",
                          told.stdout)
            rest = runner.stdout.read()
            self.assertEqual(runner.wait(timeout=10), 0, rest)
            self.assertIn("cruise: a person's message; resuming", rest)
            self.assertIn("cruise: iteration 2 carries 1 message(s) from a person", rest)
            self.assertEqual(logged(repo)[-1].get("told"), ["eu-west-1"])
            self.assertEqual((Path(directory) / "prompts").read_text().splitlines()[-1], "/cruise told: eu-west-1")
