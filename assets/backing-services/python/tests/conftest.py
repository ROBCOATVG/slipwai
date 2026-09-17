"""Put this directory on `sys.path` so every suite can import the shared test helpers.

The event-store contract lives in `tests/contract/` and is run by two suites in different
directories: the infrastructure-free adapters in `tests/contract/`, and Postgres in
`tests/integration/`. pytest puts each test file's *own* directory on `sys.path`, not the suite
root, so without this the integration suite cannot see the contract its sibling imports by name.

A conftest.py at the suite root is the one place pytest guarantees to load before collecting
anything under it, which is why the line lives here rather than in an environment variable somebody
has to remember.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
