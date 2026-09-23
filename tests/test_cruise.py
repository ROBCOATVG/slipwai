"""`/cruise`: `/drive` with nobody at the wheel — the agent as driver and product owner until the specs are satisfied.

What this gates is the spine the rest of cruise hangs from: the settings file a project has to opt into, the command
that runs `commands/drive.md` as written and says at every one of its stops what happens instead of a person, the
two delegates that answer those stops, the rows the models table and the benchmark gain for them, and the pages
that name them. Every phrase asserted here is one a person or a delegate acts on; the constants come from the
source module, so the text and the test cannot drift apart.
"""
from __future__ import annotations

import json
import subprocess
import tempfile

from support import FactoryTestCase
from test_benchmark import bench, clean, commit, installed, record
from test_drive_adoption import adopted, wrapped

from slipwai.project.cruise import (
    CONFIG,
    DECISION_ENTRY,
    LAST_LINES,
    LOG,
    REPORT,
    SCRIPT,
    SETTINGS,
    STOP_FILE,
    UNREAD,
)
from slipwai.project.cruise_agents import BOSUN, BROWSER, DECISIONS, DEMO_LOG, HAND, OWNER_BRIEF, SKIPPER
from slipwai.project.cruise_record import DEMO_ENTRY
from slipwai.project.cruise_unblock import CATASTROPHIC
from slipwai.project.stage_models import STAGES, switchable_harnesses

PROFILES = ("event-modelling", "standard")
# The rows that only exist where there is a production target, an adopted repository, or the event profile.
RELEASE_ROWS = ("| Release constraint |",
                '| "A release they want now" — no flag, or a flag already on, before the push |')
ADOPTED_ROWS = ("| Ground: a convergence row still `unrecorded` on an axis the slice touches |",
                "| The change-strategy ADR at `Accepted` |",
                "| Quick wins and method slices offered from the programme |")


def frontmatter(text: str) -> dict[str, str]:
    return dict(line.split(": ", 1) for line in text.split("\n---\n")[0].splitlines()[1:] if ": " in line)


def fenced(text: str) -> list[str]:
    """Every fenced block's body, so a template is asserted where it is shown rather than anywhere in the prose."""
    return [block.split("\n", 1)[1].rstrip("\n") for block in text.split("```")[1::2]]


