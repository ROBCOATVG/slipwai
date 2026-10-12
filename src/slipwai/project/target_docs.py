"""Which pages a project going to production is given, and the words the README borrows from its target.

A managed target's `docs/deployment.md` and `docs/adr/0002-production-target.md` are entirely that cloud's:
its nodes, its products, its prices, its consequences. There is no general version of either to parameterise
— the attempt would be a page of conditionals describing nothing in particular — so each target brings its
own, as the `docs_pages` member of its `TARGET`.

Until phase 10 this module was a table saying which keel module wrote them, with one module per cloud beside
it. The table is gone: a target package answers `docs_pages` and the keel asks. What is left here is the
asking, and the two small readings the README does of the same `TARGET` — the rows it adds to *Before
`./init`* and the nouns its *Production* section is written round.

The paths are the same for every target on purpose: a reader who has seen one generated project knows where
the drawing and the decision record are, whatever it deploys to, and `slipwai migrate` merges them across a
change of neither name nor number.
"""
from __future__ import annotations

from ..errors import GenerationError
from ..loaded_targets import answer
from ..services import App
from ..target_protocol import DOCS_PAGES, PREREQUISITES, README_WORDS


def pages(project_name: str, apps: list[App], target: str) -> dict[str, str]:
    """Both pages for this target, written from this project's own answers."""
    built = answer(target, DOCS_PAGES, default={})
    if not built:
        raise GenerationError(
            f"the {target} target provisions infrastructure but answers no docs_pages: a managed target "
            f"arrives with its drawing and its decision record, which is what `docs_pages` is"
        )
    return {path: build(project_name, apps) for path, build in built.items()}


def prerequisites(target: str) -> tuple[tuple[str, str], ...]:
    """The README's *Before `./init`* table, middle rows only: what this cloud in particular asks of the
    machine that runs the first day's work.

    The rows around them — Python, the forge, the repository URL, somewhere to keep the passphrase — are the
    same wherever a project deploys, so they stay in `readme.py` and these are numbered into the middle of
    them. Each row is what to have and what proves it is there.
    """
    return tuple(answer(target, PREREQUISITES, default=()) or ())


def words(target: str) -> dict[str, str]:
    """The nouns the README's *Production* section is written round: what `infra/` runs a service as, what a
    browser app is served from, and what `make bootstrap` looks for.

    Words rather than a second copy of the section, because everything around them — the pipeline,
    `AUTO_PROMOTE`, the rollback workflow, what `make bootstrap` does once — is the same promise whatever
    the cloud is.
    """
    return dict(answer(target, README_WORDS, default={}) or {})
