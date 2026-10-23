"""`AGENTS.md` and `docs/architecture.md`: the rules that hold whoever works in the project.

Both are generated from the selection rather than shipped whole, because a rule about an adapter the
project does not have is a rule that teaches the reader to ignore the file. What they *say* is under
`assets/guidance/` — two pages and the per-answer rules either is made of — and what is here is the
selection: which rules this project's own answers put it under, in what order, and the values its sentences
agree with. `docs/generated-prose.md` is the rule that split them, and `rules.py` reads the tree.

Three things in these pages are deliberately not in an asset, and each is the same reason: an asset that
could express it would be a second answer to a question the project's declarations already answer. The
browser sentences agree with how many browser apps there are. The ownership bullets are one per service.
And the deployment paragraph a managed target contributes is the target package's own answer
(`AGENT_RULES`), not a page's — a backend's or a cloud's paragraph belongs to whoever wrote the package.

One block is in the page unconditionally and phrased conditionally, and is worth knowing why before
somebody tidies it: *Finding your way around this codebase* is written identically for every project
because an extension is elected at `./init`, after this file is written. `./init` can only *append* to
`AGENTS.md`, so a code index's own block lands below the closing line as a footnote, and it was the one
place in a generated project that mentioned the index at all — while the two skills that ask for exactly
the operation an index performs said nothing about how to perform it. Naming those two in the page is the
bridge, which is why an index extension's own suite holds them to still saying what it claims they say.
"""
from __future__ import annotations

from ..catalog import CATALOG
from ..deployment_shapes import row
from ..loaded_targets import answer, cloud_of
from ..npm_workspace import npm
from ..registry import SHARED_CODE, registry
from ..services import (
    App,
    containers_of,
    contexts_of,
    described,
    families_of,
    has_feature,
    services_of,
    transports_of,
    web_apps,
)
from ..target_protocol import AGENT_RULES
from ..targets import managed
from .backing_service_prose import stores_by_rung
from .compose import composed
from .existing import EXISTING_GUIDANCE
from .flags import reader_calls, reader_paths
from .rules import frontend_contract, page, rule
from .write_model_prose import agents_write_model, architecture_write_model, store_port_rule


def browser_agreements(web: list[App]) -> dict[str, str]:
    """What the browser section's sentences have to agree with: how many browser apps there are, and where.

    Every one of these is a sentence agreeing with a count, which is the half of a conditional
    `docs/generated-prose.md` keeps in Python — the asset carries the words and this carries the agreement,
    so that neither the asset nor a template language is a second answer to "how many browser apps is it".
    """
    several = len(web) > 1
    return {
        "browser-plural": "s" if several else "",
        "browser-paths": ", ".join(f"`{app.path}`" for app in web),
        "browser-is": "are" if several else "is an",
        "browser-proxies": "; ".join(f"`{app.path}` proxies `/api` to `{app.api}`" for app in web),
        "browser-consumes": "Each consumes" if several else "It consumes",
        "browser-imports": "none imports" if several else "it does not import",
    }


def architecture(profile: str, apps: list[App]) -> str:
    services = services_of(apps)
    web = web_apps(apps)
    families = families_of(apps)
    # A browser app shares code the same way a service does, and it is the npm family whether or not any
    # service is: without this, a browser app beside a Go service is told nothing about `packages/` at all.
    if web and not any(npm(family) for family in families):
        families = [*families, web[0].language]
    contexts = "\n".join(
        f"- `{context}` — " + "; ".join(
            f"`{service.path}`" + (f": {service.purpose}" if service.purpose else " (no purpose recorded yet)")
            for service in members
        )
        for context, members in contexts_of(apps).items()
    )
    # Read from the family itself: the page is per family, and names `typescript` for a browser app even
    # where no service is.
    shared_code = {family: registry().families[family].answers[SHARED_CODE] for family in families}
    shared = "\n\n".join(
        f"In {family}: {shared_code[family]}." if len(families) > 1 else f"{shared_code[family]}."
        for family in families
    )
    model_gate = (
        ", and `make check-model` makes every slice from `modelled` on name its `context` beside its `service`"
        if profile == "event-modelling" else ""
    )
    base = page("architecture.md", {
        "services": ", ".join(described(service) for service in services),
        "shared-code": shared,
        "contexts": contexts,
        "model-gate": model_gate,
        **browser_agreements(web),
    }, wanted=("browser",) if web else ())
    if profile == "event-modelling":
        base += architecture_write_model(apps)
    return base


