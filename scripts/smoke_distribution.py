"""Smoke the installed keel outside its checkout, without bundling a language package.

Published package generation is the release backstop's separate gate. These checks prove that the keel's
own UTF-8 material and dynamically loaded helpers survive either distribution format.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path


def smoke(command: list[str], expected: str) -> dict[str, str]:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temporary:
        root = Path(temporary)
        environment = {**os.environ, "PYTHONPATH": "", "SLIPWAI_LANGUAGES": str(root / "packages")}

        def run(*arguments: str, cwd: Path = root) -> str:
            done = subprocess.run([*command, *arguments], cwd=cwd, env=environment,
                                  capture_output=True, text=True, timeout=120)
            if done.returncode:
                raise RuntimeError(f"{' '.join(arguments)} failed: {done.stdout}{done.stderr}")
            return done.stdout

        if run("--version").strip() != f"slipwai {expected}":
            raise RuntimeError("the installed command's version differs from VERSION")
        plugin = root / "plugin"
        run("package", "plugin", str(plugin))
        if not (plugin / "commands/sail.md").is_file():
            raise RuntimeError("the packaged toolkit is incomplete. Run: make test-wheel test-executable")
        harness = root / "native"
        run("package", "harness", str(harness), "--harness", "codex")
        if not (harness / ".agents/skills/sail/SKILL.md").is_file():
            raise RuntimeError("the packaged native renderer is incomplete. Run: make test-wheel test-executable")
        existing = root / "existing"
        existing.mkdir()
        source = 'def greet():\n    return "harbour — ✓"\n'
        (existing / "pyproject.toml").write_text('[project]\nname="existing"\nversion="0.1.0"\n', encoding="utf-8")
        (existing / "app.py").write_text(source, encoding="utf-8")
        subprocess.run(["git", "init", "--quiet", str(existing)], check=True, capture_output=True)
        run("adopt", "--yes", cwd=existing)
        manifest = json.loads((existing / "project.json").read_text(encoding="utf-8"))
        delivery = existing / manifest.get("layout", {}).get("delivery", ".")
        if not (delivery / "skills/tdd/SKILL.md").is_file():
            raise RuntimeError("the packaged adoption toolkit is incomplete. Run: make test-wheel test-executable")
        if (existing / "app.py").read_text(encoding="utf-8") != source:
            raise RuntimeError("adoption changed existing application code")
    print("distribution smoke: version, plugin, native command skills and UTF-8 adoption passed")
    return dict.fromkeys(("version", "plugin", "native", "adoption"), "passed")
