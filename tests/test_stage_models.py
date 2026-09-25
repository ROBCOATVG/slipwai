"""Each stage of `/drive` runs on a model chosen for it — or on the host model, said out loud."""
from __future__ import annotations

import ast
import json
import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase
from test_adopt import repository, slipwai

from slipwai.assets import TOOLKIT_ROOT
from slipwai.project.stage_models import FAST_SEEDED, STAGES, switchable_harnesses

SCRIPT = TOOLKIT_ROOT / "scripts/agents/models.py"
VERIFIED = {"claude", "codex", "copilot", "cursor-agent", "gemini", "opencode"}


def models(repo: Path, *arguments: str, delivery: str = ".") -> subprocess.CompletedProcess:
    return subprocess.run(
        ["python3", str(repo / delivery / "scripts/agents/models.py"), *arguments],
        cwd=repo, text=True, capture_output=True,
    )


def installed(repo: Path, *keys: str) -> None:
    (repo / ".specify/integration.json").write_text(json.dumps({"installed_integrations": list(keys)}))


class StageModelsTest(FactoryTestCase):
    def test_the_table_carries_the_default_split_and_drive_applies_it(self) -> None:
        """The choice lives in the project, versioned with it, keyed by the command each stage runs: strong
        where a stage decides what to build or whether it was built, fast where the input is already on
        paper. Roles, not identifiers — those go stale — and `host` is a value: the model running `/drive`,
        which `strong` maps to everywhere. The ladder reads the table before a stage and says which model ran
        it either way, because a silent switch cannot be compared with anything."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "split", "standard", "python")
            table = json.loads((repo / ".specify/models.json").read_text())
            self.assertEqual(table["stages"], {"default": "strong", **{s.key: s.role for s in STAGES}})
            self.assertEqual({s.key for s in STAGES if s.role == "fast"}, {"tasks", "implement", "mutation"})
            self.assertEqual(list(table["roles"]), [entry["key"] for entry in switchable_harnesses()])
            for key, roles in table["roles"].items():
                self.assertEqual(roles["strong"], "host", key)
                self.assertEqual(roles["fast"], FAST_SEEDED.get(key), key)
            self.assertEqual(table["roles"]["claude"]["fast"], "sonnet")

            drive = (repo / "commands/drive.md").read_text()
            section = drive.split("## Who runs each stage")[1].split("## Once inside the slice")[0]
            self.assertIn("python3 scripts/agents/models.py implement", section)
            self.assertIn("`make models` prints them all", section)
            self.assertIn(
                "Prefer a fresh\nsub-agent whenever the stage can get all of its inputs from artifacts", section,
            )
            self.assertIn("set it explicitly through the mechanism the registry\nnames", section)
            self.assertIn("whether its context was fresh", section)
            self.assertIn("Nothing about what a stage produces changes with who runs", section)
            self.assertIn("hands the\nquestion back here", section)
            # The tasks command writes `[P]` markers and a parallel-opportunities section into every tasks.md,
            # and until this paragraph nothing told the driver to read them: it printed six `[P]` tasks to see
            # what was unchecked, then delegated them one at a time. The rule that has to be spelled out is
            # the one the siblings cannot infer — tasks.md is the file they would all write.
            self.assertIn("read `tasks.md` for its `[P]` markers", section)
            self.assertIn("*Parallel opportunities* section", section)
            self.assertIn("whose files are disjoint from the batch already running is a concurrent sibling", section)
            self.assertIn("**no concurrent delegate writes `tasks.md`**", section)
            self.assertIn("each reports which task it finished and this session ticks the checkbox", section)
            # And the markers never override what the section rules out: increments stay sequential.
            self.assertIn("starts\nfrom a green, committed suite", section)
            self.assertLess(section.index("is a concurrent sibling"),
                            section.index("report once when the batch completes"))
            # The owner's to change at any point, and read before every stage so the change is the next stage's.
            self.assertIn("read before every stage rather than once", section)
            self.assertIn("merges a newer factory's table over it rather than replacing it", section)
            # Applied before the slice is entered, not after: the entry stage is the first delegated one.
            self.assertLess(drive.index("## Enter at the first incomplete stage"),
                            drive.index("## Who runs each stage"))

            makefile = (repo / "Makefile").read_text()
            self.assertIn("models: ## Show which model runs each stage of /drive", makefile)
            gate = ("check-agents: ## Fail when an initialized agent projection has drifted, "
                    "or .specify/models.json, drive.json or cruise.json is malformed\n"
                    "\tpython3 scripts/agents/project.py --check\n"
                    "\tpython3 scripts/agents/models.py --check && python3 scripts/agents/drive.py --check && "
                    "python3 scripts/agents/cruise.py --check\n")
            self.assertIn(gate, makefile)
            subprocess.run(["make", "check-agents"], cwd=repo, check=True, capture_output=True)
            for page in ("docs/agent-harnesses.md",):
                self.assertIn("subagentModel", (repo / page).read_text())

            # The change is a command of the project's own, projected like every other, and it goes through the
            # checked path — the ladder names it as the way an owner's request becomes the change.
            command = (repo / "commands/model-delegation-settings.md").read_text()
            self.assertIn("description: Show or change which model runs each stage of /drive", command)
            self.assertIn("python3 scripts/agents/models.py --set $ARGUMENTS", command)
            self.assertIn("do not work around it by editing the file", command)
            self.assertIn("ask for the identifier rather than inventing one", command)
            self.assertIn("commit\n`.specify/models.json` on its own", command)
            self.assertIn("`/model-delegation-settings implement=strong claude.fast=haiku` edits it checked", section)
            self.assertIn("- `/model-delegation-settings` — `commands/model-delegation-settings.md`",
                          (repo / "docs/skills-and-commands.md").read_text())
            installed(repo, "claude")
            subprocess.run(["python3", "scripts/agents/project.py", "claude"], cwd=repo, check=True,
                           capture_output=True)
            projected = (repo / ".claude/commands/model-delegation-settings.md").read_text()
            self.assertIn("Generated from commands/model-delegation-settings.md", projected)

    def test_delegation_names_the_safety_page_and_each_sessions_index_routes(self) -> None:
        """The delegation preference and the code-index block used to say opposite things about the same
        stages: prefer a fresh sub-agent for converge, post-implementation gaps and adversary, while the
        block says to answer those from the index yourself because a delegate cannot reach it. Following
        the first silently loses the index on exactly the stages a blast-radius question is asked, and a
        pass explored without it reads like a clean one. So the preference now carries the exemption, and
        it says what the brief must contain when the stage is delegated anyway.

        The other half is the standing contract. `AGENTS.md` requires every brief to reference
        `docs/delegated-agent-safety.md`, and every agent type in `agents/` carries it — but the section
        that describes delegation at length never named it, which is how a brief ends up restating the
        constraints inline and drifting from the page they are written on."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "delegating", "event-modelling", "typescript")
            drive = (repo / "commands/drive.md").read_text()
            section = drive.split("## Who runs each stage")[1].split("## Once inside the slice")[0]

            self.assertIn("`docs/delegated-agent-safety.md`", section)
            self.assertIn("the standing boundary every\ndelegation is held to", section)
            self.assertIn("reference it, restate none of it", section)
            self.assertTrue((repo / "docs/delegated-agent-safety.md").is_file())

            flat = " ".join(section.split())
            self.assertIn("A delegate does not inherit this session's code-index connection, and needs none", flat)
            self.assertIn("`drive-converge`, `drive-gaps` and `drive-adversary`", flat)
            # The route a delegate has whatever its session was given, rather than an order of routes to probe.
            self.assertIn("every delegate's shell has `scripts/codegraph`", flat)
            self.assertNotIn("Prefer to run those here", flat)
            self.assertIn("Never pass the parent conversation", flat)
            for agent in (repo / "agents").glob("drive-*.md"):
                body = " ".join(agent.read_text().split())
                self.assertIn("Where the tree has `.codegraph/`", body)
                self.assertIn("`scripts/codegraph callers <symbol>`", body)
                self.assertIn("Name the route that answered", body)

    def test_the_registry_says_per_harness_what_is_possible_and_a_no_is_written(self) -> None:
        """Harnesses differ in how a sub-task gets its model, so the registry is where that is said — read
        from each harness's own documentation, with the date, never assumed. A harness nothing was verified
        for records `null` on every row rather than a missing key, so "cannot switch" is a fact the script
        reports and not a gap it fell through. The script's list of stages is the factory's list."""
        registry = json.loads((TOOLKIT_ROOT / "scripts/agents/registry.json").read_text())
        verified = set()
        for harness in registry["harnesses"]:
            self.assertIn("subagentModel", harness, harness["key"])
            mechanism = harness["subagentModel"]
            if mechanism is None:
                continue
            verified.add(harness["key"])
            for field in ("how", "where", "identifiers", "source"):
                self.assertTrue(mechanism.get(field), f"{harness['key']}: {field}")
            self.assertRegex(mechanism["source"], r"read \d{4}-\d{2}-\d{2}$", harness["key"])
        self.assertEqual(verified, VERIFIED)
        self.assertEqual([entry["key"] for entry in switchable_harnesses()], sorted(VERIFIED))
        self.assertIn("`subagentModel` is the factory's own", registry["_generated"])
        self.assertNotIn("regenerate-registry", registry["_generated"])

        module = ast.parse(SCRIPT.read_text())
        known = next(
            ast.literal_eval(node.value)
            for node in module.body
            if isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "KNOWN_STAGES" for t in node.targets)
        )
        self.assertEqual(tuple(known), tuple(stage.key for stage in STAGES))

    def test_the_resolver_names_the_model_or_says_why_it_is_the_hosts(self) -> None:
        """One line per stage, and every road to the host model is a different sentence: the role maps to
        host, no identifier is mapped for this harness, the registry records no mechanism, no harness is
        installed yet, or the project predates the table. A malformed table is refused by the check with
        every finding named, and the resolver points at the check rather than resolving from a broken file."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "resolve", "event-modelling", "go")
            absent = models(repo)
            self.assertEqual(absent.returncode, 0, absent.stderr)
            self.assertIn("no harness installed yet", absent.stdout)
            self.assertIn("implement: fast → host model", absent.stdout)

            installed(repo, "claude")
            self.assertEqual(
                models(repo, "implement").stdout.strip(),
                "implement: fast → sonnet — Claude Code: the Agent tool's `model` parameter, set per call",
            )
            host = "strong → host model — `strong` maps to the host model"
            self.assertEqual(models(repo, "plan").stdout.strip(), f"plan: {host}")
            # A stage the table has no row for — an adopted repository's Ground or Pin — takes the default row.
            self.assertEqual(models(repo, "ground").stdout.strip(), f"ground: {host}")
            whole = models(repo).stdout
            self.assertTrue(whole.startswith(
                "Claude Code (claude):\n  can switch: the Agent tool's `model` parameter, set per call; identifiers: "
                "an alias — sonnet, opus, haiku, fable — or a model id\n  principles: strong → host model"))
            self.assertIn("\n  mutation: fast → sonnet — Claude Code:", whole)

            installed(repo, "codex", "amp")
            both = models(repo, "tasks").stdout
            self.assertIn("Codex CLI (codex):\n  can switch: a custom agent file with `model`", both)
            self.assertIn("\n  tasks: fast → host model — no identifier mapped for `fast` under `codex` in "
                          ".specify/models.json", both)
            self.assertIn("Amp (amp):\n  cannot switch: the registry records no way for Amp to choose a model for a "
                          "sub-task\n  tasks: fast → host model — the registry records no way for Amp", both)

            check = models(repo, "--check")
            self.assertEqual(check.returncode, 0, check.stderr)
            self.assertIn("check-models: .specify/models.json names 17 stage(s) and 6 harness(es)", check.stdout)

            path = repo / ".specify/models.json"
            table = json.loads(path.read_text())
            table["stages"]["implment"] = "quick"
            table["roles"]["nope"] = {"strong": "host"}
            del table["roles"]["claude"]["fast"]
            path.write_text(json.dumps(table))
            broken = models(repo, "--check")
            self.assertEqual(broken.returncode, 1)
            for finding in (
                "`stages.implment` is not a stage of the ladder",
                "`roles.claude` does not say what `fast` maps to",
                "`roles.codex` does not say what `quick` maps to",
                "`roles.nope` is not a harness the registry knows",
            ):
                self.assertIn(finding, broken.stderr)
            resolved = models(repo, "implement")
            self.assertEqual(resolved.returncode, 1)
            self.assertIn("is malformed; `make check-agents` lists why", resolved.stderr)
            gate = subprocess.run(["make", "check-agents"], cwd=repo, text=True, capture_output=True)
            self.assertNotEqual(gate.returncode, 0)

            path.unlink()
            before = models(repo, "implement")
            self.assertEqual(before.returncode, 0, before.stderr)
            self.assertEqual(before.stdout.strip(), "no .specify/models.json: every stage runs on the host model; "
                                                    "`slipwai migrate` writes the table")

    def test_a_moved_layout_finds_the_table_at_the_root(self) -> None:
        """An adopted repository keeps the method under `delivery/`; `.specify/` stays at the root where Spec Kit
        puts it, and the script finds the root by `project.json` the way every toolkit script does. The ladder
        names the moved script and the moved Makefile."""
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", {
                "package.json": '{"name": "shop", "private": true, "scripts": {"test": "node --test"}}\n',
                "package-lock.json": '{"name": "shop", "lockfileVersion": 3}\n',
                "test/a.test.js": "test('a', () => {});\n",
            })
            result = slipwai(repo, "adopt", "--yes")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((repo / ".specify/models.json").is_file())
            self.assertTrue((repo / "delivery/scripts/agents/models.py").is_file())
            installed(repo, "claude")
            line = models(repo, "implement", delivery="delivery")
            self.assertEqual(line.returncode, 0, line.stderr)
            self.assertTrue(line.stdout.startswith("implement: fast → sonnet"))
            drive = (repo / "delivery/commands/drive.md").read_text()
            self.assertIn("python3 delivery/scripts/agents/models.py implement", drive)
            self.assertIn("`make -f delivery/Makefile models` prints them all", drive)

    def test_the_owner_changes_the_table_at_any_time_and_the_change_is_checked(self) -> None:
        """"Ensure that these models can be changed by the user as and when." One command changes a stage's role
        or what a role maps to on a harness, refuses what would never be read or would leave the table malformed,
        and writes nothing otherwise; the next resolution reads the change. A role a stage newly names is added
        as null under every harness so the line before the stage says "no identifier mapped" rather than the
        check saying "malformed"."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "change", "standard", "typescript")
            installed(repo, "claude")
            path = repo / ".specify/models.json"
            before = path.read_text()

            changed = models(repo, "--set", "implement=strong", "claude.fast=haiku")
            self.assertEqual(changed.returncode, 0, changed.stderr)
            self.assertIn("stages.implement = strong\nroles.claude.fast = haiku\n", changed.stdout)
            self.assertIn("takes effect at the next stage /drive runs. Commit it", changed.stdout)
            self.assertTrue(models(repo, "implement").stdout.startswith("implement: strong → host model"))
            self.assertTrue(models(repo, "tasks").stdout.startswith("tasks: fast → haiku — Claude Code:"))
            table = json.loads(path.read_text())
            self.assertEqual(table["stages"]["implement"], "strong")
            self.assertEqual(table["roles"]["claude"], {"strong": "host", "fast": "haiku", "skipper": "host"})
            self.assertEqual(table["_comment"], json.loads(before)["_comment"])

            added = models(repo, "--set", "tasks=cheap")
            self.assertEqual(added.returncode, 0, added.stderr)
            self.assertIn("`cheap` added as null under claude, codex, copilot, cursor-agent, gemini, opencode; map it "
                          "with --set <harness>.cheap=<id>", added.stdout)
            self.assertTrue(models(repo, "tasks").stdout.startswith(
                "tasks: cheap → host model — no identifier mapped for `cheap` under `claude`"))
            self.assertEqual(models(repo, "--check").returncode, 0)
            unmapped = models(repo, "--set", "claude.fast=null")
            self.assertEqual(unmapped.returncode, 0, unmapped.stderr)
            self.assertIsNone(json.loads(path.read_text())["roles"]["claude"]["fast"])

            written = path.read_text()
            for assignment, refusal in (
                ("amp.fast=x", "the registry records no way for Amp to choose a model for a sub-task, so a role mapped "
                               "for it would never be read"),
                ("bogus=strong", "`bogus` is not a stage of the ladder"),
                ("nope.fast=x", "`nope` is not a harness the registry knows"),
                ("implement", "--set takes stage=role or harness.role=identifier"),
            ):
                refused = models(repo, "--set", assignment)
                self.assertEqual(refused.returncode, 1, assignment)
                self.assertIn(refusal, refused.stderr, assignment)
            self.assertEqual(path.read_text(), written)
