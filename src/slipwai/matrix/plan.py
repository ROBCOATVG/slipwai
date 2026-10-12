"""The plan, read in the interpreter `run.plan` starts with the package directory already set.

`python -m slipwai.matrix.plan <language-dir> <package> <report>` writes the backends the package owns, each one's
native-gate rows and its image row to the file `<report>`, as JSON, and exits 0; where the package does not load, or
the catalog has outgrown the rows, it writes `{"refused": [line, …]}` instead. Nothing it prints is the report, so
nothing a package prints at import is. Imported only here, because the merged catalog is read at import and the
package directory is the one the maintainer named.

The backends are the package's own (`conformance.probe.owned`): a framework is planned with its family beside it and
owns its own backends, and a family with no backend of its own owns none, its frameworks' matrices generating it
.
"""
from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ..catalog import CATALOG
from ..conformance.probe import ALONE, owned, protocol
from ..images import image_builder
from ..probes import ready_path
from ..registry import registry
from .rows import image_row, native_rows


def report(directory: Path, package: str) -> dict[str, Any]:
    """What the plan says about `package` in `directory`: its backends and rows, or the lines refusing it."""
    refused, backends = protocol(directory, package)
    own, families = owned(registry(), (directory / package).resolve())
    if isinstance(backends, str):
        # A family that loaded and owns no backend, with no framework beside it, has nothing to run,
        # which is not a refusal.
        if families and not own and backends == ALONE.format(family=", ".join(families)):
            return {"backends": [], "rows": [], "images": []}
        # `protocol` names why there is nothing to check where there are no backends; its findings are the refusal.
        return {"refused": refused}
    try:
        rows = [asdict(row) for key in own for row in native_rows(CATALOG, key)]
    except ValueError as error:
        return {"refused": [str(error)]}
    # No managed target installed is no production image to build: `image_row` answers None, and the plan
    # carries no image rather than one nothing could be deployed from.
    built = [(key, image_row(CATALOG, key)) for key in own]
    images = [{"row": asdict(row), "tool": image_builder(key)["tool"], "ready": ready_path(key)}
              for key, row in built if row is not None]
    return {"backends": own, "rows": rows, "images": images}


def main(argv: list[str]) -> int:
    directory, package, destination = Path(argv[0]), argv[1], Path(argv[2])
    if not directory.is_absolute():
        directory = directory.absolute()
    destination.write_text(json.dumps(report(directory, package)), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
