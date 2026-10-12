"""How one canonical toolkit file reaches a generated project, or why it does not.

`assets/toolkit/` is the single source for the shipped skills, docs and gate scripts; `assets/profiles/`
overlays whatever a profile replaces. Nothing is copied twice and no starter copy is committed anywhere, so
a change under `assets/` reaches every combination the moment it is generated.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache

from .assets import PROFILE_ROOT, TOOLKIT_ROOT, asset_files
from .capabilities import declared_for, pruning_capabilities, serves
from .catalog import CATALOG, EXTENSIONS, family_of, framework_of
from .examples import Speaker, resolve_canonical_examples, resolve_examples_for, stamp_pseudocode_notes
from .extension_directory import files as package_files
from .extension_tools import declared as tools_declared
from .guards import declared as guards_declared
from .hooks import declared
from .registry import EXECUTABLES, registry
from .services import APPLICATIONS, FIRST_SERVICE, FIRST_WEB, App, families_of, services_of, web_apps, wrapped_of
from .tooling import for_app, verify_path

# The language the toolkit's own prose and canonical snippets are written in: the keel's
# material, not a language package.
# Where no service the keel made speaks (an adoption), every marker resolves to these, from the keel's own copy under
# `assets/examples/`, so adopting needs no language installed (S09 Q2).
CANON = "typescript"

STANDARD_OVERRIDES = {
    "docs/adr/0001-record-architecture-decisions.md",
    "skills/architecture-decisions/SKILL.md",
    "skills/adversarial-testing/SKILL.md",
    "skills/adversarial-testing/resources/attack-catalogue.md",
}


def skill_of(path: str) -> str | None:
    """The skill a toolkit path belongs to — `SKILL.md` and every resource beside it — or None."""
    parts = path.split("/")
    return parts[1] if len(parts) > 2 and parts[0] == "skills" else None


@lru_cache(maxsize=1)
def skill_declarations() -> dict[str, tuple[str, ...] | None]:
    """What each skill in the catalogue says it serves, read once off the asset tree."""
    declared: dict[str, tuple[str, ...] | None] = {}
    for source in asset_files(TOOLKIT_ROOT / "skills"):
        if source.name == "SKILL.md":
            declared[source.parent.name] = declared_for(source.read_text(encoding="utf-8"))
    return declared


def toolkit_treatment(path: str, profile: str, capabilities: set[str] | None = None) -> str:
    """How one canonical toolkit file reaches a generated project, or why it does not.

    Two questions, and they are different ones. The **profile** decides the event-modelling documents and
    the model gate, which are a workflow rather than a capability. What the project **can do** decides the
    skills: a skill declares the capabilities it serves in its `SKILL.md` frontmatter (`capabilities.py`),
    and one that declares none serves every project, which is most of the catalogue. `secure-oauth-oidc` is
    eleven thousand words about a login; in a project with no identity provider it is eleven thousand words
    about nothing, and it is also a wrong turn `find-skills` can take.

    This is deliberately not the same rule as the one about a skill's *examples*. A language-shaped skill
    still ships wherever its language is not the project's, with a pseudocode disclaimer (see
    `stamp_pseudocode_notes`), because a skill nobody can read is worse guidance than one whose examples
    are in the wrong language. That reading only exists where the skill is about something the project has;
    `typescript-strict` in a Go project is not guidance in the wrong language, it is guidance about a
    language this project does not use, and it declares `typescript` for exactly that reason.

    A toolkit file the generator also writes — `docs/first-slice.md`, say — needs no entry here: `scaffold`
    writes the generated files over the copied ones, so the generated text wins by construction and there is
    no second list of "which docs are generated" to keep in step with `project/docs.py`.
    """
    if profile == "standard" and path in STANDARD_OVERRIDES:
        return "profile-transformed"
    if profile == "standard" and (
        path.startswith("docs/event-model/")
        or path in {"docs/event-modeling-to-code.md", "docs/first-slice.md"}
        or path.startswith("scripts/event-model/")
    ):
        return "profile-excluded"
    skill = skill_of(path)
    if skill is not None and capabilities is not None and not serves(skill_declarations().get(skill), capabilities):
        return "capability-excluded"
    return "copied"


# The committed assets — a skeleton's comments, a skill's prose, a Spec Kit template — say `apps/service`
# and `apps/web`, the names every project had before a generation could choose them. Matched as whole path
# segments, so `apps/web-admin` is not half-rewritten when the browser app is called something else.
ASSET_PATHS = {
    kind: re.compile(rf"{APPLICATIONS}/{name}(?![\w-])")
    for kind, name in (("service", FIRST_SERVICE), ("web", FIRST_WEB))
}


def spoken_for(text: str, service: App | None, web: App | None) -> str:
    """An asset's `apps/service` and `apps/web`, as this project spells them.

    In a service's own files `apps/service` is that service, whichever one it is; in the toolkit and the
    profile overlays it is the first service. `apps/web` is the browser app that proxies to that service,
    or the first, where the project has one at all — and is left alone where it has none, because prose
    about a browser app the project lacks is not made truer by renaming it. `apps/service` is left alone
    for the same reason and in one more case: an adopted repository between `adopt` and its first confirmed
    candidate (ADR 0003) has no application to name, and gets the asset's own words until it has one.
    """
    text = text if service is None else ASSET_PATHS["service"].sub(service.path, text)
    return text if web is None else ASSET_PATHS["web"].sub(web.path, text)


# What the prose says where a repository holds no application to point at as its example: `adopt` writes the
# commands before any candidate has been confirmed (ADR 0003), and confirming one regenerates them, so this is
# what stands in for the short window between. The same question `spoken_for` answers for an asset's paths.
NO_APPLICATION = "the first application confirmed"
NO_DIRECTORY = "that application's own directory"


def example_of(apps: list[App]) -> tuple[str, str]:
    """The application a generated command's prose points at, and its directory — or what to say instead."""
    first = next(iter(services_of(apps) or wrapped_of(apps)), None)
    return (first.name if first else NO_APPLICATION, first.path if first else NO_DIRECTORY)


