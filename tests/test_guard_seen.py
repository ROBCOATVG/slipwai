"""An extension's own tools reach its guard, and the rule `codegraph` needs can be held: the acceptance proof.

The rule is *refuse a search of the source for a symbol until this session has asked the index, and never
refuse a search of documents* (#121; ROBCOATVG/slipwai-extension-codegraph#3). Two things made it
unholdable. A guard was handed only the query, which `tests/test_guard_event.py` covers. And *has asked the
index* was unobservable: an ask over MCP is a tool call, the harness's matcher named `Grep|Glob|Bash`, and
so a session that had asked went on being refused for ever.

So a guard declares the tools whose use it should **see**. That is a separate moment from the guard point —
`tool-use` — because seeing is not judging: the guard is told and whatever it exits with refuses nothing, so
an extension's guard cannot stop one of its own tools, or anybody else's, by being asked about it. And what
may be declared is one MCP server's tools by name, never a pattern that could match every call.

`CodegraphInMiniatureTest` is the rule itself, with a stand-in extension: the five cases the issue names.
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401
from guard_project import TOOLKIT, Project

from slipwai import guards
from slipwai.layout import AT_ROOT
from slipwai.project.agent_settings import harness_hooks

ROOT = Path(__file__).resolve().parents[1]
#: The rule in miniature, written against the contract page and nothing else.
ASK_FIRST = '''\
import json, re, sys
from pathlib import Path

event = json.loads(sys.stdin.read() or "{}")
record = Path(__file__).parent / "asked.json"
asked = json.loads(record.read_text(encoding="utf-8")) if record.is_file() else []
who = f"{event.get('session')}:{event.get('agent', 'host')}"
if event.get("point") == "tool-use":
    record.write_text(json.dumps(sorted({*asked, who})), encoding="utf-8")
    sys.exit(0)
documents = event.get("path", "").startswith(("specs/", "docs/")) or event.get("glob", "").endswith(".md")
symbol = re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", event.get("pattern", ""))
if event.get("tool") != "Grep" or who in asked or documents or not symbol:
    sys.exit(0)
print(f"ask the index first: codegraph explore {event['pattern']}", file=sys.stderr)
sys.exit(2)
'''
DECLARED = {"before-search": {"run": "guards/ask_first.py", "budget": "30s", "sees": ["mcp__index__.*"]}}


def grep(session: str = "s-1", **searched: str) -> dict:
    return {"session_id": session, "cwd": "/work/project", "hook_event_name": "PreToolUse", "tool_name": "Grep",
            "tool_input": {"pattern": "place_order", **searched}}


def asks(session: str = "s-1", tool: str = "mcp__index__explore") -> dict:
    return {"session_id": session, "cwd": "/work/project", "hook_event_name": "PreToolUse", "tool_name": tool,
            "tool_input": {"query": "who calls place_order", "secret": "not-for-a-guard"}}


class Elected(unittest.TestCase):
    def setUp(self) -> None:
        self.project = Project()
        self.addCleanup(self.project.close)
        settings = self.project.root / ".claude/settings.json"
        settings.parent.mkdir()
        settings.write_text(json.dumps({"permissions": {"allow": []}, "hooks": harness_hooks(AT_ROOT)},
                                       indent=2) + "\n", encoding="utf-8")
        self.settings, self.written = settings, settings.read_bytes()
        self.project.extension("index", DECLARED, **{"guards/ask_first.py": ASK_FIRST})
        self.project.elected("index")
        self.project.guards("--elect", "index")

    def rows(self) -> list[dict]:
        return json.loads(self.settings.read_text(encoding="utf-8"))["hooks"]["PreToolUse"]


class CodegraphInMiniatureTest(Elected):
    def test_a_symbol_grep_of_the_source_is_refused_before_the_index_was_asked(self) -> None:
        done = self.project.session("before-search", grep(path="apps/"))
        self.assertEqual(done.returncode, 2)
        self.assertIn("ask the index first: codegraph explore place_order", done.stderr)

    def test_the_same_grep_is_allowed_once_the_session_used_the_declared_tool(self) -> None:
        self.assertEqual(self.project.session("before-search", grep(path="apps/")).returncode, 2)
        self.assertEqual(self.project.session("tool-use", asks()).returncode, 0)
        self.assertEqual(self.project.session("before-search", grep(path="apps/")).returncode, 0)

    def test_a_grep_under_specs_is_never_refused(self) -> None:
        self.assertEqual(self.project.session("before-search", grep(path="specs/001-orders")).returncode, 0)
        self.assertEqual(self.project.session("before-search", grep(glob="*.md")).returncode, 0)

    def test_a_glob_is_never_refused(self) -> None:
        done = self.project.session("before-search", {"session_id": "s-1", "cwd": "/work/project",
                                                      "tool_name": "Glob",
                                                      "tool_input": {"pattern": "place_order"}})
        self.assertEqual(done.returncode, 0)

    def test_another_session_is_still_refused(self) -> None:
        self.project.session("tool-use", asks("s-1"))
        self.assertEqual(self.project.session("before-search", grep("s-1")).returncode, 0)
        self.assertEqual(self.project.session("before-search", grep("s-2")).returncode, 2)

    def test_a_sub_agent_that_has_not_asked_is_refused_inside_a_session_that_has(self) -> None:
        self.project.session("tool-use", asks("s-1"))
        delegate = {**grep("s-1"), "agent_id": "a-7"}
        self.assertEqual(self.project.session("before-search", delegate).returncode, 2)
        self.project.session("tool-use", {**asks("s-1"), "agent_id": "a-7"})
        self.assertEqual(self.project.session("before-search", delegate).returncode, 0)


class SeeingIsNotJudgingTest(Elected):
    def test_a_guard_cannot_refuse_the_tool_it_is_told_about(self) -> None:
        """A guard written before any of this exits 2 at whatever it is run for. Told about its own tool,
        it has refused nothing: the ask goes ahead, and nothing it printed is sent back as a refusal."""
        (self.project.extensions / "index/guards/ask_first.py").write_text(
            "import sys\nprint('no', file=sys.stderr)\nsys.exit(2)\n", encoding="utf-8")
        done = self.project.session("tool-use", asks())
        self.assertEqual(done.returncode, 0)
        self.assertIn("cannot refuse", done.stderr)

    def test_a_tool_it_did_not_declare_is_not_shown_to_it(self) -> None:
        for tool in ("mcp__other__explore", "Bash", "Edit", "mcp__index"):
            with self.subTest(tool=tool):
                self.project.session("tool-use", asks(tool=tool))
                self.assertEqual(self.project.session("before-search", grep()).returncode, 2)

    def test_it_is_told_which_tool_and_whose_call_and_not_what_was_asked(self) -> None:
        """The arguments of somebody's MCP call are not a search, and may hold anything. A guard that sees
        a tool used is told the tool's name and who used it."""
        probe = ("import json, sys\nfrom pathlib import Path\n"
                 "(Path(__file__).parent / 'saw.json').write_text(sys.stdin.read(), encoding='utf-8')\n")
        (self.project.extensions / "index/guards/ask_first.py").write_text(probe, encoding="utf-8")
        self.project.session("tool-use", {**asks(), "agent_id": "a-7"}, SLIPWAI_STAGE="implement")
        saw = json.loads((self.project.extensions / "index/guards/saw.json").read_text(encoding="utf-8"))
        self.assertEqual(saw, {"v": 1, "point": "tool-use", "tool": "mcp__index__explore",
                               "cwd": "/work/project", "session": "s-1", "agent": "a-7", "stage": "implement"})

    def test_a_guard_nobody_agreed_to_sees_nothing(self) -> None:
        self.project.guards("--remove", "index")
        self.project.session("tool-use", asks())
        self.assertFalse((self.project.extensions / "index/guards/asked.json").exists())

    def test_a_registry_edited_to_see_everything_shows_it_nothing(self) -> None:
        """The limit is held where a guard is run as well as where a manifest is read: the registry is a
        file, and a pattern put into it by hand is still not one an extension may declare."""
        written = json.loads(self.project.registry.read_text(encoding="utf-8"))
        written["guards"]["before-search"][0]["sees"] = [".*", "Bash", "mcp__.*"]
        self.project.registry.write_text(json.dumps(written), encoding="utf-8")
        self.project.session("tool-use", asks(tool="Bash"))
        self.project.session("tool-use", asks())
        self.assertFalse((self.project.extensions / "index/guards/asked.json").exists())


