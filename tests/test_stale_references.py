"""Nothing the prune leaves behind points at something the prune took away.

The pruner removes files; it cannot remove the sentence in a file it kept that tells the reader to go and
look at one of them. The result reads as a defect in the reader rather than in the text — an agent that
opens `apps/service/src/…` is told to compare this adapter with a sibling that is not in the repository,
or to read a file under a name it does not have here.

Two properties, both read off generated trees rather than off `assets/`, because what is stale depends on
the answers:

  1. a path or file name quoted in a retained file under `apps/` resolves in the tree, and
  2. a retained file does not point at an adapter by name — *the* SQLite adapter, *the* Postgres one —
     when the project has no such adapter.

Comparative prose survives both: "SQLite serialises its writers" explains why a guarantee needs a real
server and is true wherever it is read. What neither allows is the definite article pointing somewhere.
"""
from __future__ import annotations

import re
import tempfile
from pathlib import Path

from support import FactoryTestCase, backends_under_test

from slipwai.catalog import CATALOG, axis_default

# Extensions a quoted token has to carry to be read as a path. `.js` is left out because a TypeScript
# import specifier names the compiled sibling of a `.ts` file that does exist, and `.md` because the
# skeleton deliberately cites pages of the *factory* that made the project (`docs/adr/…` in `events.ts`),
# which are not in the tree and are not meant to be.
EXTENSIONS = "ts|tsx|py|go|java|sql|properties|yml|yaml|tf|sh|xml|toml"
# Backticks in every language's comments, and Javadoc's `{@code …}`, which is Java's backtick. Files only,
# never a bare directory: `target/` and `cmd/` are build output that exists after a build and not before,
# and telling those apart from a shipped directory would need a second list to keep in step.
QUOTED = re.compile(rf"`([\w][\w./-]*\.(?:{EXTENSIONS}))`|\{{@code ([\w][\w./-]*\.(?:{EXTENSIONS}))\}}")

# An adapter, as prose names it and as the tree spells it. A project has the adapter when some path under
# it carries the spelling — which is how the pruner itself decides what is still answerable.
ADAPTERS = {
    "SQLite": "sqlite",
    "Postgres": "postgres",
    "PostgreSQL": "postgres",
    "Keycloak": "keycloak",
    "Fastify": "fastify",
}
# *The* named thing, which is a pointer. "SQLite serialises its writers" is a comparison and stays.
POINTER = "|".join(
    rf"\bthe {name} (?:adapter|one|pair|store|plugin)\b|\b{name} adapter's\b" for name in ADAPTERS
)
POINTS_AT = re.compile(POINTER)


def combinations() -> list[tuple[str, str, str, str, str]]:
    """Profile, backend, event store, transport and frontend — the spread that brings the most prose.

    Both transports per backend, because dropping the transport is the prune that leaves the read side
    behind with nothing to register on, and both profiles, because the standard one has no event store,
    no projections and no read side at all while the files that describe them are shared assets.
    """
    chosen = []
    for backend in backends_under_test():
        transport = axis_default("http", backend, "none")
        for profile in CATALOG["profiles"]:
            stores = ("memory", "sqlite", "postgres") if profile == "event-modelling" else ("memory",)
            for store in stores:
                chosen.append((profile, backend, store, transport, "react-vite"))
                chosen.append((profile, backend, store, "none", "none"))
    return chosen


