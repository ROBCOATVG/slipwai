"""The same material, laid out where each harness reads it, from the rows `registry.json` already holds.

The risk the whole phase carries is that the keel ships a manifest per harness and is then edited whenever
any of thirty-six changes its mind. So this is one renderer reading one row, and what it proves is that
adding a harness is a row: the test that matters walks every harness the registry knows and holds each to
its own declaration, rather than naming two and hoping.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import native, plugin
from slipwai.harness import keys as harness_keys
from slipwai.harness import row_of


class EveryHarnessTest(unittest.TestCase):
    """Thirty-six rows, one renderer, and nothing per-harness anywhere but the row."""

    def test_every_harness_the_registry_knows_renders(self) -> None:
        for key in harness_keys():
            with self.subTest(harness=key):
                native.files(key)

    def test_nothing_lands_outside_the_locations_its_row_declares(self) -> None:
        """A file at a path the registry did not name is the keel having an opinion of its own."""
        for key in harness_keys():
            row = row_of(key)
            declared = [str(row[field]) for field in ("skillsDir", "commandsDir")
                        if isinstance(row.get(field), str)]
            agent_row = row.get("agentFile")
            if isinstance(agent_row, dict) and isinstance(agent_row.get("dir"), str):
                declared.append(str(agent_row["dir"]))
            mcp = row.get("projectMcp")
            if isinstance(mcp, dict):
                declared.append(str(mcp["file"]))
            for path in native.files(key):
                with self.subTest(harness=key, path=path):
                    self.assertTrue(any(path == place or path.startswith(f"{place}/") for place in declared),
                                    f"{path} is under nothing {key}'s row declares")

    def test_a_harness_the_registry_has_not_got_is_refused_by_name(self) -> None:
        with self.assertRaises(Exception) as caught:
            native.files("claude-code")
        self.assertIn("claude-code", str(caught.exception))

    def test_every_harness_says_what_it_could_not_be_given(self) -> None:
        """A gap written down is a gap somebody can read; a gap left out is one the next person assumes
        the harness is holding."""
        for key in harness_keys():
            row = row_of(key)
            with self.subTest(harness=key):
                said = native.unplaceable(key)
                if not isinstance(row.get("projectMcp"), dict):
                    self.assertTrue(any("MCP" in line for line in said), said)


class CodexTest(unittest.TestCase):
    """The harness the slice names: its prompts directory and its MCP configuration."""

    rendered: dict[str, str]

    @classmethod
    def setUpClass(cls) -> None:
        cls.rendered = native.files("codex")

    def test_the_commands_land_in_codexs_prompts_directory(self) -> None:
        self.assertIn(".codex/prompts/sail.md", self.rendered)

    def test_the_skills_land_where_codex_reads_skills(self) -> None:
        self.assertTrue(any(path.startswith(".agents/skills/tdd/") for path in self.rendered))

    def test_a_command_is_the_same_file_the_plugin_carries(self) -> None:
        """Bar the argument placeholder, which is the one thing the row says differs."""
        self.assertEqual(self.rendered[".codex/prompts/sail.md"],
                         plugin.files()["commands/sail.md"])

    def test_its_mcp_configuration_names_the_servers_command(self) -> None:
        found = self.rendered[".codex/config.toml"]
        self.assertIn(f"[mcp_servers.{native.SERVER}]", found)
        self.assertIn('"mcp"', found)

    def test_every_format_the_registry_declares_is_one_this_renders(self) -> None:
        """The direction that would fail silently: a harness whose project MCP file this cannot spell
        would get no configuration at all, and nothing would say so."""
        declared = {str(row_of(key)["projectMcp"]["format"]) for key in harness_keys()
                    if isinstance(row_of(key).get("projectMcp"), dict)}
        self.assertEqual(sorted(declared), sorted(native.FORMATS))


class ClaudeTest(unittest.TestCase):
    """Claude Code is a row like the rest here, even though 12.1 gives it a plugin of its own."""

    rendered: dict[str, str]

    @classmethod
    def setUpClass(cls) -> None:
        cls.rendered = native.files("claude")

    def test_the_commands_land_where_claude_code_reads_commands(self) -> None:
        self.assertIn(".claude/commands/sail.md", self.rendered)

    def test_its_mcp_configuration_is_json_naming_the_server(self) -> None:
        found = json.loads(self.rendered[".mcp.json"])
        self.assertIn(native.SERVER, found["mcpServers"])
        self.assertIn("mcp", found["mcpServers"][native.SERVER]["args"])


class PlaceholderTest(unittest.TestCase):
    """`$ARGUMENTS` is the canonical spelling and each row says what that harness calls it."""

    def test_no_harness_is_handed_a_placeholder_its_row_does_not_use(self) -> None:
        source = {path: text for path, text in plugin.files().items() if path.startswith("commands/")}
        for key in harness_keys():
            row = row_of(key)
            rendered = native.commands_of(source, row)
            if not rendered:
                continue
            with self.subTest(harness=key):
                placeholder = row.get("argPlaceholder") or "$ARGUMENTS"
                if placeholder != "$ARGUMENTS":
                    self.assertFalse(any("$ARGUMENTS" in text for text in rendered.values()))

    def test_a_harness_whose_commands_are_not_markdown_is_given_none_and_told_why(self) -> None:
        """Gemini's are TOML and Goose's are YAML; `./init` renders those inside a project, where there is
        one spelling of a command and not two."""
        for key in ("gemini", "goose", "tabnine"):
            with self.subTest(harness=key):
                self.assertEqual(native.commands_of({"commands/sail.md": "x"}, row_of(key)), {})
                self.assertTrue(any("markdown commands" in line for line in native.unplaceable(key)))


class WrittenTest(unittest.TestCase):
    """What `slipwai package harness` leaves on disk."""

    def test_it_writes_every_rendered_file_under_the_directory_it_was_given(self) -> None:
        into = Path(tempfile.mkdtemp()) / "codex"
        written = native.write("codex", into)
        self.assertEqual(sorted(written), sorted(native.files("codex")))
        self.assertTrue((into / ".codex/prompts/sail.md").is_file())


if __name__ == "__main__":
    unittest.main()
