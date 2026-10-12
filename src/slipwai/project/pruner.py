"""The pruning script a project carries, and the keel's own copy of it: the keel's one implementation, with rows.

`assets/backing-services/prune.py` names no language. What it needs to know about one (which files in a service
carry marker regions, which a feature owns, what a feature added to the manifest and how that is removed) is
each family's `prune_rows`, answered in its language module. This part reads those answers from the registry
and gives them to the script two ways:

- `emitted` is what a generated project carries as `scripts/backing-services.py`: the keel's source with its one
  empty `ROWS` line replaced by the rows of the project's families, as JSON the script reads.
- `pruner` is what the keel itself prunes with at generation, `add-service` and `replay`: the same file,
  loaded, with every loaded family's rows. `assets.PRUNER` is the keel's copy with none, which is what the catalog
  checks read for the facts that are not rows. It cannot read the registry itself, because `assets` is the
  foundation tier and the registry is not (`scripts/check-structure.py`).

The format is fixed in `specs/001-slipwai-2-language-addons/contracts/backend-protocol.md`, `prune_rows`.
"""
from __future__ import annotations

import functools
import json
import sys
from collections.abc import Iterable
from types import ModuleType
from typing import Any

from ..assets import BACKING_SERVICE_ROOT, ROOT
from ..catalog import CATALOG
from ..registry import PRUNE_ROWS, Registry, registry

SOURCE = BACKING_SERVICE_ROOT / "prune.py"
# The keel's own line, the one place a script's rows go. Emission replaces it; a source without exactly one is refused.
ROWS_LINE = "ROWS: dict[str, dict] = {}\n"
OPTIONS_LINE = "AXIS_OPTIONS: dict[str, dict] = {}\n"
TARGETS_LINE = "AXIS_TARGETS: dict[str, dict] = {}\n"
REQUIRES_LINE = "TARGET_REQUIRES: dict[str, tuple[str, ...]] = {}\n"


def family_rows(loaded: Registry, family: str) -> dict | None:
    """One family's rows, read through its first backend, so a family answer and a backend's are read alike.

    A family with no loaded backend (its frameworks absent or refused) has nothing to prune and answers None.
    """
    backend = next((key for key, candidate in loaded.backends.items() if candidate.family == family), None)
    return None if backend is None else dict(loaded.answer(backend, PRUNE_ROWS))


def prune_rows(families: Iterable[str]) -> dict[str, dict]:
    """The rows of these families, keyed by family, in the order given; a family with no backend has none."""
    loaded = registry()
    rows = {family: family_rows(loaded, family) for family in families}
    return {family: answer for family, answer in rows.items() if answer is not None}


def axis_options(catalog: dict[str, Any] | None = None) -> dict[str, dict]:
    """Every axis option a package brought, keyed by axis, in the shape the pruner's own table takes.

    The keel's copy of the pruner carries the infrastructure answers and no framework: an option named
    after a library — `fastapi`, `spring-web` — belongs to the package that implements it. They are
    written into a generated project's copy from the merged catalogue, the way each family's rows are,
    so a project prunes by the options it was actually offered.
    """
    merged = CATALOG if catalog is None else catalog
    keel = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))["axes"]
    brought: dict[str, dict] = {}
    for axis, spec in merged["axes"].items():
        own = set(keel.get(axis, {}).get("options", {}))
        for name, option in spec["options"].items():
            if name in own:
                continue
            brought.setdefault(axis, {})[name] = {
                "capabilities": list(option.get("capabilities", ())),
                "features": list(option.get("features", ())),
                "targets": list(option.get("targets", ())),
                "label": option.get("label", ""),
                "note": option.get("note", ""),
                "app-in-compose": bool(option.get("app-in-compose")),
                "repository-owned": list(option.get("repository-owned", ())),
                "web-app-owned": list(option.get("web-app-owned", ())),
            }
    return brought


def axis_targets(catalog: dict[str, Any] | None = None) -> dict[str, dict]:
    """Where every option is offered, by axis, as the merged catalogue says it.

    Written into a project's copy because the keel's own carries no place at all: every place is a package,
    so the shipped literal says `none` and `existing` and nothing else, and a project that deploys somewhere
    would otherwise prune by a table that had never heard of where it deploys.
    """
    merged = CATALOG if catalog is None else catalog
    return {axis: {name: list(option.get("targets", ())) for name, option in spec["options"].items()}
            for axis, spec in merged["axes"].items()}


def target_requires(catalog: dict[str, Any] | None = None) -> dict[str, list[str]]:
    """Which axes each target will not take the no-infrastructure answer to, as the merged catalogue says.

    The other half of the same fact, and the one a prune has to refuse on: a project that deploys an HTTP
    service and proves the deploy by asking it for `/health` cannot be pruned to `--http none` afterwards
    any more than it could be generated that way.
    """
    merged = CATALOG if catalog is None else catalog
    return {name: list(target.get("requires", ())) for name, target in merged["targets"].items()
            if target.get("requires")}


def emitted(families: Iterable[str], source: str | None = None) -> str:
    """The keel's pruning script carrying the rows of these families, the options their packages brought,
    and where the installed targets offer each answer — nothing of any other, as the project's copy."""
    text = SOURCE.read_text(encoding="utf-8") if source is None else source
    for line in (ROWS_LINE, OPTIONS_LINE, TARGETS_LINE, REQUIRES_LINE):
        if text.count(line) != 1:
            raise RuntimeError(f"the pruning script must carry exactly one `{line.strip()}` line to write into")
    written = {
        ROWS_LINE: ("ROWS: dict[str, dict]", prune_rows(families)),
        OPTIONS_LINE: ("AXIS_OPTIONS: dict[str, dict]", axis_options()),
        TARGETS_LINE: ("AXIS_TARGETS: dict[str, dict]", axis_targets()),
        REQUIRES_LINE: ("TARGET_REQUIRES: dict[str, tuple[str, ...]]", target_requires()),
    }
    for line, (declared, value) in written.items():
        text = text.replace(line, f'{declared} = json.loads(r"""\n{json.dumps(value, indent=2)}\n""")\n')
    return text


@functools.cache
def pruner() -> ModuleType:
    """The keel's pruner: the script a project of every loaded family would carry, loaded.

    It is `emitted` run as a module rather than the shipped file with rows patched in afterwards, because the
    script folds the brought options into its tables — `FEATURES`, what puts the app in Compose, what a
    transport owns — as it loads, so a copy that learned of them after loading would still refuse `fastify`
    as a feature it does not know. The same text is what the project gets, so the two cannot disagree.
    """
    module = ModuleType("slipwai_factory_pruner")
    module.__file__ = str(SOURCE)
    # Registered before it runs: `dataclasses` looks the defining module up by name while it builds a class.
    sys.modules[module.__name__] = module
    exec(compile(emitted(registry().families), str(SOURCE), "exec"), vars(module))
    return module