def agent_guidance(
    profile: str, apps: list[App], target: str = "none", shape: str = "liner",
) -> str:
    """`AGENTS.md`: the standing page, with the rules this project's own answers put it under written into it.

    The order is the project's, not the asset's — a rule arrives where the declaration that asked for it
    comes in the list, and some arrive once per service — so the rules are assembled here and handed to the
    page as one value. Which rule each answer gets is a section name; what a rule says is in `rules.md`.
    """
    services = services_of(apps)
    web = web_apps(apps)
    rules = "".join(
        f"- `{service.path}/**` is {'the' if len(services) == 1 else 'a'} `{service.backend}` backend service. "
        f"Use its native toolchain and keep domain/application code\n"
        f"  independent of delivery and persistence adapters.\n"
        for service in services
    )
    if len(services) > 1:
        rules += (
            "- `project.json` lists the services, each with its own language, framework and backing-service "
            "answers; add one with the\n  factory's `add-service`, and record what one is for with its "
            "`describe-service`, never by hand.\n"
        )
    for app in web:
        rules += rule("browser-app", {
            "path": app.path, "api": f" talking to `{app.api}`" if len(web) > 1 else "",
        })
    if web:
        rules += frontend_contract(apps)
    if profile == "event-modelling":
        rules += agents_write_model(apps)
    if composed(apps):
        rules += rule("demo")
    if containers_of(apps):
        rules += rule("containers")
    if has_feature(apps, "memory"):
        rules += store_port_rule(apps)
    # Keyed by the store *and* the rung: the same Postgres proves a never-write-the-same-version-twice
    # guarantee about a log in one service and a lost-update guarantee about a row in the next, and one
    # paragraph claiming both is a paragraph whose concurrency test nobody can place.
    for store, logged in stores_by_rung(services):
        rules += rule(f"{store}-{'event' if logged else 'state'}-store")
    for transport in transports_of(apps):
        rules += rule("http-transport", {"transport": transport})
    # Two passes and not one: who signs in to the service and who signs in to the product are answered on
    # separate axes, and a project may have either realm without the other.
    for identity in dict.fromkeys(s.selection.feature_of("auth") for s in services):
        if identity is not None:
            rules += rule(f"{identity}-auth")
    for identity in dict.fromkeys(s.selection.feature_of("users") for s in services):
        if identity is not None:
            rules += rule(identity)
    if target == "existing":
        rules += EXISTING_GUIDANCE
    if managed(CATALOG, target):
        # The flag rule names the file each service reads one through, rather than describing the
        # convention: an author who has to derive `FLAG_<KEY>` for themselves eventually derives it wrong.
        deployment = answer(target, AGENT_RULES, default="")
        if shape == "skiff" and (choice := row(target, shape)):
            deployment = rule("skiff", {"compute": choice["compute"], "database": choice["database"]})
        rules += deployment + rule("flags", {
            "readers": reader_paths(apps), "calls": reader_calls(apps), "cloud": cloud_of(target),
        })
        # The browser half only where there is a browser: the flag rule for an app that does not exist is
        # the kind of rule that teaches a reader to skim the file.
        if web:
            rules += rule("browser-flags", {"web": web[0].path})
    # The rules are a section of their own rather than a value in the page's text, so that a project with
    # none of them — every application wrapped rather than generated — gets no blank line where they would
    # have been. The page's own newline is what ends the last rule, which is why the trailing one goes.
    contract = "continuation-standard" if profile == "standard" else "continuation-cruise"
    wanted = ("rules", contract) if rules else (contract,)
    return page("agents.md", {"rules": rules.removesuffix("\n")}, wanted=wanted)
