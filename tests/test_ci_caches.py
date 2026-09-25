"""What `verify.yml` caches, and that each cache is keyed on a file the project actually has.

A cache keyed on a missing file is the quiet kind of failure: the setup action warns, restores nothing,
saves nothing, and the run stays green — only slower, on every run, for as long as nobody reads the warning.
"""
from __future__ import annotations

from support import FactoryTestCase
from test_services import with_payments

from slipwai.project.ci_workflows import workflow
from slipwai.services import default_apps


class CiCachesTest(FactoryTestCase):
    def test_setup_go_keys_on_every_module_and_the_workspace_because_a_workspace_has_no_root_go_sum(self) -> None:
        """`actions/setup-go` keys on `./go.sum` unless told otherwise, and a Go project here is a workspace:
        `go.work` and `go.work.sum` at the root, each module's `go.sum` beside its `go.mod`."""
        one = workflow(default_apps("go", "none"))
        self.assertIn(
            "      - uses: actions/setup-go@v7\n        with:\n          go-version-file: apps/service/go.mod\n"
            "          cache-dependency-path: |\n            apps/service/go.sum\n            go.work.sum\n",
            one,
        )
        files, _ = with_payments("go", http="net-http")
        self.assertNotIn("go.sum", [path for path in files if "/" not in path], "a workspace keeps no root go.sum")
        self.assertIn("apps/service/go.sum", files)
        self.assertIn(
            "          cache-dependency-path: |\n            apps/service/go.sum\n            apps/payments/go.sum\n"
            "            go.work.sum\n",
            files[".github/workflows/verify.yml"],
        )