class StaleReferenceTest(FactoryTestCase):
    def generated(self, directory: str) -> list[tuple[str, Path]]:
        repos = []
        for profile, backend, store, transport, frontend in combinations():
            name = f"stale-{profile}-{backend}-{store}-{transport}-{frontend}"
            repos.append((name, self.generate(
                directory, name, profile, backend, frontend,
                event_store=store,
                http=transport,
                # Sign-in needs the transport to reach it, and a customer login needs a browser app.
                auth="keycloak" if transport != "none" else "none",
                users="keycloak" if frontend != "none" else "none",
            )))
        return repos

    def test_no_retained_file_points_at_a_file_that_is_not_there(self) -> None:
        dangling: list[str] = []
        with tempfile.TemporaryDirectory() as directory:
            for name, repo in self.generated(directory):
                files = [path for path in repo.rglob("*") if path.is_file() and "/.git/" not in path.as_posix()]
                basenames = {path.name for path in files}
                relatives = {path.relative_to(repo).as_posix() for path in files}
                for path in files:
                    relative = path.relative_to(repo).as_posix()
                    if not relative.startswith("apps/"):
                        continue
                    try:
                        text = path.read_text()
                    except (UnicodeDecodeError, OSError):
                        continue
                    for number, line in enumerate(text.splitlines(), 1):
                        for match in QUOTED.finditer(line):
                            token = match.group(1) or match.group(2)
                            if (
                                token.rsplit("/", 1)[-1] in basenames
                                or token in relatives
                                or any(one.endswith("/" + token) for one in relatives)
                            ):
                                continue
                            dangling.append(f"{name}: {relative}:{number} names `{token}`, which is not here")
        self.assertEqual(
            [],
            sorted(set(dangling)),
            "a file the prune kept points at one it did not write:\n  " + "\n  ".join(sorted(set(dangling))),
        )

    def test_no_retained_file_points_at_an_adapter_that_was_pruned(self) -> None:
        pointing: list[str] = []
        with tempfile.TemporaryDirectory() as directory:
            for name, repo in self.generated(directory):
                files = [path for path in repo.rglob("*") if path.is_file() and "/.git/" not in path.as_posix()]
                tree = " ".join(path.relative_to(repo).as_posix().lower() for path in files)
                present = {display for display, token in ADAPTERS.items() if token in tree}
                for path in files:
                    relative = path.relative_to(repo).as_posix()
                    if not relative.startswith("apps/"):
                        continue
                    try:
                        text = path.read_text()
                    except (UnicodeDecodeError, OSError):
                        continue
                    for number, line in enumerate(text.splitlines(), 1):
                        for match in POINTS_AT.finditer(line):
                            named = next(one for one in ADAPTERS if one in match.group(0))
                            if named in present:
                                continue
                            pointing.append(
                                f"{name}: {relative}:{number} says “{match.group(0)}”, and there is none"
                            )
        self.assertEqual(
            [],
            sorted(set(pointing)),
            "a file the prune kept names an adapter this project does not have; describe the kind of "
            "store rather than pointing at a sibling that may not be here:\n  "
            + "\n  ".join(sorted(set(pointing))),
        )

    def test_the_rules_themselves_notice_what_they_exist_to_catch(self) -> None:
        """Both patterns, held to the text they were written for and to the text they must leave alone."""
        self.assertEqual(
            ["http-app.ts"],
            [m.group(1) or m.group(2) for m in QUOTED.finditer("`FlagSnapshot` in `http-app.ts` is structural")],
        )
        self.assertEqual(
            ["src/adapters/driven/event-store-postgres/index.ts"],
            [m.group(1) or m.group(2)
             for m in QUOTED.finditer("the real one in `src/adapters/driven/event-store-postgres/index.ts`")],
        )
        self.assertEqual([], [m.group(0) for m in QUOTED.finditer("built into `target/` by `mvnw`")])
        self.assertEqual(
            ["CheckpointStore.java"],
            [m.group(1) or m.group(2) for m in QUOTED.finditer("see {@code CheckpointStore.java} for it")],
        )
        self.assertTrue(POINTS_AT.search("see the SQLite adapter's note"))
        self.assertTrue(POINTS_AT.search("neither the in-memory nor the SQLite adapter can prove"))
        self.assertIsNone(POINTS_AT.search("SQLite serialises its writers, so it would too"))
        self.assertIsNone(POINTS_AT.search("Postgres has a uuid column, SQLite has text"))