def own_paths(files: dict[str, str], apps: list[App]) -> dict[str, str]:
    """`spoken_for` over every file that lives under a service, in that service's own name."""
    web = web_apps(apps)
    spoken = dict(files)
    for service in services_of(apps):
        proxy = next((app for app in web if app.api == service.name), web[0] if web else None)
        for path, text in files.items():
            if path.startswith(f"{service.path}/"):
                spoken[path] = spoken_for(text, service, proxy)
    return spoken


def speakers_of(apps: list[App]) -> list[Speaker]:
    """The languages a project's skills speak, in service order, each labelled for its block.

    One speaker per backend, because two services on the same backend want the same snippet. The label is
    the language's name from the catalog, the framework beside it only where the project has two
    frameworks of one language, and the services it is for — so the agent working in `apps/ledger` can
    see which block is written for the code it is in.
    """
    services = services_of(apps)
    if not services:
        # No service the keel made: the canonical snippets stand as written, and `stamp_pseudocode_notes`
        # says whose languages they are not.
        return [Speaker(CANON, CANON, "TypeScript")]
    per_backend: dict[str, list[App]] = {}
    for service in services:
        per_backend.setdefault(service.backend, []).append(service)
    families = [family_of(backend) for backend in per_backend]
    speakers = []
    for backend, owners in per_backend.items():
        family = family_of(backend)
        name = CATALOG["backends"][backend]["label"].split(" — ")[0]
        framework = framework_of(backend)
        if framework is not None and families.count(family) > 1:
            name = f"{name} ({framework.replace('-', ' ').title()})"
        paths = ", ".join(f"`{service.path}`" for service in owners)
        speakers.append(Speaker(backend, family, f"{name} — {paths}"))
    return speakers


def toolkit_files_from_assets(profile: str, apps: list[App]) -> dict[str, str]:
    # Snippets are a property of the language, overridden per backend where the framework changes the
    # answer, and every language a service is written in gets its block at each marker. The paths the
    # prose names are the first service's, and the disclaimer names every language the project lacks
    # TypeScript examples for — which is none of them when one of the services is TypeScript.
    # Where nothing here was made by the keel, the first application that existed before the method did
    # is what the prose's `apps/service` means, and its language is the one the snippets are not in.
    services = services_of(apps)
    first = next(iter(services or wrapped_of(apps)), None)
    web = web_apps(apps)
    speakers = speakers_of(apps)
    families = families_of(apps) or list(dict.fromkeys(app.language for app in wrapped_of(apps)))

    def copied(source) -> str:
        text = source.read_text(encoding="utf-8")
        resolved = (resolve_examples_for(text, speakers) if services
                    else resolve_canonical_examples(text))
        return spoken_for(resolved, first, web[0] if web else None)

    capabilities = pruning_capabilities(profile, apps)
    files: dict[str, str] = {}
    for source in asset_files(TOOLKIT_ROOT):
        path = source.relative_to(TOOLKIT_ROOT).as_posix()
        if toolkit_treatment(path, profile, capabilities) == "copied":
            files[path] = copied(source)
    overlay = PROFILE_ROOT / profile
    if overlay.is_dir():
        for source in asset_files(overlay):
            path = source.relative_to(overlay).as_posix()
            # An overlay file *is* the profile's answer for the path it rewrites, so the profile's own
            # verdicts do not apply to it — but a rewrite of a skill this project has no capability for is
            # still a skill it has no capability for.
            if toolkit_treatment(path, profile, capabilities) != "capability-excluded":
                files[path] = copied(source)
    if CANON not in families:
        stamp_pseudocode_notes(files, families)
    return files