class LimitTest(unittest.TestCase):
    """What may be declared: one MCP server's tools, by name or all of that server's. Nothing wider."""

    def declared(self, *sees: object) -> dict:
        return guards.declared({"guards": {"before-search": {"run": "g.py", "sees": list(sees)}}})

    def test_one_servers_tools_are_declared_by_name_or_all_of_them(self) -> None:
        self.assertEqual(self.declared("mcp__codegraph__.*", "mcp__chrome-devtools__click")["before-search"]["sees"],
                         ["mcp__codegraph__.*", "mcp__chrome-devtools__click"])

    def test_the_allow_lists_spelling_is_read_as_the_same_thing(self) -> None:
        """`tools` says `mcp__codegraph__*`, and whoever copies it down a line meant the same tools."""
        self.assertEqual(self.declared("mcp__codegraph__*")["before-search"]["sees"], ["mcp__codegraph__.*"])

    def test_nothing_that_could_match_another_kind_of_call_is_accepted(self) -> None:
        for pattern in (".*", "*", "Bash", "Grep|mcp__codegraph__.*", "mcp__.*", "mcp__codegraph__.*|Edit",
                        "mcp__codegraph__(a|.*)", "mcp__codegraph__", "(?i)mcp__codegraph__x", "", 7):
            with self.subTest(pattern=pattern), self.assertRaises(ValueError) as refused:
                self.declared(pattern)
            self.assertIn("mcp__<server>__", str(refused.exception))

    def test_a_guard_sees_only_so_many(self) -> None:
        self.declared(*(f"mcp__s{index}__.*" for index in range(guards.SEES_LIMIT)))
        with self.assertRaises(ValueError):
            self.declared(*(f"mcp__s{index}__.*" for index in range(guards.SEES_LIMIT + 1)))

    def test_a_guard_that_declares_none_is_what_it_was(self) -> None:
        self.assertEqual(guards.declared({"guards": {"before-search": "g.py"}}),
                         {"before-search": {"run": "g.py", "budget": guards.DEFAULT_BUDGET}})


