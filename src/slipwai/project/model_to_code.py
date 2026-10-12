"""The document that says what each box on the model becomes in a file, per service.

Its own module because it is most of the bytes and none of the behaviour: `event_model.py` computes the
per-backend paths and this renders them, which is the same split the service layouts were on the other side
of. One page, generated per project, because the paths in it are the project's own.

A section per service rather than one table for the project, because the write model is per service and the
table is the write model written out: the same `evt` on the timeline is a record appended to a log in one
service and a file the use case raises after a row is saved in the next, and a reader told only the first
will write a fold into a service that keeps no history to fold.

The words are the asset's now — `assets/event-model/event-modeling-to-code.md` is the page and
`write-model.md` the two rung sections it carries once per service, which is why they are a file of
sections and nothing between them rather than a page of their own. What is left here is what
`docs/generated-prose.md` keeps out of an asset: the table of where each box lands, which is rendered from
the backend's own answer and so cannot drift from it, the bullet per service that agrees with how many
there are, and the paragraph on naming the owning service, which opens and closes inside the paragraph
around it.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..assets import MODEL_PAGE_ROOT
from .prose import page

PAGE = "event-modeling-to-code.md"
SECTIONS = "write-model.md"
#: Every token the three files under `assets/event-model/` may name, pooled with `event_model.TOKENS` by
#: `tests/test_generated_prose.py`. Declared rather than derived, because no single render names them all:
#: the page is rendered once and the write-model sections once per service, each with its own paths.
TOKENS = ("placing", "write-models", "examples", "path", "usecase", "events", "domain", "repository")


@dataclass(frozen=True)
class ServiceCode:
    """One service's section of the page: where it is, which rung it is on, and where its code lands.

    The rung arrives as the answer `metadata.sourced` already gave rather than as the axis's word, so this
    module has no second opinion about what `events` means and never has to be kept in step with one.

    `paths` is the backend's `event_model_paths` with `repository` always in it (`event_model.code_paths`),
    which only the state-stored section reads: on the other rung the store a write is appended to is the
    event-store port, and that is named in the write-model table rather than here.
    """

    path: str
    sourced: bool
    paths: dict[str, str]


def write_model_section(service: ServiceCode) -> str:
    """One service's table and rules, from the rung it is on and the paths its backend answered."""
    named = {"path": service.path, **{key: service.paths[key]
                                      for key in ("usecase", "events", "domain", "repository")}}
    return page(MODEL_PAGE_ROOT, SECTIONS, named,
                ("event-sourced",) if service.sourced else ("state-stored",))


def model_to_code(services: list[ServiceCode]) -> str:
    """`docs/event-modeling-to-code.md`, with one section per service and the project's own paths in it."""
    placing = (
        """A slice names the service it belongs to in `model.yaml`'s `service` field, decided against what each
service says it owns — the `purpose` on its `project.json` entry, listed under *Bounded contexts* in
`docs/architecture.md`. With one service the field is optional; with two or more, `make check-model`
requires it, because a slice that names no owner lands in the first service by gravity, not by decision."""
        if len(services) == 1
        else """A slice names the service it belongs to in `model.yaml`'s `service` field, decided against what each
service says it owns — the `purpose` on its `project.json` entry, listed under *Bounded contexts* in
`docs/architecture.md`. `make check-model` requires it here, because a slice that names no owner lands in
the first service by gravity, not by decision — and because with more than one write model in the project,
naming the service is what settles which table below the slice is read against."""
    )
    # Named per service only where there is more than one, so the single-service page keeps the sentence it
    # has always had rather than growing a prefix that answers a question nobody has.
    examples = "\n".join(
        f"- Express agreed examples as observable tests using `{service.paths['test']}`."
        if len(services) == 1
        else f"- In `{service.path}`, express agreed examples as observable tests using "
             f"`{service.paths['test']}`."
        for service in services
    )
    return page(MODEL_PAGE_ROOT, PAGE, {
        "placing": placing,
        "write-models": "\n".join(write_model_section(service) for service in services),
        "examples": examples,
    })
