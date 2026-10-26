"""The gate refuses what a decided strategy forbids before it happens, rather than warning after."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

import checkout_packages  # noqa: F401

from slipwai.assets import ADOPTION_ROOT, TOOLKIT_ROOT

IDENTITY = ["-c", "user.name=t", "-c", "user.email=t@example.com"]


def script(name: str, path: Path) -> Any:
    """An adopted repository's script, loaded as a module."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def gate(root: Path) -> Any:
    """The adopted repository's `check-convergence`, pointed at `root`."""
    module = script("check_convergence", ADOPTION_ROOT / "scripts/check-convergence.py")
    module.ROOT, module.DELIVERY, module.LEDGER = root, root / "adopt", root / "adopt/retirement.md"
    return module


def strangler(**lines: str) -> dict:
    return {"decided": "strangler-fig", "adr": "adopt/docs/adr/0002-strategy.md", "missing": [],
            "lines": {"New home": "beside apps/shop-next", "End": "partial", **lines}}


class GateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        (self.root / "adopt/docs/adr").mkdir(parents=True)
        self.old = {"shop": {"path": "web", "generated": False, "kind": "service"}}

    def git(self, *args: str) -> None:
        subprocess.run(["git", *IDENTITY, *args], cwd=self.root, check=True, capture_output=True)

    def test_no_feature_is_specified_before_the_new_home_exists(self) -> None:
        (self.root / "specs/001-panel").mkdir(parents=True)
        (self.root / "specs/001-panel/spec.md").write_text("# spec")
        document = {"strategy": strangler(), "deployables": self.old}
        self.assertIn("before the new home exists", " ".join(gate(self.root).strategy_gaps(document)))
        home = {**self.old, "shop-next": {"path": "apps/shop-next", "kind": "service"}}
        self.assertEqual(gate(self.root).strategy_gaps({"strategy": strangler(), "deployables": home}), [],
                         "a generated deployable carries no `generated` key, and is the new home")

    def test_a_rewrite_in_a_new_repository_specifies_nothing_here(self) -> None:
        (self.root / "specs/001-panel").mkdir(parents=True)
        (self.root / "specs/001-panel/spec.md").write_text("# spec")
        rewrite = {"decided": "rewrite", "missing": [], "lines": {"Home": "new-repo ../shop-rewrite"}}
        self.assertIn("built in a new repository", " ".join(
            gate(self.root).strategy_gaps({"strategy": rewrite, "deployables": self.old})))

    def test_the_old_code_changes_only_with_a_reason_once_the_strategy_is_decided(self) -> None:
        self.git("init", "-q")
        (self.root / "web").mkdir()
        (self.root / "web/home.jsp").write_text("<html/>\n")
        (self.root / "adopt/docs/adr/0002-strategy.md").write_text("Strategy: strangler-fig\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "Decide the change strategy")
        document = {"strategy": strangler(), "deployables": self.old}
        with (self.root / "web/home.jsp").open("a") as page:
            page.write("<!-- the panel -->\n")
        self.git("commit", "-qam", "Add the panel to the home page")
        said = " ".join(gate(self.root).strategy_gaps(document))
        self.assertIn("without a `Legacy-change:` trailer", said)
        self.git("commit", "-q", "--amend", "-m", "Include the panel from the new home", "-m", "Legacy-change: seam")
        self.assertEqual(gate(self.root).legacy_changes(document, document["strategy"]), [])

    def test_a_capability_moves_only_after_it_was_shadowed_and_transitional_pieces_hold_the_end(self) -> None:
        ledger = self.root / "adopt/retirement.md"
        ledger.write_text(
            "| Date | Capability | From | To | Routed by | Pinned by | Status |\n|---|---|---|---|---|---|---|\n"
            "| 2026-10-01 | orders | web | apps/next | proxy | t1 | *routed* |\n"
            "| 2026-10-05 | orders | web | apps/next | proxy | t1 | *moved* |\n")
        self.assertIn("no `shadowed` row", " ".join(gate(self.root).ledger_gaps()))
        ledger.write_text(
            "| Date | Capability | From | To | Routed by | Pinned by | Status |\n|---|---|---|---|---|---|---|\n"
            "| 2026-10-01 | orders | web | apps/next | proxy | t1 | *routed* |\n"
            "| 2026-10-03 | orders | web | apps/next | proxy | t1 | *shadowed* |\n"
            "| 2026-10-05 | orders | web | apps/next | proxy | t1 | *removed* |\n"
            "\n| Date | Piece | Why | Remove when | Status |\n|---|---|---|---|---|\n"
            "| 2026-10-01 | include in home.jsp | the panel | home moves | *live* |\n")
        self.assertEqual(gate(self.root).ledger_gaps(), [])
        self.assertFalse(gate(self.root).ledger_finished(), "a live include is the old home still serving")

    def test_a_left_system_past_its_review_fails(self) -> None:
        left = {"decided": "leave-it", "missing": [], "lines": {"Review": "2001-01-01"}}
        self.assertIn("that date has passed", " ".join(gate(self.root).strategy_gaps({"strategy": left})))


class ToolTest(unittest.TestCase):
    def test_the_missing_tool_is_named_not_the_directory_it_runs_in(self) -> None:
        ratchet = script("ratchet", ADOPTION_ROOT / "scripts/ratchet.py")
        self.assertEqual(ratchet.tool_of("cd MyApp && ant -q compile"), "ant")
        self.assertEqual(ratchet.tool_of("CI=1 npm test"), "npm")

    def test_a_modular_layout_holds_the_context_rule_without_the_layer_rules(self) -> None:
        root = Path(tempfile.mkdtemp())
        (root / "scripts").mkdir()
        (root / "scripts/check-imports.py").write_text(
            (TOOLKIT_ROOT / "scripts/check-imports.py").read_text(encoding="utf-8"), encoding="utf-8")
        (root / "project.json").write_text(json.dumps({"deployables": {"shop": {
            "path": "web", "kind": "service", "generated": False, "layout": "modular",
            "contexts": ["orders", "billing"]}}}))
        orders = root / "web/src/com/shop/orders/domain"
        orders.mkdir(parents=True)
        (orders / "Order.java").write_text("import com.shop.billing.domain.Invoice;\nimport com.shop.adapters.Db;\n")
        ran = subprocess.run([sys.executable, str(root / "scripts/check-imports.py")], capture_output=True, text=True)
        self.assertEqual(ran.returncode, 1)
        self.assertIn("orders reaches into billing", ran.stderr)
        self.assertNotIn("outer layer", ran.stderr, "modular is the context rule, not the layer rules")


if __name__ == "__main__":
    unittest.main()
