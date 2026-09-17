"""Go's ko-built migrate image must carry its .sql files inside the binary.

ko ships a compiled binary and nothing else. A runtime filesystem glob matched nothing *even when
the repository had .sql files*, exited 0, and left freshly created databases empty behind green
deploys. Embedding closes that. An empty *.sql set remains legitimate (Minimum CD may ship before
any schema).
"""
from __future__ import annotations

import subprocess
import tempfile

from support import FactoryTestCase


class GoMigrateEmbedTest(FactoryTestCase):
    def test_go_migrate_embeds_sql_and_allows_an_empty_set(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(
                directory, "go-embed", language="go", target="aws",
                event_store="postgres", http="net-http", auth="none",
            )
            self.assertTrue((repo / "apps/service/migrations/embed.go").is_file())
            self.assertTrue((repo / "apps/service/migrations/keep").is_file())
            self.assertTrue((repo / "apps/service/cmd/migrate/main_test.go").is_file())
            migrate = (repo / "apps/service/cmd/migrate/main.go").read_text()
            self.assertIn("migrations.FS", migrate)
            self.assertNotIn("filepath.Glob", migrate)
            self.assertIn('fmt.Println("migrate: no migrations to apply")', migrate)
            self.assertNotIn("Refusing to report success", migrate)
            # The gate that expand/contract alone never covered: .sql files but no embed.go → refuse.
            (repo / "apps/service/migrations/embed.go").unlink()
            check = subprocess.run(
                ["python3", "scripts/check-migrations.py"], cwd=repo, text=True, capture_output=True
            )
            self.assertNotEqual(check.returncode, 0)
            self.assertIn("no embed.go", check.stderr)