class ContractTest(unittest.TestCase):
    """The page, the keel's list and the script that builds the event name the same fields."""

    def test_the_page_lists_exactly_what_a_guard_that_sees_a_tool_is_handed(self) -> None:
        page = (ROOT / "docs/extensions.md").read_text(encoding="utf-8")
        table = page.split("### A guard can see its extension's own tools used", 1)[1].split("So one script", 1)[0]
        source = (TOOLKIT / "scripts/agents/tool_event.py").read_text(encoding="utf-8")
        built = re.search(r"^USED = (\[.*?\])$", source, re.MULTILINE | re.DOTALL)
        assert built is not None
        self.assertEqual(re.findall(r"^\| `([a-z_]+)` \|", table, re.MULTILINE), list(guards.TOOL_USE_EVENT))
        self.assertEqual(json.loads(built.group(1)), list(guards.TOOL_USE_EVENT))

    def test_the_runner_and_the_projection_hold_the_limit_the_keel_does(self) -> None:
        for script in ("guards.py", "guard_harness.py"):
            source = (TOOLKIT / "scripts/extensions" / script).read_text(encoding="utf-8")
            with self.subTest(script=script):
                self.assertIn(f'SEES = re.compile(r"{guards.SEES.pattern}")', source)
                self.assertIn(f"SEES_LIMIT = {guards.SEES_LIMIT}", source)


class HarnessMatcherTest(Elected):
    """Claude Code runs a hook for the tools its matcher names, so the row is written from the agreement."""

    def seen(self) -> list[dict]:
        return [row for row in self.rows() if str(row["hooks"][0]["command"]).endswith("session.py tool-use")]

    def test_agreeing_writes_one_row_matching_exactly_what_was_declared(self) -> None:
        (row,) = self.seen()
        self.assertEqual(row["matcher"], "mcp__index__.*")
        self.assertEqual(row["hooks"][0]["command"],
                         "python3 $CLAUDE_PROJECT_DIR/scripts/agents/session.py tool-use")
        self.assertEqual([one for one in self.rows() if one not in self.seen()],
                         harness_hooks(AT_ROOT)["PreToolUse"])

    def test_agreeing_again_changes_nothing(self) -> None:
        before = self.settings.read_bytes()
        self.project.guards("--elect", "index")
        self.assertEqual(self.settings.read_bytes(), before)

    def test_two_guards_share_the_row_and_removing_one_narrows_it(self) -> None:
        self.project.extension("other", {"before-write": {"run": "g.py", "sees": ["mcp__other__read"]}})
        self.project.guards("--elect", "other")
        self.assertEqual(self.seen()[0]["matcher"], "mcp__index__.*|mcp__other__read")
        self.project.guards("--remove", "index")
        self.assertEqual(self.seen()[0]["matcher"], "mcp__other__read")

    def test_with_nothing_left_to_see_the_file_is_what_the_keel_wrote(self) -> None:
        self.project.guards("--remove", "index")
        self.assertEqual(self.settings.read_bytes(), self.written)

    def test_a_project_with_no_such_file_is_not_given_one(self) -> None:
        self.settings.unlink()
        self.assertEqual(self.project.guards("--elect", "index").returncode, 0)
        self.assertFalse(self.settings.exists())

    def test_settings_nobody_can_read_are_left_alone_and_the_agreement_still_stands(self) -> None:
        self.settings.write_text("{ not json", encoding="utf-8")
        done = self.project.guards("--elect", "index")
        self.assertEqual(done.returncode, 0)
        self.assertEqual(self.settings.read_text(encoding="utf-8"), "{ not json")
        self.assertEqual(self.project.agreed(), {"before-search": ["index"]})


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
