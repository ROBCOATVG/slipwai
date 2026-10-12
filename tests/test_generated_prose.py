"""The three-way rule of [docs/generated-prose.md](../docs/generated-prose.md), held by a check.

Phase 16 moves standing text out of `src/slipwai/project/` and into assets. The risk it carries is that every
one of those modules writes a file somebody receives, so a move that changes a byte is a change nobody asked
for. The digest gate in `test_briefs.py` is what catches that per slice. This is the other half: the rules
that make the mechanism safe to use eight more times.

**Both directions of the substitution.** A token an asset names that nothing provides would ship `{{make}}`
into somebody's repository, where it reads as a typo in the method rather than a bug in the keel — the file
is valid markdown either way, so nothing downstream would notice. And a value provided that no asset names is
a value somebody keeps in step with a path that moved, for no reader at all.

**Nothing the keel renders ships a marker** — that one lives in `test_generated.py`, which already stands a
real project up once for its class, rather than generating a second one here to ask one question.

**Nothing the keel renders ships a marker.** The check the other two cannot make: a real generation, read for
a placeholder that survived it. A token can be provided, named, and still reach a project unresolved if a
page is copied by a path that does not render it — which is exactly the arrangement `toolkit.py` uses, where
an asset is copied verbatim and then written over by the resolved one.

Read over **what the keel renders**, and not over every file a project receives, because `{{name}}` is not
the keel's spelling alone. A generated project ships `scripts/agents/registry.json` carrying
`"argPlaceholder": "{{args}}"` and a skill carrying `{{badges}}`, and both are another system's substitution
that must arrive intact — a harness fills `{{args}}` itself. Scanning everything would refuse those, and the
only way to keep them would be to exempt them by name, which is a list that goes stale the first time
somebody adds a skill. So the rows below name where each templated tree lands, and the check reads those.
"""
from __future__ import annotations

import unittest
from collections.abc import Callable

import checkout_packages  # noqa: F401

from slipwai.assets import ADOPTION_ROOT, GUIDANCE_ROOT, PAGE_ROOT, TOOLKIT_ROOT
from slipwai.errors import GenerationError
from slipwai.layout import AT_ROOT
from slipwai.project import (
    add_commands,
    briefs,
    commands,
    docs,
    flags,
    ground_command,
    pin_commands,
    prose,
    readme,
    rules,
    run_skill,
    sail_section,
)


def pooled(*providers: Callable[[], dict[str, str]]) -> dict[str, str]:
    """One tree's values, from every module that writes a page into it.

    `commands/` is one directory that five modules write into, and no keel module holds the others' values:
    one that did would have to import the modules that import it. Two of them name `make`, which is one
    value two pages ask for; what the rules below read is the pool, and the digest gate is what holds each
    page to the set its own module provides.
    """
    values: dict[str, str] = {}
    for provider in providers:
        values.update(provider())
    return values


#: Every directory of assets that is rendered rather than copied, where what it renders to lands in a
#: generated project, and the values each may name. One row per templated asset tree: a slice of phase 16
#: that templates another adds its row here, and the two rules below then hold it without another test being
#: written. A tree lands at one or more paths, each either a directory of rendered files or a single page —
#: `assets/guidance/` is three files that become two pages, and `rules.md` is not one of them, being the
#: paragraphs the pages are assembled from.
TEMPLATED = (
    (TOOLKIT_ROOT / "agents", ("agents",), lambda: briefs.values(AT_ROOT)),
    # The pages a project is given that are rendered rather than copied. Three rows rather than one,
    # because each tree is written by its own module and so names its own values — pooling them would let
    # a page name a token only another module provides and still pass.
    (PAGE_ROOT, ("README.md",), lambda: readme.values("project", "standard", [], "none", "liner")),
    # `docs/` is written by two modules: the four pages `docs.py` renders, and the release half of
    # `docs/deployment.md`, which is `flags.py`'s because every sentence of it is about the reader,
    # `flags.tf` and `flags.auto.tfvars`. Pooled as `commands/` is, and for the same reason: no keel
    # module holds the other's values, and one that did would import the module that imports it.
    (PAGE_ROOT / "docs", ("docs",),
     lambda: pooled(lambda: docs.values("project", "standard", [], "none"), lambda: flags.values([]))),
    (PAGE_ROOT / "skills/run-the-app", ("skills/run-the-app",),
     lambda: run_skill.values("project", [], AT_ROOT)),
    (GUIDANCE_ROOT, ("AGENTS.md", "docs/architecture.md"), lambda: rules.TOKENS),
    (TOOLKIT_ROOT / "commands", ("commands",),
     lambda: pooled(commands.values, sail_section.values, add_commands.values)),
    # The pages only a repository that adopted the method receives. An asset of the adoption rather than of
    # the toolkit, because everything under `assets/toolkit/` is copied into every project and only an
    # adopted one is written over here — so a page kept there would reach a generated repository with its
    # `{{make}}` still in it, which is the third refusal catching the first slice to need the distinction.
    (ADOPTION_ROOT / "commands", ("commands",),
     lambda: pooled(pin_commands.values, ground_command.values)),

)


