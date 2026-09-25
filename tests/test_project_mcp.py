"""An extension's MCP server travels with the checkout: `scripts/extensions/guidance.py`'s one writer names it in the
project-scoped file of every harness installed here, in the shape the registry's `projectMcp` column gives that
harness, merging into what a person already configured and leaving alone what it cannot parse."""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase
from test_extensions import CODEX_TABLE, FAKE_SPECIFY, SERVER


class ProjectMcpTest(FactoryTestCase):
    def test_the_server_is_named_in_every_installed_harness_file_and_each_file_is_a_merge_target(self) -> None:
        """One writer, four shapes: Claude Code's, Gemini's and Cursor's `mcpServers`, opencode's `mcp` with the command
        as one array, Codex's TOML table. A file the user hand-edits is merged, never replaced (docs/extensions.md,
        6): a server they configured stays, a second run rewrites nothing, and a file that cannot be parsed is left
        alone and said. A harness with no known file is named with the reason, and reaches the index by CLI."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "codegraph-merge")
            fake_bin = Path(directory) / "fake-bin"
            fake_bin.mkdir()
            (fake_bin / "specify").write_text(FAKE_SPECIFY)
            (fake_bin / "specify").chmod(0o755)
            (fake_bin / "codegraph").write_text("#!/bin/sh\nexit 0\n")
            (fake_bin / "codegraph").chmod(0o755)
            environment = os.environ | {"PATH": f"{fake_bin}:{os.environ['PATH']}"}
            (repo / ".specify").mkdir(exist_ok=True)
            (repo / ".specify/integration.json").write_text(json.dumps(
                {"installed_integrations": ["claude", "gemini", "opencode", "cursor-agent", "copilot"]}))
            docs = {"type": "http", "url": "https://docs.example/mcp"}
            (repo / ".mcp.json").write_text(json.dumps({"mcpServers": {"docs": docs}, "note": "kept"}))
            (repo / "opencode.jsonc").write_text('{\n  // mine\n  "mcp": {}\n}\n')
            (repo / ".codex").mkdir()
            (repo / ".codex/config.toml").write_text(
                'model = "gpt-6"\n\n[mcp_servers.docs]\ncommand = "docs-mcp"\n\n[mcp_servers.codegraph]\n'
                'command = "codegraph"\nargs = ["serve", "--mcp"]\n\n[profiles.fast]\nmodel = "gpt-6-mini"\n')
            adopt = ["./init", "--integration", "codex", "--extension", "codegraph"]
            said = subprocess.run(adopt, cwd=repo, check=True, env=environment, capture_output=True, text=True)
            self.assertEqual(json.loads((repo / ".mcp.json").read_text()),
                             {"mcpServers": {"docs": docs, "codegraph": {**SERVER, "alwaysLoad": True}},
                              "note": "kept"})
            # Claude Code's entry alone carries `alwaysLoad`: the registry row's `serverFields`, so a delegate is
            # given the tool at session start rather than a bare name to load first; the other files are unchanged.
            self.assertEqual(json.loads((repo / ".gemini/settings.json").read_text()),
                             {"mcpServers": {"codegraph": SERVER}})
            self.assertEqual(json.loads((repo / ".cursor/mcp.json").read_text()), {"mcpServers": {"codegraph": SERVER}})
            self.assertEqual((repo / ".codex/config.toml").read_text(),
                             'model = "gpt-6"\n\n[mcp_servers.docs]\ncommand = "docs-mcp"\n\n' + CODEX_TABLE
                             + '\n[profiles.fast]\nmodel = "gpt-6-mini"\n')
            # opencode's `.jsonc` is the person's and cannot be merged without parsing its comments: left, and said.
            self.assertEqual((repo / "opencode.jsonc").read_text(), '{\n  // mine\n  "mcp": {}\n}\n')
            self.assertFalse((repo / "opencode.json").exists())
            self.assertIn("codegraph: opencode: opencode.jsonc is not a JSON object (comments, perhaps); left as it is",
                          said.stdout)
            self.assertIn("codegraph: GitHub Copilot: no project MCP file is known for it, so it reaches `codegraph` "
                          "through the CLI — the Copilot CLI reads MCP servers from `~/.copilot/mcp-config.json` only",
                          said.stdout)
            self.assertIn("codegraph: Claude Code: .mcp.json names `codegraph`; commit it", said.stdout)
            self.assertIn("codegraph: Codex CLI: .codex/config.toml names `codegraph`; commit it", said.stdout)
            before = {path: path.stat().st_mtime_ns for path in (repo / ".mcp.json", repo / ".codex/config.toml",
                                                                    repo / ".gemini/settings.json")}
            again = subprocess.run(adopt, cwd=repo, check=True, env=environment, capture_output=True, text=True)
            for path, stamp in before.items():
                self.assertEqual(path.stat().st_mtime_ns, stamp, f"{path.name}: a second run rewrites nothing")
            self.assertNotIn("commit it", again.stdout)
            (repo / ".mcp.json").write_text("{not json")
            said = subprocess.run(adopt, cwd=repo, check=True, env=environment, capture_output=True, text=True)
            self.assertEqual((repo / ".mcp.json").read_text(), "{not json")
            self.assertIn("codegraph: Claude Code: .mcp.json is not a JSON object (comments, perhaps); left as it is",
                          said.stdout)
