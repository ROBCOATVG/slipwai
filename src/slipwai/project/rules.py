"""Reading `assets/guidance/`, and the half of what its pages say that may not live in one.

The prose moved out of Python in slice 16.3. `agents.md` and `architecture.md` are the two pages a project
receives whole; `rules.md` is the per-answer paragraphs either of them is made of, one section each, because
a page carries them in the order its own declarations come in and repeats some of them per service — which
one render of one page cannot do, and a page that fixed their order would answer a question the declarations
already answer.

`rules.md` is sections and nothing between them, deliberately: a blank line outside a marker is text, and
text outside a marker is kept by every render, so it would land in every page.

What is left in Python here is what `docs/generated-prose.md` keeps out of an asset: the table saying where
each transport publishes its API contract, which is read off the declaration, and the two halves of the
sentence that agrees with whether this project's transport publishes one at all. Neither is a paragraph
somebody edits for its wording — each is a second sentence the same declaration already decides.
"""
from __future__ import annotations

from ..assets import GUIDANCE_ROOT
from ..services import App, services_of, web_apps
from .prose import render

#: Every value a page under `assets/guidance/` may name, and the whole of what one may name. Declared rather
#: than derived, because no single render names them all — a page is rendered once and its rules one section
#: at a time, each with the values that section asks for. `tests/test_generated_prose.py` holds this against
#: the tree in both directions: a token here that no asset names is a value somebody keeps in step with a
#: path that moved for no reader at all, and `prose.resolve` refuses the other direction mid-generation.
TOKENS = (
    "api", "api-client", "api-contracts", "browser-consumes", "browser-imports", "browser-is",
    "browser-paths", "browser-plural", "browser-proxies", "calls", "cloud", "compute", "contexts",
    "database", "model-gate", "path", "readers", "rules", "services", "shared-code", "transport", "web",
)


def page(name: str, named: dict[str, str], wanted: tuple[str, ...] | None = None) -> str:
    """One page under `assets/guidance/`, rendered for this project: the sections `wanted`, tokens resolved.

    The read is here rather than in `prose.py` because a root is not a mechanism: `prose` is the substitution
    and the section marker, and the next slice of phase 16 renders a different tree with the same two.
    """
    return render(name, (GUIDANCE_ROOT / name).read_text(encoding="utf-8"), named, wanted)


def rule(name: str, named: dict[str, str] | None = None) -> str:
    """One section of `rules.md`: what a page carries for one answer to one axis.

    A name `rules.md` has not got is refused by `prose.render`, naming the file and what it does carry —
    which is where a lookup table keyed by a product used to raise `KeyError` from the middle of a
    generation.
    """
    return page("rules.md", named or {}, (name,))


# Where each transport publishes its service's API contract, keyed by the feature that answered the `http`
# axis; `__APP__` is the service's own directory. A transport absent from here publishes nothing this
# factory ships — Quarkus and Spring do not — so the sentence that names these simply stops after
# "contracts": a rule pointing at a path the project does not have teaches the reader to ignore the file.
API_CONTRACTS = {
    "fastify": "`GET /openapi.json`",
    "fastapi": "`GET /openapi.json` (and `/docs` for a person)",
    "net-http": "`__APP__/openapi.yaml`",
}


def api_contracts(apps: list[App]) -> str:
    """Where this project's services publish their contracts, as the sentence promising one says it."""
    published = dict.fromkeys(
        API_CONTRACTS[transport].replace("__APP__", service.path)
        for service in services_of(apps)
        for transport in (service.selection.feature_of("http"),)
        if transport in API_CONTRACTS
    )
    if not published:
        return ""
    # Broken before the path rather than after it, so the sentence wraps the same way whatever the
    # project is called and however many services it has.
    return f",\n  which this project publishes at {', '.join(published)}"


def frontend_contract(apps: list[App]) -> str:
    """The rule a project with a browser app is under: what the frontend reads, and where it is."""
    web = web_apps(apps)
    if any(service.selection.feature_of("http") in API_CONTRACTS for service in services_of(apps)):
        client = (
            "\n  `packages/api-client` is that contract as types — generated from the committed document by"
            "\n  `make build-packages`, never edited — so the browser app calls the API through it rather than"
            "\n  writing paths and shapes out a second time. `make openapi` rewrites the document from the"
            "\n  routes and `make check-openapi` fails when the committed one has fallen behind them."
        )
    else:
        # Said out loud, because the absence reads as an omission otherwise: there is no `packages/api-client`
        # here, and a reader who finds none would reasonably conclude the frontend was left half-wired.
        client = (
            "\n  This project's transport publishes none, so there is no `packages/api-client` and the one"
            "\n  route fetches by hand with a `Record<string, unknown>` response — what a shape nobody"
            "\n  declared honestly is. Publishing a document is what buys the typed client; `docs/design.md`"
            "\n  says what changes here when it does."
        )
    return rule("browser-contract",
                {"api-contracts": api_contracts(apps), "api-client": client, "web": web[0].path})
