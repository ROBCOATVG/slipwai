"""The composition root's half of readiness: which store this project opens, and what `/ready` is given.

`flag_route.py` does this for the flag source; this does it for the event store, and for the same reason.
The HTTP adapter is the same file in every project on a transport — it declares the store structurally and
registers `/ready` — so the *answer* to the event-store question can only arrive where the entry point is
written, which is here.

Three rules shape every string `entry_stores.py` holds, and they are written here because this is where a
reader arrives.

**One store, opened once, by the entry point.** Nothing else in a generated service constructs one: a
module-level store is a second composition root nobody can see, and two of them are two logs.

**The answer sits in its own marked region.** `scripts/backing-services.py --event-store memory` deletes the
chosen adapter, so an entry point that named it unconditionally would stop compiling. The shape is the one
`assets/backing-services/prune.py` describes for an alternative: both states are valid at once — the region
sets the store and the line after it falls back to the in-memory one, so removing the region leaves a
project that still runs, on the store it has left.

**Nothing connects while the process starts.** A service that dies because its database is not up yet gives
a platform a crash loop where it wanted a task reporting "not ready" until the store came back — and it
makes `make smoke-image`, which runs one image with nothing else running, impossible to pass. Two of the
three drivers are lazy already (`pg.Pool`, `pgxpool`); psycopg connects as its connection object is built,
so the Python entry point defers the open to the first probe and keeps the store once one exists.
"""
from __future__ import annotations

from ..selection import Selection
from .entry_stores import ENTRY_STORES, FEATURE

#: What a transport's entry point carries where the store is wired in. Several rather than one because an
#: import cannot be written where an argument goes, and Python's import groups are sorted by a linter.
STORE_IMPORT = "__STORE_IMPORT__"
APP_IMPORTS = "__APP_IMPORTS__"
STORE_OPEN = "__STORE_OPEN__"
STORE_ARGUMENT = "__STORE_ARGUMENT__"
SETTINGS_IMPORTS = "__SETTINGS_IMPORTS__"


def wire_store(files: dict[str, str], selection: Selection, backend: str) -> dict[str, str]:
    """Resolve a transport entry point's store placeholders, in place, and hand the files back.

    A project with no transport has no entry point and nothing to wire; a project with no event store —
    every project on the standard profile — has its placeholders *removed* rather than left in the file,
    which is the direction `wire_entry` takes for the same reason: an unresolved placeholder is the one
    failure here that would reach a generated project looking like the factory forgot something.
    """
    wiring = ENTRY_STORES.get(backend)
    if wiring is None or wiring.entry not in files:
        return files
    # `has("memory")` is the question "was the event-store axis asked at all": the in-memory adapter
    # arrives with every answer to it and with no other axis, so a project without it — every project on
    # the standard profile — is one with no store to open and no port to probe.
    stored = selection.has("memory")
    store = selection.feature_of("event-store") if stored else None
    opened = wiring.open[store].rstrip("\n") + "\n" + wiring.gap if stored else ""
    # `"none"` is a project with no event-store axis at all (the standard profile). The adapter
    # import of `buildApp` / `readiness` still has to land: emptying the placeholder drops the
    # line, and TypeScript keeps that import in this table rather than as a static line, so Biome
    # can sort it with the adapter imports when a store is present. Python names the same symbols
    # through `__APP_IMPORTS__` instead, so its table has no `"none"` row and this is a no-op.
    imported = wiring.imports[store] if stored else wiring.imports.get("none", "")
    # The marker in those two says `__FEATURE__` until here, because the feature is the key each was found
    # under and a table's key is the one place an option's name belongs. The in-memory answer owns no
    # feature and carries no marker, so this is a no-op for it.
    if store is not None:
        opened, imported = opened.replace(FEATURE, store), imported.replace(FEATURE, store)
    content = files[wiring.entry]
    # Each placeholder owns its own line, so removing one removes the line with it rather than leaving a
    # blank where a project with no store would otherwise read as one the factory forgot to fill in.
    for placeholder, replacement in ((STORE_IMPORT, imported), (STORE_OPEN, opened)):
        content = content.replace(f"{placeholder}\n", replacement)
    content = content.replace(STORE_ARGUMENT, wiring.argument if stored else wiring.absent)
    # `"none"` and not `None`: the first is a project with no event store, the second is the in-memory
    # answer, and they are told apart here because they need different imports.
    answered = store if stored else "none"
    for placeholder, table in ((APP_IMPORTS, wiring.app_imports), (SETTINGS_IMPORTS, wiring.settings_imports)):
        if table is not None:
            content = content.replace(placeholder, table[answered])
    files[wiring.entry] = content
    return files
