"""The stages `/drive` delegates are named types the harness enforces, not scopes asked for in a brief."""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase
from test_adopt import repository, slipwai
from test_stage_models import installed, models

from slipwai.assets import TOOLKIT_ROOT
from slipwai.project.agents import types

REGISTRY = json.loads((TOOLKIT_ROOT / "scripts/agents/registry.json").read_text())["harnesses"]
# Every harness whose own documentation was read for how it declares a named agent type.
WITH_AGENT_FILES = {"claude", "codex", "copilot", "cursor-agent", "gemini", "opencode"}
# What each harness's file must show for a type declaring `writes: none` — the key it withholds editing with,
# read from that harness's documentation (`agentFile.writes` in the registry says the same in prose).
READ_ONLY_KEY = {
    "claude": "disallowedTools: Edit, Write, NotebookEdit",
    "codex": 'sandbox_mode = "read-only"',
    "copilot": '"read"',
    "cursor-agent": "readonly: true",
    "gemini": "  - read_file",
    "opencode": "  edit: deny",
}
# The harnesses whose agent file can also bound what a delegate *runs*. The other four cannot: the shell is one
# tool there, and an adversary has to run a reproduction, so denying it outright would be stricter than the
# declaration and useless. Those four carry `commands: read-only` in the prompt and say so in the stamp.
ENFORCES_COMMANDS = {"codex", "cursor-agent"}
# The two harnesses whose read-only spelling IS a tool list, so the list is the whole grant and an MCP tool it
# leaves out is withheld. The other four reach the session's servers whatever the agent file says: Claude Code
# and Codex inherit them, Cursor inherits every tool, and opencode's permission map is a denylist.
GRANTS_MCP_IN_A_TOOL_LIST = {"copilot", "gemini"}
# What each of those two has to name for the code index to survive its read-only list.
MCP_GRANT = {"copilot": '"codegraph/*"', "gemini": "  - mcp_*"}


def harness(key: str) -> dict:
    return next(entry for entry in REGISTRY if entry["key"] == key)


def projected(repo: Path, key: str, name: str) -> str:
    row = harness(key)["agentFile"]
    return (repo / row["dir"] / f"{name}{row['extension']}").read_text()