class SectionTest(unittest.TestCase):
    """The answer phase 16 gave to conditional prose: a whole section is an asset's, a sentence is not."""

    PAGE = (
        "Standing opening.\n\n"
        "<!-- section: browser -->\n## Browser\n\nIts words.\n<!-- end section -->\n"
        "Standing close.\n"
    )

    def test_a_section_the_module_does_not_want_leaves_nothing_behind(self) -> None:
        self.assertEqual(prose.render("p.md", self.PAGE, {}, ()), "Standing opening.\n\nStanding close.\n")

    def test_a_section_the_module_wants_keeps_its_words_and_loses_its_markers(self) -> None:
        rendered = prose.render("p.md", self.PAGE, {}, ("browser",))
        self.assertIn("## Browser", rendered)
        self.assertNotIn("<!-- section", rendered)
        self.assertNotIn("<!-- end section -->", rendered)

    def test_no_selection_keeps_every_section(self) -> None:
        self.assertIn("## Browser", prose.render("p.md", self.PAGE, {}))

    def test_a_section_the_page_has_not_got_is_refused_rather_than_ignored(self) -> None:
        """A module selecting a section that is no longer there is a paragraph silently gone from somebody's
        file — the failure the digest gate exists for, caught here instead."""
        with self.assertRaises(GenerationError) as raised:
            prose.render("p.md", self.PAGE, {}, ("frontend",))
        self.assertIn("has no section frontend", str(raised.exception))

    def test_a_section_opened_and_never_closed_is_refused(self) -> None:
        with self.assertRaises(GenerationError) as raised:
            prose.sections("p.md", "<!-- section: a -->\nwords\n")
        self.assertIn("never closes it", str(raised.exception))

    def test_a_section_named_twice_is_refused(self) -> None:
        page = "<!-- section: a -->\none\n<!-- end section -->\n<!-- section: a -->\ntwo\n<!-- end section -->\n"
        with self.assertRaises(GenerationError) as raised:
            prose.sections("p.md", page)
        self.assertIn("carries section a twice", str(raised.exception))


class TokenTest(unittest.TestCase):
    """Both directions, over every templated asset tree there is."""

    def test_every_token_an_asset_names_is_one_some_value_provides(self) -> None:
        for directory, _lands, provider in TEMPLATED:
            named = provider()
            for path in sorted(directory.glob("*.md")):
                with self.subTest(asset=path.name):
                    for token in prose.MARKER.findall(path.read_text(encoding="utf-8")):
                        self.assertIn(token, named, f"{path.name} names {{{{{token}}}}}, which nothing provides")

    def test_every_value_provided_is_named_by_some_asset(self) -> None:
        for directory, _lands, provider in TEMPLATED:
            text = "".join(path.read_text(encoding="utf-8") for path in sorted(directory.glob("*.md")))
            used = set(prose.MARKER.findall(text))
            for token in provider():
                with self.subTest(value=token):
                    self.assertIn(token, used, f"nothing under {directory.name}/ names {{{{{token}}}}}")

    def test_a_token_nothing_provides_is_refused_by_name(self) -> None:
        with self.assertRaises(GenerationError) as raised:
            prose.resolve("p.md", "a {{nobody}} b", {"make": "make"})
        self.assertIn("{{nobody}}", str(raised.exception))
        self.assertIn("the whole set is make", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
