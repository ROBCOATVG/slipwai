"""Write this service's published API document to a file, from the routes themselves.

``make openapi`` runs it; ``make check-openapi`` runs it into a scratch file and fails when the
committed one differs. ``apps/<service>/openapi.json`` is the result, and it is committed because
things outside this process read it: ``packages/api-client`` is generated from it, a consumer reads
it without reading Python, and a reviewer sees the contract change in the diff rather than in a
running service.

── Why a file and not a running service ─────────────────────────────────────────────────────
``app.openapi()`` is the same document ``GET /openapi.json`` serves, and it is available the moment
the app exists — before anything binds. So the gate needs no port, no wait loop and no cleanup,
which is what makes it a gate rather than a flaky one.

── Why it is built the way the process builds it ────────────────────────────────────────────
The app is constructed here exactly as ``main`` constructs it, flag source and all. A document built
from a differently-assembled app is a document that describes a service nobody runs: the route a
flag source adds would be missing from it, and the browser app's client would have no way to call
the one endpoint it actually needs.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .adapters.driving.http.app import build_app, readiness
__FLAGS_IMPORT__


def main() -> None:
    """Write the document to the path named on the command line, or to ``openapi.json`` here."""
    destination = Path(sys.argv[1] if len(sys.argv) > 1 else "openapi.json")
    # `readiness()` with no store: the document needs the *route*, and ``/ready``'s schema is the
    # same whether or not one was handed over. Opening a store here would make writing a document a
    # thing that touches a database, which is precisely what a gate must not do.
    app = build_app([readiness()]__FLAGS_SOURCE__)
    # Trailing newline, two-space indent, keys as FastAPI orders them: a document a person will read
    # in a diff, and one that does not make every commit look like it rewrote the whole file.
    destination.write_text(json.dumps(app.openapi(), indent=2) + "\n")


if __name__ == "__main__":
    main()