class AgentTypesTest(FactoryTestCase):
    def test_the_registry_says_per_harness_how_a_type_is_declared_and_a_no_is_written(self) -> None:
        """A projection can only be as honest as the row it is rendered from, so the row is read from the
        harness's own documentation with the date on it, `null` where nothing was verified — and `null` again,
        inside a row, for a scope that harness cannot express, with the reason beside it. A harness that can
        name an agent type is a harness that can choose a sub-task's model: on five of the six that file is
        the *only* place it can, which is why the file has to be a projection of `.specify/models.json`."""
        verified = set()
        for entry in REGISTRY:
            self.assertIn("agentFile", entry, entry["key"])
            row = entry["agentFile"]
            if row is None:
                continue
            verified.add(entry["key"])
            self.assertIsInstance(entry["subagentModel"], dict, entry["key"])
            for field in ("dir", "extension", "format", "model", "writes", "source"):
                self.assertTrue(row.get(field), f"{entry['key']}: {field}")
            self.assertRegex(row["source"], r"read \d{4}-\d{2}-\d{2}$", entry["key"])
            self.assertIn("commands", row, entry["key"])
            if row["commands"] is None:
                # A negative answer is written, with its reason, never left as a missing key.
                self.assertTrue(row.get("commandsReason"), entry["key"])
            self.assertEqual(entry["key"] in ENFORCES_COMMANDS, row["commands"] is not None, entry["key"])
            # How a delegate here reaches this project's MCP servers, read the same way. A harness whose write
            # scope is a tool list withholds every MCP tool that list leaves out, and nothing says so at the
            # call — so the row carries what it takes to keep the route open, `null` where nothing is needed.
            self.assertIsInstance(row.get("mcp"), dict, entry["key"])
            self.assertTrue(row["mcp"].get("reaches"), entry["key"])
            self.assertIn("grant", row["mcp"], entry["key"])
            self.assertRegex(row["mcp"]["source"], r"read \d{4}-\d{2}-\d{2}$", entry["key"])
            self.assertEqual(entry["key"] in GRANTS_MCP_IN_A_TOOL_LIST, row["mcp"]["grant"] is not None,
                             entry["key"])
        self.assertEqual(verified, WITH_AGENT_FILES)

    def test_one_canonical_type_per_delegated_stage_and_one_for_a_whole_slice(self) -> None:
        """Six types are the stages the ladder sends to a fresh context, named for the stage so the model
        resolves through the table with no second lookup, and declaring their scope in words no harness owns.
        A conversational stage has no type, because it stays here. The seventh is `/drive`'s slice delegate,
        which runs a whole slice in a worktree of its own and reads the table stage by stage inside itself —
        so it declares no stage, and inherits rather than resolving one model for fourteen stages."""
        self.assertEqual([agent.name for agent in types()],
                         ["drive-gaps", "drive-tasks", "drive-implement", "drive-converge", "drive-adversary",
                          "drive-mutation", "drive-slice"])
        self.assertEqual(next(a for a in types() if a.name == "drive-slice").stage, "none")
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "types", "standard", "python")
            self.assertEqual(sorted(path.name for path in (repo / "agents").glob("*.md")),
                             sorted(f"{agent.name}.md" for agent in types()))
            for agent in types():
                text = (repo / "agents" / f"{agent.name}.md").read_text()
                self.assertTrue(text.startswith("---\n"), agent.name)
                declared = dict(
                    line.split(": ", 1) for line in text.split("\n---\n")[0].splitlines()[1:] if ": " in line
                )
                self.assertEqual(declared["name"], agent.name)
                self.assertEqual(declared["stage"], agent.stage)
                self.assertEqual(declared["writes"], agent.writes)
                self.assertEqual(declared["commands"], agent.commands)
                self.assertTrue(declared["description"])
                # The standing part of the brief, and the one page it defers to rather than copying.
                self.assertIn("docs/delegated-agent-safety.md", text)
                self.assertIn("hands the question back", text)
            # The stage that must never be able to fix what it finds says so in its own words too.
            adversary = (repo / "agents/drive-adversary.md").read_text()
            self.assertIn("You never fix it.", adversary)
            self.assertIn("you may not edit a file", adversary)
            tasks = (repo / "agents/drive-tasks.md").read_text()
            self.assertIn("Every task is **one RED-GREEN-REFACTOR increment**", tasks)
            self.assertIn("Your one write is this slice's `tasks.md`", tasks)
            self.assertIn("styling is a task here", tasks)
            self.assertIn("*Parallel opportunities* section", tasks)
            self.assertIn("leave a `## Convergence` heading", tasks)
            # And the ladder delegates by type rather than describing the role again.
            drive = (repo / "commands/drive.md").read_text()
            self.assertIn("| `adversary` | `drive-adversary` | nothing | anything that reads |", drive)
            self.assertIn(
                "| `tasks` | `drive-tasks` | only the slice's `tasks.md` | "
                "anything that reads, plus the installed tasks command |",
                drive,
            )
            self.assertIn("Delegate to the type by name.", drive)
            self.assertIn("`drive-implement · model: sonnet · delegated, fresh context`", drive)
            self.assertIn("the `drive-adversary` type", (repo / "commands/adversary.md").read_text())
            # And the fan-out delegates a whole slice to the type that carries one.
            self.assertIn("to one fresh `drive-slice` delegate", drive)
            self.assertIn("strictly sequential", (repo / "agents/drive-slice.md").read_text().lower())

    def test_each_harness_gets_the_type_in_its_own_spelling_with_what_it_can_enforce(self) -> None:
        """The point of the whole thing: a read-only type reaches the harness as a file that withholds
        editing, rather than as a sentence in a brief asking the delegate not to. Each projection is checked
        against the keys that harness's own documentation names, and where the harness cannot hold part of
        the declaration the stamp says so in as many words — a gap somebody can read beats a gap assumed
        away."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "spelling", "standard", "python")
            installed(repo, *sorted(WITH_AGENT_FILES))
            subprocess.run(["python3", "scripts/agents/project.py"], cwd=repo, check=True, capture_output=True)
            for key in sorted(WITH_AGENT_FILES):
                adversary = projected(repo, key, "drive-adversary")
                tasks = projected(repo, key, "drive-tasks")
                implement = projected(repo, key, "drive-implement")
                self.assertIn("Generated from agents/drive-adversary.md", adversary, key)
                self.assertIn("You attack one seam", adversary, key)
                # `writes: none` is expressible everywhere, and this is the key each harness expresses it with.
                self.assertIn(READ_ONLY_KEY[key], adversary, key)
                self.assertNotIn(READ_ONLY_KEY[key], implement, key)
                self.assertIn("`writes: none` is enforced here", adversary, key)
                self.assertIn("`writes: manifest` is a per-call manifest", implement, key)
                self.assertIn("`writes: tasks` is the fixed scope of this slice's tasks.md", tasks, key)
                self.assertIn("cannot restrict them to one path", tasks, key)
                self.assertIn("`commands: tasks-command` permits read-only inspection", tasks, key)
                # `commands: read-only` is not, and the stamp is where that is admitted.
                if key in ENFORCES_COMMANDS:
                    self.assertIn("`commands: read-only` is enforced here", adversary, key)
                else:
                    self.assertIn("`commands: read-only` is NOT enforced here", adversary, key)
                    self.assertIn("The body asks for it instead.", adversary, key)
            # Claude Code is the case the issue called out: the editing tools can go, `Bash` cannot.
            claude = projected(repo, "claude", "drive-adversary")
            self.assertIn("Bash is one tool, allowed or not at all", claude)
            # Codex's one flag covers both, and its body is a TOML literal rather than a markdown file.
            codex = projected(repo, "codex", "drive-adversary")
            self.assertIn("developer_instructions = '''", codex)
            self.assertIn('name = "drive-adversary"', codex)
            # Nothing is committed: a projection is the canonical file again, and the gate re-derives it.
            ignored = (repo / ".gitignore").read_text()
            for key in sorted(WITH_AGENT_FILES):
                self.assertIn(f"{harness(key)['agentFile']['dir']}/\n", ignored, key)
            check = subprocess.run(["python3", "scripts/agents/project.py", "--check"], cwd=repo, text=True,
                                   capture_output=True)
            self.assertEqual(check.returncode, 0, check.stderr)
            (repo / ".claude/agents/drive-adversary.md").write_text("edited by hand\n")
            drifted = subprocess.run(["python3", "scripts/agents/project.py", "--check"], cwd=repo, text=True,
                                     capture_output=True)
            self.assertEqual(drifted.returncode, 1)
            self.assertIn(".claude/agents/drive-adversary.md: differs from its canonical source", drifted.stderr)

    def test_a_read_only_type_keeps_the_route_to_the_code_index(self) -> None:
        """The write scope a harness expresses as a *tool list* is a grant, not a denial: Gemini and Copilot
        withhold every tool the list leaves out, MCP tools included. So the projection that made
        `drive-gaps` and `drive-adversary` read-only was also, silently, the thing that put the CodeGraph MCP
        server out of the delegate's reach on those two — no error at the call, just a harness where *probe
        your MCP route* can only ever fail. The lists name it back, which costs nothing that was being held:
        both already carry the whole shell. And every projection says in its stamp how the route stands
        here, because a withheld route nobody can read is the failure repeating itself."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "reachable", "standard", "python")
            installed(repo, *sorted(WITH_AGENT_FILES))
            subprocess.run(["python3", "scripts/agents/project.py"], cwd=repo, check=True, capture_output=True)
            for key in sorted(WITH_AGENT_FILES):
                for name in ("drive-adversary", "drive-gaps"):
                    text = projected(repo, key, name)
                    self.assertIn("A delegate here", text, f"{key}/{name}: the stamp says nothing about MCP")
                    if key in GRANTS_MCP_IN_A_TOOL_LIST:
                        self.assertIn(MCP_GRANT[key], text, f"{key}/{name}: the tool list withholds MCP")
                        self.assertIn("grants them back with", text, key)
                    else:
                        self.assertNotIn("grants them back with", text, key)
            # The two harnesses that inherit rather than list say which inheritance it is, so the next reader
            # does not have to go and ask the documentation again.
            self.assertIn("can arrive deferred", projected(repo, "claude", "drive-adversary"))
            self.assertIn("inherits the parent session's `mcp_servers`", projected(repo, "codex", "drive-gaps"))
            # A type that may write gets no tool list at all on those two, so nothing is withheld there.
            self.assertNotIn("tools:", projected(repo, "gemini", "drive-implement"))
            self.assertNotIn("tools:", projected(repo, "copilot", "drive-implement"))
            # And the server Copilot has to name by hand is one this factory actually installs, not a
            # name that drifted: an entry for an extension nobody ships would be ignored in silence, which
            # is the same silence this test exists to break.
            projector = (TOOLKIT_ROOT / "scripts/agents/project.py").read_text()
            servers = projector.split("EXTENSION_MCP_SERVERS = (")[1].split(")")[0]
            self.assertTrue(servers.strip(), "no MCP server is named for Copilot's list")
            for server in [name.strip().strip('",') for name in servers.split(",") if name.strip()]:
                self.assertTrue((TOOLKIT_ROOT / f"scripts/extensions/{server}/init.py").is_file(), server)

    def test_the_model_comes_from_the_table_and_a_change_rewrites_the_types(self) -> None:
        """The agent file is a projection of `.specify/models.json`, never a second place a model is written:
        five of the six harnesses can only give a sub-task its own model here, so if the file decided for
        itself `/model-delegation-settings` would stop being the answer to which model runs implement. Which
        means a `--set` has to rewrite the files, and a role that maps to nothing has to say so rather than
        pick something."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "resolved", "standard", "python")
            installed(repo, "claude", "codex")
            subprocess.run(["python3", "scripts/agents/project.py"], cwd=repo, check=True, capture_output=True)
            # `implement` is `fast`, and Claude Code's `fast` is the one identifier the factory seeds.
            self.assertIn("model: sonnet\n", projected(repo, "claude", "drive-implement"))
            self.assertIn("model: sonnet\n", projected(repo, "claude", "drive-tasks"))
            self.assertIn("`tasks` resolves to sonnet in .specify/models.json",
                          projected(repo, "claude", "drive-tasks"))
            self.assertIn("`implement` resolves to sonnet in .specify/models.json",
                          projected(repo, "claude", "drive-implement"))
            # `adversary` is `strong`, which maps to the host model everywhere: no model, and why.
            adversary = projected(repo, "claude", "drive-adversary")
            self.assertNotIn("\nmodel:", adversary)
            self.assertIn("`strong` maps to the host model, so this type inherits the session's model",
                          adversary)
            # Codex maps no identifier for `fast` yet, so its type says that rather than guessing one.
            self.assertIn("no identifier mapped for `fast` under `codex`",
                          projected(repo, "codex", "drive-implement"))
            # The slice delegate takes no stage's model on any harness — it picks one per stage inside itself,
            # so resolving one here would choose a model for the whole ladder at once.
            for key in ("claude", "codex"):
                slice_type = projected(repo, key, "drive-slice")
                self.assertNotIn("model", slice_type.split("\n\n")[0].replace("the session's model", ""), key)
                self.assertIn("reads the table stage by stage inside itself", slice_type, key)

            changed = models(repo, "--set", "claude.fast=haiku")
            self.assertEqual(changed.returncode, 0, changed.stderr)
            self.assertIn("Projections rewritten: the agent types carry the model this table names.",
                          changed.stdout)
            self.assertIn("model: haiku\n", projected(repo, "claude", "drive-implement"))
            check = subprocess.run(["python3", "scripts/agents/project.py", "--check"], cwd=repo, text=True,
                                   capture_output=True)
            self.assertEqual(check.returncode, 0, check.stderr)
            self.assertIn("rewrites the agent types", (repo / "commands/model-delegation-settings.md").read_text())

    def test_a_fresh_clone_has_no_projections_and_is_not_drifted(self) -> None:
        """The projections are derived and ignored, so a clone nobody has run `./init` in has none — which is
        a clone, not drift, and the gate says which."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "fresh", "standard", "python")
            check = subprocess.run(["python3", "scripts/agents/project.py", "--check"], cwd=repo, text=True,
                                   capture_output=True)
            self.assertEqual(check.returncode, 0, check.stderr)
            self.assertIn("not initialized; no projections expected yet", check.stdout)
            installed(repo, "claude")
            unprojected = subprocess.run(["python3", "scripts/agents/project.py", "--check"], cwd=repo, text=True,
                                         capture_output=True)
            self.assertEqual(unprojected.returncode, 0, unprojected.stderr)
            self.assertIn("Claude Code: not projected here", unprojected.stdout)

    def test_a_moved_layout_carries_the_types_with_everything_else(self) -> None:
        """An adopted repository keeps the method under `delivery/`, so the canonical types go there and the
        Makefile they name is the moved one; the projections still land where the harness reads them, which
        is the repository root."""
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", {
                "package.json": '{"name": "shop", "private": true, "scripts": {"test": "node --test"}}\n',
                "package-lock.json": '{"name": "shop", "lockfileVersion": 3}\n',
                "test/a.test.js": "test('a', () => {});\n",
            })
            result = slipwai(repo, "adopt", "--yes")
            self.assertEqual(result.returncode, 0, result.stderr)
            implement = (repo / "delivery/agents/drive-implement.md").read_text()
            self.assertIn("`make -f delivery/Makefile verify`", implement)
            self.assertIn("delivery/docs/delegated-agent-safety.md", implement)
            installed(repo, "claude")
            subprocess.run(["python3", "delivery/scripts/agents/project.py"], cwd=repo, check=True,
                           capture_output=True)
            self.assertIn("Generated from delivery/agents/drive-implement.md",
                          (repo / ".claude/agents/drive-implement.md").read_text())
