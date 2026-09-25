"""A code index the check cannot open is not a corrupt one, and is never moved aside for it.

A project on macOS's system Python found `check-codegraph` calling CodeGraph's sound database corrupt, and
`code_index.py health` rebuilding it in a loop: that SQLite refuses a read-only open of a WAL database with no
`-shm` beside it, which is how CodeGraph leaves one once its daemon exits. The open is retried with `immutable=1`,
and an open that still fails is said as one.
"""
from __future__ import annotations

import os
import sqlite3
import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase
from test_code_index_health import indexed

# macOS's system SQLite as far as this goes: a read-only open of a WAL database with no `-shm` beside it fails with
# "unable to open database file", where other builds create the `-shm` themselves; `REFUSE_EVERY_OPEN` fails them all.
APPLE_SQLITE = """import os, sqlite3
_connect = sqlite3.connect
def connect(database, *args, **kwargs):
    path = str(database).removeprefix("file://").removeprefix("file:").split("?")[0]
    wal = os.path.isfile(path) and open(path, "rb").read(20)[18:20] == b"\\x02\\x02"
    apple = "mode=ro" in str(database) and wal and not os.path.exists(path + "-shm")
    if os.environ.get("REFUSE_EVERY_OPEN") or apple:
        raise sqlite3.OperationalError("unable to open database file")
    return _connect(database, *args, **kwargs)
sqlite3.connect = connect
"""


class CodeIndexOpenTest(FactoryTestCase):
    def test_a_database_the_check_cannot_open_is_not_called_corrupt_and_is_never_moved_aside(self) -> None:
        """A project on macOS's system Python found `check-codegraph` calling CodeGraph's sound WAL database corrupt:
        that SQLite refuses a read-only open with no `-shm` beside the file, `health` moved the database aside,
        rebuilt the same one, and failed again. A read-only open refused is the environment, not the index. That
        SQLite is stood in for here, whoever runs the suite: a `sitecustomize` makes every `mode=ro` open of a WAL
        database with no `-shm` beside it fail as Apple's does, and `REFUSE_EVERY_OPEN` fails every open. The first
        is read through `immutable=1`; a database no open reaches is left where it is and said so."""
        with tempfile.TemporaryDirectory() as directory:
            repo, env, log = indexed(self, directory, "unopened")
            index = repo / ".codegraph"
            database = index / "codegraph.db"
            with sqlite3.connect(database) as connection:
                connection.execute("PRAGMA journal_mode=wal")
            connection.close()
            self.assertEqual(database.read_bytes()[18:20], b"\x02\x02")
            self.assertFalse((index / "codegraph.db-shm").exists())
            apple = Path(directory) / "apple-sqlite"
            apple.mkdir()
            (apple / "sitecustomize.py").write_text(APPLE_SQLITE)
            refusing = {**os.environ, **env, "PYTHONPATH": str(apple)}
            health = ["python3", "scripts/agents/code_index.py", "health"]
            probe = ("import sqlite3, sys\n"
                     "sqlite3.connect(f'file:{sys.argv[1]}?mode=ro', uri=True).execute('PRAGMA quick_check')")
            refused = subprocess.run(["python3", "-c", probe, str(database)], env=refusing, text=True,
                                     capture_output=True)
            self.assertIn("sqlite3.OperationalError: unable to open database file", refused.stderr)
            sound = subprocess.run(health, cwd=repo, env=refusing, text=True, capture_output=True)
            self.assertEqual(sound.returncode, 0, sound.stdout + sound.stderr)
            self.assertIn("code-index: current", sound.stdout)
            self.assertFalse((index / "corrupt").exists())
            closed = {**refusing, "REFUSE_EVERY_OPEN": "1"}
            unopened = subprocess.run(health, cwd=repo, env=closed, text=True, capture_output=True)
            gated = subprocess.run(["python3", "scripts/check-codegraph.py"], cwd=repo, env=closed, text=True,
                                   capture_output=True)
            self.assertEqual(unopened.returncode, 1)
            self.assertIn("could not be opened to be checked", unopened.stdout)
            self.assertIn("left it where it is", unopened.stdout)
            self.assertEqual(gated.returncode, 1)
            self.assertIn("could not be opened to be checked", gated.stderr)
            self.assertNotIn("integrity check", gated.stderr)
            self.assertTrue(database.is_file())
            self.assertFalse((index / "corrupt").exists())
            self.assertFalse(log.exists(), "nothing rebuilt an index that was never shown to be damaged")
