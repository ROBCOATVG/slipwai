"""Every text file slipwai or a generated project's scripts open is UTF-8, and every one they write is LF.

Without an `encoding`, Python opens a file in the locale's encoding, which is UTF-8 on macOS and Linux and
cp1252 on Windows — so the first run of `slipwai generate` in PowerShell died reading its own skill files
(`UnicodeDecodeError: 'charmap' codec can't decode byte 0x9d`, `toolkit.py`), and worked the moment
`PYTHONUTF8=1` was set. Every file here is UTF-8, so every call says so. Held on the package, on the Python
a generated project ships (`assets/`, which `./init` and `make verify` run on the person's machine) and on
the factory's own scripts. Binary modes are left alone, and so is a mode that is not a literal, which this
cannot judge — the few there are open URLs, not files.

The same Windows run then showed the other half: with no `newline`, a text-mode write turns every `\n` into
`\r\n`. The pruner `generate` runs rewrote its files that way, so the tree on disk was CRLF — `./init`
included, which Git Bash then cannot run — while the root `.gitattributes` had Git store LF, hence "CRLF will
be replaced by LF" per file. Every text-mode write says `newline="\n"`; reading needs nothing, because a read
already takes either ending.
"""
from __future__ import annotations

import ast
from collections.abc import Callable

from support import FactoryTestCase

from slipwai.assets import ROOT

TEXT_METHODS = {"read_text": 0, "write_text": 1}
NOT_FILES = {"webbrowser", "os", "tarfile", "zipfile", "gzip", "io"}


def unencoded(call: ast.Call) -> bool:
    """Whether `call` opens a text file in the locale's encoding."""
    if any(keyword.arg in ("encoding", None) for keyword in call.keywords):
        return False
    func = call.func
    if isinstance(func, ast.Attribute) and func.attr in TEXT_METHODS:
        return len(call.args) <= TEXT_METHODS[func.attr]
    builtin = isinstance(func, ast.Name) and func.id == "open"
    method = isinstance(func, ast.Attribute) and func.attr == "open" and not (
        isinstance(func.value, ast.Name) and func.value.id in NOT_FILES
    )
    if not (builtin or method) or len(call.args) > (3 if builtin else 2):
        return False
    index = 1 if builtin else 0
    mode = next((keyword.value for keyword in call.keywords if keyword.arg == "mode"), None)
    if mode is None and len(call.args) > index:
        mode = call.args[index]
    if mode is None:
        return True
    return isinstance(mode, ast.Constant) and isinstance(mode.value, str) and "b" not in mode.value


def translated(call: ast.Call) -> bool:
    """Whether `call` writes a text file with the platform's line ending, which is CRLF on Windows."""
    if any(keyword.arg in ("newline", None) for keyword in call.keywords):
        return False
    func = call.func
    if isinstance(func, ast.Attribute) and func.attr == "write_text":
        return len(call.args) <= 3
    builtin = isinstance(func, ast.Name) and func.id == "open"
    method = isinstance(func, ast.Attribute) and func.attr == "open" and not (
        isinstance(func.value, ast.Name) and func.value.id in NOT_FILES
    )
    if not (builtin or method) or len(call.args) > (4 if builtin else 3):
        return False
    index = 1 if builtin else 0
    mode = next((keyword.value for keyword in call.keywords if keyword.arg == "mode"), None)
    if mode is None and len(call.args) > index:
        mode = call.args[index]
    if not (isinstance(mode, ast.Constant) and isinstance(mode.value, str)):
        return False
    return "b" not in mode.value and any(flag in mode.value for flag in "wax+")


def calls(check: Callable[[ast.Call], bool]) -> list[str]:
    """Every call in the shipped and factory Python that `check` finds, as `path:line`."""
    found: list[str] = []
    for tree in ("src/slipwai", "assets", "scripts"):
        for path in sorted((ROOT / tree).rglob("*.py")):
            try:
                module = ast.parse(path.read_text(encoding="utf-8"))
            except SyntaxError:
                continue  # a template with markers in it, which is not Python until it is generated
            found.extend(
                f"{path.relative_to(ROOT)}:{node.lineno}"
                for node in ast.walk(module)
                if isinstance(node, ast.Call) and check(node)
            )
    return found


class Utf8IoTest(FactoryTestCase):
    def test_every_text_file_is_opened_as_utf8(self) -> None:
        self.assertEqual(calls(unencoded), [], "opened without encoding=\"utf-8\", which is cp1252 on Windows")

    def test_every_text_file_is_written_with_lf(self) -> None:
        self.assertEqual(calls(translated), [], "written without newline=\"\\n\", which is CRLF on Windows")

    def test_the_check_would_catch_the_call_that_broke_windows(self) -> None:
        call = ast.parse("declared_for(source.read_text())").body[0].value.args[0]  # type: ignore[attr-defined]
        self.assertTrue(unencoded(call))
        self.assertFalse(unencoded(ast.parse('p.read_text(encoding="utf-8")').body[0].value))  # type: ignore[attr-defined]
        self.assertFalse(unencoded(ast.parse('open(p, "rb")').body[0].value))  # type: ignore[attr-defined]
        self.assertTrue(translated(ast.parse('path.write_text("".join(kept), encoding="utf-8")').body[0].value))  # type: ignore[attr-defined]
        self.assertFalse(translated(ast.parse('p.write_text(t, encoding="utf-8", newline="\\n")').body[0].value))  # type: ignore[attr-defined]
        self.assertFalse(translated(ast.parse('open(p, encoding="utf-8")').body[0].value))  # type: ignore[attr-defined]
