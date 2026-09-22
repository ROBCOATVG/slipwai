"""Adding a service or a browser app to a generated project, with the generator's own code paths.

`add-service <name>` is run inside an existing generated project. It reads `project.json` for everything the
project was given — profile, frontend, target, and each service's language, framework and selection — puts
one more service on the list, and asks `scaffold.project_files` for the whole project twice: once with the
list as it was, once with the new service on it. Every file under the new service's directory is written,
and so is every other file whose content differs between the two — which is exactly the set the manifest
drives (the Makefile, Compose, CI, the workspace, `scripts/verify`, the prose that lists the services),
derived rather than kept as a list here. Then the same pruner generation runs cuts the new service down to
what this project actually has, so a project that dropped Keycloak with `./init` gets a second service with
no auth adapter either — unless the new service was asked for it by name.

The new service may be in another language: `--language python` beside a TypeScript first service. Without
a language it takes the first service's; without an axis flag it inherits the first service's answer where
its own backend offers it, and falls back to that backend's default where it does not (a Python service
cannot inherit Fastify, so it gets FastAPI).

`add-frontend <name> [--api <service>]` is the same operation for a browser app: the skeleton under
`apps/<name>` on the next dev-server port, proxying `/api` to the service it names (the first by default),
and the same regeneration of what the list drives — which is also how a project generated with
`--frontend none` gets its first browser app.

`describe-service <name> --purpose ... --context ...` records, after the fact, what a service the list already
has is for — the two fields the delivery loop places a slice against, which `generate` and `add-service` take
at scaffold time and which are otherwise found later, when the model's lanes or the specification's vocabulary
say what the contexts are. It scaffolds nothing: `project.json`'s entry is edited in place and every file
whose content the two fields reach — the architecture page, the agent guidance, the commands that list the
applications — is regenerated, the same way as above, so the file an agent reads says what was recorded.

Nothing is committed. The tree has to be clean first so that `git checkout .` and `git clean -fd` undo the
whole thing, and the command says what it wrote and what to run next.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import replace
from pathlib import Path

from .assets import PRUNER
from .catalog import CATALOG, axis_options
from .errors import GenerationError
from .layout import layout_of
from .manifest import apps_from_manifest, check_known, read_manifest, wrote_here
from .origin import adoption_of
from .scaffold import project_files
from .selection import Selection, resolve_selection
from .services import App, add_service, add_web, checked_contexts, contexts_phrase, frontend_of, services_of
from .targets import managed, offered_backends
from .toolkit import executable_paths


def refuse_uncommitted(root: Path) -> None:
    """Nothing is committed by this command, so what it writes has to be the only thing uncommitted."""
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True, check=False
    )
    if status.returncode != 0:
        return  # not a git repository, or no git: nothing to protect and nothing to undo with
    if status.stdout.strip():
        raise GenerationError(
            "this project has uncommitted changes; commit or stash them first, so that `git checkout .` and "
            "`git clean -fd` undo exactly what add-service wrote and nothing else"
        )


def selection_for(
    first: App | None, backend: str, named: dict[str, str | None], profile: str, target: str
) -> tuple[Selection, set[str]]:
    """The new service's selection, and the axes whose answers it inherited from the first service — none,
    where no service the factory made is there to inherit from.

    A flag wins. An axis without one takes the first service's answer when the new backend offers it —
    the same store, the same identity provider — and the new backend's own default where it cannot (a
    transport is per framework). Which answers were inherited matters afterwards: an inherited feature the
    project has since pruned stays pruned, while an asked-for one is kept.
    """
    inherited: set[str] = set()
    resolved: dict[str, str | None] = {}
    for axis in CATALOG["axes"]:
        if named.get(axis) is not None:
            resolved[axis] = named[axis]
            continue
        theirs = first.selection.choices.get(axis) if first is not None else None
        if theirs is not None and theirs in axis_options(axis, backend, target):
            resolved[axis] = theirs
            inherited.add(axis)
        else:
            resolved[axis] = None
    return resolve_selection(resolved, profile, backend, target), inherited


def add_service_to(
    root: Path, name: str, backend: str | None = None, named: dict[str, str | None] | None = None,
    purpose: str | None = None, contexts: list[str] | None = None,
) -> tuple[App, list[str], list[str]]:
    """Write the new service and everything the manifest drives; return it, its files, and the rewritten ones.

    `purpose` and `contexts` are recorded, not scaffolded from: they are what the delivery loop reads when it
    has to decide which service a slice belongs to, which is a question that only arises once this command
    has run.
    """
    document = read_manifest(root)
    apps = apps_from_manifest(document)
    check_known(apps)
    services = services_of(apps)
    if backend is None and not services:
        raise GenerationError(
            "this project has no service the factory made to take the language from; name it with --language"
        )
    first = services[0] if services else None
    backend = first.backend if backend is None and first is not None else backend
    assert backend is not None
    if backend not in offered_backends(CATALOG, document["target"]):
        raise GenerationError(
            f"--backend {backend} is not offered under the {document['target']} target this project goes to"
        )
    selection, inherited = selection_for(first, backend, named or {}, document["profile"], document["target"])
    with_new = add_service(apps, name, backend, selection, purpose=purpose, contexts=contexts)
    # An answer asked for by name is kept even where the project pruned it; so is the new backend's own
    # default for an axis the first service's answer could not carry.
    asked = {
        feature
        for axis, chosen in selection.choices.items()
        if axis not in inherited
        for feature in CATALOG["axes"][axis]["options"][chosen]["features"]
    }
    return grow(root, document, apps, with_new, asked)


def add_frontend_to(root: Path, name: str, api: str | None = None) -> tuple[App, list[str], list[str]]:
    """Write a new browser app — proxying `/api` to `api`, the first service by default — and what it drives."""
    document = read_manifest(root)
    apps = apps_from_manifest(document)
    check_known(apps)
    return grow(root, document, apps, add_web(apps, name, api), set())


def grow(
    root: Path, document: dict, apps: list[App], with_new: list[App], asked: set[str]
) -> tuple[App, list[str], list[str]]:
    """Write the last application on `with_new` and every file its arrival changes, then prune to what the
    project actually has plus `asked`."""
    refuse_uncommitted(root)
    app = with_new[-1]
    if (root / app.path).exists():
        raise GenerationError(
            f"{app.path} already exists but project.json does not list it; move it aside, or register it "
            "by hand if it is an application"
        )
    keep, settled = pruning_state(root, asked)
    added, rewritten, manifest = regenerate(root, document, apps, with_new, asked, new_path=app.path)

    # The manifest is edited in place rather than regenerated, so anything else it carries survives; the
    # `frontend` field follows the browser apps, so a project that had none now says which framework it has.
    document["deployables"][app.name] = manifest["deployables"][app.name]
    document["frontend"] = frontend_of(with_new)
    rewritten.append(record(root, document))
    PRUNER.prune(root, keep, settled=settled, log=lambda _message: None)
    return app, added, sorted(rewritten)


def describe_service_in(
    root: Path, name: str, purpose: str | None = None, contexts: list[str] | None = None
) -> tuple[App, list[str]]:
    """Record what a service already on the list is for, and rewrite every file that says so.

    A field given replaces what was recorded; one not given is left as it was. Nothing under `apps/` is
    touched: the two fields are read by the delivery loop and the pages that print them, never by the
    scaffold.
    """
    if purpose is None and contexts is None:
        raise GenerationError("nothing to record: say --purpose, --context (once per context), or both")
    document = read_manifest(root)
    apps = apps_from_manifest(document)
    check_known(apps)
    named = [app for app in apps if app.name == name]
    if not named:
        raise GenerationError(
            f"project.json lists no application named '{name}'; it has {', '.join(app.name for app in apps)}"
        )
    app = named[0]
    if not app.is_service:
        raise GenerationError(f"'{name}' is a browser app; a purpose and bounded contexts are a service's to record")
    revised = replace(
        app,
        purpose=(purpose or None) if purpose is not None else app.purpose,
        contexts=checked_contexts(contexts) if contexts is not None else app.contexts,
    )
    if revised.purpose == app.purpose and revised.contexts == app.contexts:
        raise GenerationError(f"'{name}' already records exactly that; nothing to write")
    described = [revised if candidate is app else candidate for candidate in apps]
    refuse_uncommitted(root)
    keep, settled = pruning_state(root, set())
    _added, rewritten, manifest = regenerate(root, document, apps, described, set())
    entry = document["deployables"][name]
    for key in ("purpose", "contexts"):
        if key in manifest["deployables"][name]:
            entry[key] = manifest["deployables"][name][key]
        else:
            entry.pop(key, None)
    rewritten.append(record(root, document))
    PRUNER.prune(root, keep, settled=settled, log=lambda _message: None)
    return revised, sorted(rewritten)


def regenerate(
    root: Path, document: dict, apps: list[App], revised: list[App], asked: set[str], new_path: str | None = None
) -> tuple[list[str], list[str], dict]:
    """Write every file whose regenerated content differs between the list as it was and as it is — and
    every file under `new_path`, the application being added — and return the added paths, the rewritten
    ones, and the manifest the revised list generates, for the caller to take its entry from."""
    layout, adoption = layout_of(document), adoption_of(document)
    arguments = (document["name"], document["profile"], document["target"])
    before = project_files(*arguments, apps, layout, adoption)
    after = project_files(*arguments, revised, layout, adoption)
    executables = {layout.place(path) for path in executable_paths(document["profile"], revised)}
    added: list[str] = []
    rewritten: list[str] = []
    for relative, content in after.items():
        if relative == "project.json":
            continue
        new = new_path is not None and relative.startswith(f"{new_path}/")
        # A file whose regenerated content is unchanged is left alone — unless it carries a region of a
        # feature asked for by name. `.env.example` reads the same whichever services a project has, so its
        # earlier prune is the only reason a newly asked feature's keys would be missing from it; written
        # whole, the prune below cuts it down to what the project now has.
        if not new and before.get(relative) == content and not carries_any(content, asked):
            continue
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, newline="")
        path.chmod(0o755 if relative in executables else 0o644)
        (added if new else rewritten).append(relative)
    return sorted(added), rewritten, json.loads(after["project.json"])


def pruning_state(root: Path, asked: set[str]) -> tuple[set[str], set[str]]:
    """What this project actually has, read off its disk before anything is written rather than off the
    recorded selections: a later `./init` may have taken a feature away, and a regenerated file must not
    bring it back — unless it was asked for. The features to keep, and the ones an earlier `./init` settled
    (their files here, their markers gone), whose fresh markers the prune strips again."""
    existing = PRUNER.project_services(root)
    installed = PRUNER.features_installed(root, existing)
    present = PRUNER.features_present(root, existing)
    return installed | asked, installed - present


def record(root: Path, document: dict) -> str:
    """Write the manifest, edited in place, with this factory stamped as the last to write here."""
    document["generator"] = wrote_here(document.get("generator"))
    (root / "project.json").write_text(json.dumps(document, indent=2) + "\n")
    return "project.json"


def carries_any(content: str, features: set[str]) -> bool:
    """Whether a regenerated file has a marked region belonging to one of these features."""
    return any(
        feature in features
        for name, _edge in PRUNER.MARKER.findall(content)
        for feature in PRUNER.marker_features(name)
    )


def report(app: App, added: list[str], rewritten: list[str], target: str = "none") -> str:
    """What was done and what to run next, for the person who ran it."""
    regenerated = ", ".join(path for path in rewritten if path != "project.json")
    if app.is_service:
        answers = ", ".join(f"{axis} {chosen}" for axis, chosen in app.selection.summary.items()) or "no axes"
        what = f"the {app.name} service, {app.backend} on port {app.port} ({answers}; {len(added)} files)"
    else:
        what = f"the {app.name} browser app on port {app.port}, proxying /api to {app.api} ({len(added)} files)"
    lines = [
        f"added {app.path}: {what}",
        f"registered it in project.json; regenerated from that list: {regenerated}",
    ]
    if app.is_service:
        lines.append(
            f"it holds the bounded {contexts_phrase(app)}" + (f" and owns: {app.purpose}" if app.purpose else "")
        )
        if not app.purpose:
            lines.append(
                f"no purpose recorded: say what it owns (`slipwai describe-service {app.name} --purpose \"...\"`), "
                "or /drive will ask before it places a slice here"
            )
    if managed(CATALOG, target) and app.is_service:
        # The stacks read the regenerated project.auto.tfvars.json, so the service's ECS service arrives with
        # the next deploy — but its image repository is the bootstrap stack's, applied by a person.
        lines.append(
            "it goes to production with the rest: infra/ was regenerated, and `make bootstrap` needs running once "
            "more (with admin credentials) to create its image repository before the pipeline can push to it"
        )
    lines += [
        "",
        "Nothing is committed. Review with `git status` and `git diff`; `git checkout . && git clean -fd` undoes it.",
        "Next: make verify",
    ]
    return "\n".join(lines)


def described_report(app: App, rewritten: list[str]) -> str:
    """What was recorded and which files now say it, for the person who ran `describe-service`."""
    regenerated = ", ".join(path for path in rewritten if path != "project.json") or "nothing else"
    return "\n".join([
        f"recorded for {app.path}: it holds the bounded {contexts_phrase(app)}"
        + (f" and owns: {app.purpose}" if app.purpose else " (no purpose recorded)"),
        f"written to project.json; regenerated from it: {regenerated}",
    ])