class CruiseTest(FactoryTestCase):
    def test_the_settings_file_ships_every_setting_at_its_default_and_disabled(self) -> None:
        """A run nobody asked for is the failure this prevents: the file exists in every project, at the defaults
        the source declares, with `enabled` false, and its comment names the one command that changes it."""
        with tempfile.TemporaryDirectory() as directory:
            for profile in PROFILES:
                repo = self.generate(directory, f"settings-{profile}", profile, "python")
                table = json.loads((repo / CONFIG).read_text())
                self.assertEqual([key for key in table if key != "_comment"], [key for key, *_ in SETTINGS], profile)
                self.assertEqual({key: table[key] for key in table if key != "_comment"},
                                 {key: default for key, _, default, _ in SETTINGS}, profile)
                self.assertIs(table["enabled"], False)
                self.assertIn("/cruise-settings", table["_comment"])
                self.assertIn(SCRIPT, table["_comment"])

    def test_cruise_runs_the_drive_ladder_and_says_what_happens_at_every_stop(self) -> None:
        """A command that paraphrased the ladder would drift from it; one that stopped where `/drive` stops would
        wait for a person who is not there. So it runs `commands/drive.md` as written, refuses the three things it
        cannot start without, and carries one table row per stop — the release rows only under a target, the
        profile's own artifact for the gaps row — plus the two record shapes, verbatim and fenced, and the four
        last lines the outer loop reads."""
        with tempfile.TemporaryDirectory() as directory:
            for profile, target in (("event-modelling", "aws"), ("standard", "none")):
                repo = self.generate(directory, f"cruise-{profile}", profile, "typescript", target=target)
                cruise = (repo / "commands/cruise.md").read_text()
                declared = frontmatter(cruise)
                self.assertTrue(declared["description"].startswith("Run /drive as driver and product owner"))
                self.assertEqual(declared["argument-hint"],
                                 "[--feature <name>] [kick-off: what this run is for, where the brief or PRD is] | "
                                 "unblock: <what the outer loop saw>")
                self.assertIn("a feature named with `--feature` on `run` or `start`\n(`make cruise FEATURE=<name>`) is "
                              "the first word of every iteration's argument and scopes the run", cruise)
                self.assertIn("runs **that ladder — `commands/drive.md`,\nevery rule as written**", cruise)
                self.assertIn("Run `commands/drive.md` from *Enter at the first incomplete stage* to its end", cruise)
                # The refusals: a run has to be asked for, a person can always stop it, and a spec is theirs to bring.
                refuse = cruise.split("## Before anything: refuse, or start")[1].split("## Run the ladder")[0]
                self.assertIn(f"Read `{CONFIG}`. `enabled: false`, or `{STOP_FILE}` present, is a refusal", refuse)
                self.assertIn("No\n`specs/<feature>/spec.md` is a refusal too", refuse)
                # A typed /cruise starts the runner and watches it; only a runner's session is an iteration.
                self.assertIn(f"Then run\n`python3 {SCRIPT} loop`: it says what is reading this session's last line. "
                              "**Where it says nobody is**", refuse)
                self.assertIn(f"run\n`python3 {SCRIPT} start` with everything typed after `/cruise` as its arguments, "
                              "verbatim, and repeat what it\nprinted", refuse)
                self.assertIn("Then take the watch seat (*The watch seat*, below).", refuse)
                self.assertIn("**Where\nit says the outer loop started this session**, this is an iteration: read the "
                              f"owner brief (`{OWNER_BRIEF}`)\nand every standing entry in `{DECISIONS}`", refuse)
                # The kick-off reaches the first iteration only; the watch seat reads, answers, and never drives.
                self.assertIn("**The argument is the kick-off.** What a person typed after `/cruise`", refuse)
                self.assertIn("reaches the first iteration of the run and no other", refuse)
                self.assertIn("(*Blocked: the bosun protocol*, below)", refuse)
                self.assertIn("## Blocked: the bosun protocol", cruise)
                seat = refuse.split("## The watch seat")[1]
                self.assertIn(f"run `python3 {SCRIPT} watch`", seat)
                self.assertIn("**Put every line it printed in your reply, unchanged, in a\nfenced block, before "
                              "anything else** — the harness folds a command's output", seat)
                self.assertIn("run `watch` again\nat once**", seat)
                self.assertIn("run a command in the background and re-invoke this session", seat)
                self.assertIn("where it says parked, ended, or no runner, repeat what it said and end the turn", seat)
                self.assertIn("A watch the\nharness cut short — a tool timeout, with no last line from `watch` — is "
                              "watched again, not asked about. Where\nthe harness can run a command in the background",
                              seat)
                self.assertIn("never a reason to run a stage of the ladder in this session", seat)
                self.assertIn("**A person typing here is talking to you, not stopping the run.**", seat)
                self.assertIn(f"`python3 {SCRIPT}` prints every setting and what it controls", seat)
                self.assertIn("change a setting through `/cruise-settings` where they ask", seat)
                self.assertIn(f"the iteration number from `{LOG}`", refuse)
                self.assertIn(f"`touch {STOP_FILE}`", refuse)
                self.assertIn("pass `driver=cruise` to every `end` this iteration closes", refuse)
                # The table, and the rows that depend on what the project is.
                self.assertIn("| # | Where `/drive` stops | What `/cruise` does there | Recorded in |", cruise)
                self.assertIn("| 1 | The checkout is behind trunk, or the fetch failed |", cruise)
                self.assertIn("| Product specification missing | Refuse to start.", cruise)
                self.assertIn(f"| The demo stop | Delegate to `{HAND}` with exactly what the stop hands a person",
                              cruise)
                self.assertIn(f"`accepted-by: {HAND}` on the register row or status flip | `{DEMO_LOG}`", cruise)
                self.assertIn(f"| The ready set is empty | Not a stop: the completion audit below. Only an audit with "
                              f"nothing left is `done` | `{REPORT}`, decision entries |", cruise)
                self.assertIn("| An input that is genuinely unavailable — a credential, an external system, a "
                              "person's approval | Never invented. Mark the slice blocked, take the next ready slice, "
                              "and hand the blocker to `drive-bosun`", cruise)
                self.assertIn("## Blocked: the bosun protocol", cruise)
                for item in CATASTROPHIC:
                    self.assertIn(f"- {item}", cruise)
                self.assertIn("`unblock: park` turns this off", cruise)
                for row in RELEASE_ROWS:
                    self.assertEqual(row in cruise, target != "none", (profile, row))
                for row in ADOPTED_ROWS:
                    self.assertNotIn(row, cruise, profile)
                gaps_row = ("| Slice gaps: a question at a time over `examples.md` |" if profile == "event-modelling"
                            else "| Slice gaps: a question at a time over the criteria in `spec.md` |")
                self.assertIn(gaps_row, cruise)
                # The two record shapes are shown where they are used, verbatim, as a fenced block each.
                blocks = fenced(cruise)
                self.assertIn(DECISION_ENTRY, blocks)
                self.assertIn(DEMO_ENTRY, blocks)
                self.assertIn(f"one fresh `{SKIPPER}` delegate with the\nquestion", cruise)
                self.assertIn("`decide: skipper-always`, every question goes to the delegate", cruise)
                # The `hand` setting reaches the delegate only through the brief, and the app the ladder leaves up
                # for a person is stopped once the hand has finished with it.
                self.assertIn(f"which is `{CONFIG}`'s `hand` and nothing the delegate can read for itself: `browser` is"
                              f"\n`{BROWSER}` where the slice has a screen, then a browser tool the harness exposes, "
                              "then HTTP, then the CLI;\n`http` starts at HTTP; `cli` at the CLI", cruise)
                self.assertIn("**Then stop what the demo started.**", cruise)
                self.assertIn("`make demo-down` or `make services-down` where the demo used them", cruise)
                # A refusal inside an iteration, and a stop between stages, still end on a last line the loop reads.
                self.assertIn(f"`enabled: false` or the stop file ends on `{LAST_LINES[3]}`", refuse)
                self.assertIn("a missing\nspecification on `cruise: parked: a specification under "
                              "specs/<feature>/spec.md`", refuse)
                self.assertIn(f"commit what is green, and end\non `{LAST_LINES[3]}`", cruise)
                self.assertIn("Open a `skipper`, `hand` or `bosun`\nbenchmark entry", refuse)
                # A fetch that could not run is what the ladder says it is, not a park: a project with no remote
                # would otherwise park on its first iteration and never resume.
                self.assertIn("A fetch that could not run — no remote, or one this environment cannot reach — is what "
                              "the ladder says it is, *could not verify this checkout is current*, said in the "
                              "evidence line, and the run goes on: without a remote the local branch is the claim",
                              cruise)
                self.assertNotIn("a fetch that cannot run parks", cruise)
                self.assertIn("`headless.worktreeFlags`", cruise)
                self.assertIn("Only an audit with nothing left to build ends with `cruise: done`.", cruise)
                # The iteration contract ends with the four lines, listed as the only things the loop reads.
                for last in LAST_LINES:
                    self.assertIn(f"\n- `{last}`\n", cruise)
                self.assertIn("The last line of every iteration is one\nof these, and the outer loop reads nothing "
                              "else:", cruise)
                # The unit before the split exists, the turn rule, the typed-in-a-session rule, and the hook that
                # holds all three — a run ended twice in one session on what the text alone allowed.
                upstream = ("principles, the specification, the event model and the split"
                            if profile == "event-modelling" else "principles, the specification and the split")
                self.assertIn(f"**Before the split exists**, the unit is the upstream stages together —\n{upstream} — "
                              "through to the split's first ready set", cruise)
                self.assertIn("**An iteration ends only on one of those four lines.** Any other message that ends a "
                              "turn is a stop, whatever\nit says it is about to do", cruise)
                self.assertIn(f"`python3 {SCRIPT} loop`", cruise)
                self.assertIn(f"*{UNREAD}*", cruise)
                self.assertIn(f"the project's hook file runs `python3 {SCRIPT} stopping` there — "
                              "`.claude/settings.json` runs\nit as Claude Code's `Stop` hook, `.cursor/hooks.json` as "
                              "Cursor's `stop`, `.gemini/settings.json` as Gemini\nCLI's `AfterAgent`", cruise)
                self.assertIn("and while a runner\nstarted the session", cruise)
                self.assertIn("It\nlets go after three holds against a checkpoint nothing rewrote", cruise)
                # Identifiers are the host's to allocate: the number goes out in the brief, the entry comes back.
                self.assertIn("**the number its entry will carry**. `D<n>` is\nallocated here, before dispatch", cruise)
                self.assertIn("Every other identifier a decision adds to a shared artifact — a requirement, a "
                              "criterion, an\nexample, a state — is allocated the same way: by this session, after the "
                              "delegates return, in dispatch order.", cruise)
                self.assertIn("`slipwai describe-service <name> --purpose`", cruise)
                self.assertIn(f"`python3 {SCRIPT} run` (`make cruise`)", cruise)
                self.assertIn("`driver=cruise` on every benchmark entry, `skipper`, `hand` and `bosun` as stages",
                              cruise)
                self.assertNotIn("stated assumptions and `Proposed` records", cruise,
                                 "only an adopted repository is told that")

    def test_an_adopted_repository_proceeds_on_assumptions_where_a_persons_word_is_the_artifact(self) -> None:
        """Ground's `unrecorded` rows and the strategy ADR's `Accepted` are a person's, and the first adoption to
        run unattended must not learn that by inventing either: the three adopted stops are rows of their own,
        two of them worked on as stated assumptions and `Proposed` records — never `confirmed`, never
        `Accepted` — and the command says up front that a person confirms or overturns them afterwards."""
        files = adopted([wrapped("shop", ".")])
        cruise = files["delivery/commands/cruise.md"]
        for row in ADOPTED_ROWS:
            self.assertIn(row, cruise)
        self.assertIn("| A fact about the world is not a decision, and is never invented. The row stays "
                      "`unrecorded`", cruise)
        self.assertIn("never marked `confirmed` |", cruise)
        self.assertIn("| The word is a person's. The bosun proceeds on the recommendation at `Proposed` and says so |",
                      cruise)
        self.assertIn("a person confirms or overturns them afterwards", cruise)
        self.assertIn("(`make -f delivery/Makefile cruise`)", cruise, "the Makefile where the layout puts it")
        self.assertIn(".specify/cruise.json", files)
        self.assertIn("delivery/commands/cruise-settings.md", files)

    def test_the_settings_command_shows_every_setting_and_changes_them_through_the_script(self) -> None:
        """A setting changed by hand inside an iteration is a run under rules nobody can diff: the command lists
        every key with its values and default from the same list the file is written from, and changes go
        through the checked `--set`."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "settings-command", "standard", "go")
            command = (repo / "commands/cruise-settings.md").read_text()
            self.assertTrue(frontmatter(command)["description"].startswith("Show or change how /cruise runs /drive"))
            self.assertIn("| Setting | Values | Default | Controls |", command)
            for key, values, default, controls in SETTINGS:
                spelled = " \\| ".join(f"`{value}`" for value in values) if isinstance(values, tuple) else values
                self.assertIn(f"| `{key}` | {spelled} | `{json.dumps(default)}` | {controls} |", command)
            self.assertIn(f"python3 {SCRIPT} --set $ARGUMENTS", command)
            self.assertIn(f"python3 {SCRIPT}\n```", command)
            self.assertIn(f"commit `{CONFIG}` on its own", command)
            self.assertIn(f"it is `python3 {SCRIPT}\nstop` — `touch {STOP_FILE}`, which ends the run after the "
                          "iteration in flight; `--now` ends that iteration too", command)

    def test_the_skipper_decides_and_never_invents_a_fact_and_the_hand_demos_and_never_edits_code(self) -> None:
        """A skipper that deferred is a stalled slice; one that made up a credential is a shipped guess; a hand
        that fixed what it found would make the verdict evidence for itself. Each type declares its scope in the
        frontmatter the projection enforces and says the refusal in its own words."""
        by_key = {stage.key: stage for stage in STAGES}
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "types", "event-modelling", "python")
            skipper = (repo / f"agents/{SKIPPER}.md").read_text()
            hand = (repo / f"agents/{HAND}.md").read_text()
            for text, stage in ((skipper, by_key["skipper"]), (hand, by_key["hand"])):
                declared = frontmatter(text)
                self.assertEqual(declared["stage"], stage.key)
                self.assertEqual(declared["writes"], stage.writes)
                self.assertEqual(declared["commands"], stage.commands)
                self.assertIn("docs/delegated-agent-safety.md", text)
                self.assertIn("hands the question back", text)
            self.assertEqual((by_key["skipper"].writes, by_key["skipper"].commands), ("none", "read-only"))
            self.assertEqual((by_key["hand"].writes, by_key["hand"].commands), ("report", "any"))
            self.assertIn("You are the product owner for one question, and you decide it.", skipper)
            self.assertIn("Decide. Do not defer, do not list the options back", skipper)
            self.assertIn("**A fact is not a decision, and you never invent one.**", skipper)
            self.assertIn("`unavailable: <what a person must provide>`", skipper)
            self.assertIn("You write nothing. Return the whole entry, in the shape", skipper)
            self.assertIn("`D<n>` is allocated by the session that delegated you, before dispatch", skipper)
            self.assertIn("Number nothing\nelse:", skipper)
            self.assertIn("You are the actor. You use what the slice built and you say what using it revealed.", hand)
            self.assertIn("**The brief names the rung your ladder starts at** — `.specify/cruise.json`'s `hand`: "
                          "`browser`, `http` or\n`cli` — and you never climb above it.", hand)
            self.assertIn(f"`{BROWSER}` first", hand)
            self.assertIn("Under `http` start there, and under `cli` at the CLI", hand)
            self.assertIn("Leave the app the brief started running when you finish and say that it is up: the "
                          "session that delegated\nyou stops it once your verdict is recorded", hand)
            for word in ("`accepted`", "`behaviour`", "`implementation`"):
                self.assertIn(word, hand)
            self.assertIn("you edit no code, no test and no artifact of\nthe slice", hand)
            self.assertIn(f"Your writes are `{DEMO_LOG}`", hand)
            self.assertIn("`make verify` is not yours to run", hand)

    def test_the_models_table_names_both_stages_and_the_skipper_role_resolves(self) -> None:
        """A stage the table does not name runs on the `default` row silently, and a role no harness maps is
        refused by the check: both stages have rows, `skipper` is a role seeded to the host everywhere, and the
        resolver prints a line for each — so a project can put a bigger model on deciding than on driving."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "models", "standard", "typescript")
            table = json.loads((repo / ".specify/models.json").read_text())
            self.assertEqual(table["stages"]["skipper"], "skipper")
            self.assertEqual(table["stages"]["hand"], "strong")
            for entry in switchable_harnesses():
                self.assertEqual(table["roles"][entry["key"]]["skipper"], "host", entry["key"])
            installed(repo, "claude")
            models = repo / "scripts/agents/models.py"
            skipper = subprocess.run(["python3", str(models), "skipper"], cwd=repo, text=True, capture_output=True)
            self.assertEqual(skipper.stdout, "skipper: skipper → host model — `skipper` maps to the host model\n")
            hand = subprocess.run(["python3", str(models), "hand"], cwd=repo, text=True, capture_output=True)
            self.assertEqual(hand.stdout, "hand: strong → host model — `strong` maps to the host model\n")
            check = subprocess.run(["python3", str(models), "--check"], cwd=repo, text=True, capture_output=True)
            self.assertEqual(check.returncode, 0, check.stderr)
            self.assertIn("names 17 stage(s)", check.stdout)
            changed = subprocess.run(["python3", str(models), "--set", "claude.skipper=opus"], cwd=repo, text=True,
                                     capture_output=True)
            self.assertEqual(changed.returncode, 0, changed.stderr)
            self.assertEqual(json.loads((repo / ".specify/models.json").read_text())["roles"]["claude"]["skipper"],
                             "opus")

    def test_the_ladder_and_the_skills_page_name_the_two_types_as_cruises(self) -> None:
        """Under `/drive` alone a person is the owner and the actor, so the two rows in the delegable-types table
        have to say whose they are, and the page that lists what a project carries names the command and both
        types — a type no page names is one a session discovers from an error."""
        with tempfile.TemporaryDirectory() as directory:
            for profile in PROFILES:
                repo = self.generate(directory, f"pages-{profile}", profile, "go")
                drive = (repo / "commands/drive.md").read_text()
                self.assertIn(f"| `skipper` | `{SKIPPER}` | nothing | anything that reads |", drive)
                self.assertIn(f"| `hand` | `{HAND}` | only the report it produces | anything |", drive)
                self.assertIn("The last three rows, `skipper`, `hand` and `bosun`,\nare `/cruise`'s: the product "
                              "owner, the actor and the one who gets a blocked run moving", drive)
                self.assertIn(f"| `bosun` | `{BOSUN}` | the files its manifest names | anything |", drive)
                self.assertIn("Under `/drive` alone they run nothing; a person is the owner and the actor.", drive)
                page = (repo / "docs/skills-and-commands.md").read_text()
                self.assertIn("- `/cruise` — `commands/cruise.md`\n"
                              "- `/cruise-settings` — `commands/cruise-settings.md`", page)
                self.assertIn(f"Three more, `{SKIPPER}`, `{HAND}` and `{BOSUN}`, are `/cruise`'s product owner, "
                              "actor and\nunblocker", page)
                self.assertIn("`claude.skipper=opus`", (repo / "commands/model-delegation-settings.md").read_text())

    def test_the_benchmark_records_who_drove(self) -> None:
        """A piloted slice and a driven one cost differently, and a record that cannot say which was which cannot
        compare them: `driver=cruise` is a signal `end` accepts and writes, and the two delegates are stages the
        record takes without complaint."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "driver", "standard", "python")
            slice_ = "specs/shop/slices/S1"
            (repo / slice_).mkdir(parents=True)
            (repo / slice_ / "tasks.md").write_text("# Tasks\n- [ ] T1\n")
            commit(repo, "the slice begins")
            env = clean()
            for stage, signal in (("skipper", "driver=cruise"), ("hand", "outcome=accepted"),
                                  ("implement", "driver=cruise")):
                self.assertEqual(bench(repo, "start", slice_, stage, env=env).returncode, 0, stage)
                ended = bench(repo, "end", slice_, stage, signal, env=env)
                self.assertEqual(ended.returncode, 0, (stage, ended.stderr))
            stages = record(repo, slice_)["stages"]
            self.assertEqual([entry["stage"] for entry in stages], ["skipper", "hand", "implement"])
            self.assertEqual(stages[0]["signals"], {"driver": "cruise"})
            self.assertEqual(stages[2]["signals"], {"driver": "cruise"})
            refused = bench(repo, "end", slice_, "implement", "driver=cruise", env=env)
            self.assertEqual(refused.returncode, 1, "no open entry to close")