#: Where an extension package's files land in a generated project. The path `./init` already looks under,
#: so an extension that arrives from the chandlery is run by the loop that ran the keel's own three.
EXTENSION_ROOT = "scripts/extensions"
#: What each offered extension attaches to, written beside them. The manifest itself is not copied — a project
#: is not where one is read — but the hooks are, because `./init` has to write the registry from what was
#: elected and there is no keel in a project to ask.
EXTENSION_HOOKS = f"{EXTENSION_ROOT}/available.json"
#: The same, for the second closed set. Separate from the hooks file because the two are agreed to
#: separately: electing an extension runs its hooks, and a guard — which may refuse a tool call a person
#: asked for — is a question `./init` asks and a person answers.
EXTENSION_GUARDS = f"{EXTENSION_ROOT}/available-guards.json"
#: And for the tool names each one needs a headless session allowed to call. A third file rather than a key
#: in the first, because `available.json` is keyed by hook point and `tools` is not a point: a reader that
#: walked it as one would be asking the closed set about a name that was never in it.
EXTENSION_TOOLS = f"{EXTENSION_ROOT}/available-tools.json"


def extension_files() -> dict[str, str]:
    """Every installed extension's files, at the paths a generated project runs them from.

    The project gets the files at generation, not at election, because the menu `./init` shows is built from
    the catalogue and the election happens inside the project — there is no keel there to fetch anything.
    What is offered is what was installed when the project was generated, which is also what `./init` can
    actually run, and those being the same list is the whole point.

    A file that is not text is skipped rather than refused: the keel writes a project as text, an extension
    that ships a binary is shipping something the generator has no way to place, and one unreadable file is
    not a reason the other extensions do not arrive. `check-extensions` is where that is said out loud.
    """
    written: dict[str, str] = {}
    attached: dict[str, dict] = {}
    guarding: dict[str, dict] = {}
    calling: dict[str, list[str]] = {}
    for extension in EXTENSIONS:
        attached[extension.name] = declared(extension.manifest)
        guarding[extension.name] = guards_declared(extension.manifest)
        calling[extension.name] = list(tools_declared(extension.manifest))
        for relative in package_files(extension.root):
            try:
                text = (extension.root / relative).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            written[f"{EXTENSION_ROOT}/{extension.name}/{relative.as_posix()}"] = text
    written[EXTENSION_HOOKS] = json.dumps(attached, indent=2, sort_keys=True) + "\n"
    written[EXTENSION_GUARDS] = json.dumps(guarding, indent=2, sort_keys=True) + "\n"
    written[EXTENSION_TOOLS] = json.dumps(calling, indent=2, sort_keys=True) + "\n"
    return written


def executable_paths(profile: str, apps: list[App]) -> set[str]:
    """Every generated path that has to arrive runnable.

    The toolkit's executable bit can be read off disk — `assets/toolkit/` is committed with it set, and
    everything there lands at the path it is committed at — but a language's skeleton is written under each
    service's directory, so its asset mode cannot answer a question asked about the generated path. That pair
    is stated by each backend's `executables` answer, relative to the service and stamped here per service. A
    lost `chmod +x` on `mvnw` is a fresh clone where every Maven goal reports "permission denied", so
    `tests/test_matrix.py` asserts the mode on the written file rather than trusting the answer.
    """
    # `scripts/deploy.py`, `scripts/bootstrap.py`, `scripts/check-flags.py` and `scripts/check-deploy-role.py`
    # arrive only with a production target; naming a path that is not written costs nothing, since the mode
    # is set on the files that exist.
    executables = {
        "init", "scripts/verify", "scripts/backing-services.py", "scripts/ratchet.py", "scripts/check-convergence.py",
        "scripts/deploy.py", "scripts/bootstrap.py", "scripts/check-flags.py", "scripts/check-deploy-role.py",
    }
    executables |= {verify_path(family, apps) for family in families_of(apps)}
    for service in services_of(apps):
        executables |= {for_app(path, service.path) for path in registry().answer(service.backend, EXECUTABLES)}
    capabilities = pruning_capabilities(profile, apps)
    for source in asset_files(TOOLKIT_ROOT):
        if source.stat().st_mode & 0o111:
            path = source.relative_to(TOOLKIT_ROOT).as_posix()
            if toolkit_treatment(path, profile, capabilities) == "copied":
                executables.add(path)
    return executables
