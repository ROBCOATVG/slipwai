"""`slipwai package new`: a language, an extension or a target package that loads on the first try.

Every kind of package is a directory, a manifest and some files, and each has a shape the loader refuses for
reasons a publisher cannot guess from the outside — a `core` range, a module name derived from the package's
own, a `LANGUAGE` the fragment has to agree with, an entry point meeting six obligations, a `TARGET`
answering every member a managed target owes. Version 1 had no scaffold for any of them, and every package
anyone wrote started as a copy of one that already worked, carrying whatever was wrong with it.

**So the keel writes the skeleton, and the skeleton is one the keel reads.** An extension, a target or a
quickstart passes `package check` the moment it is written, with the parts a publisher has to fill marked
`TODO` rather than left out. A language is the one kind that cannot: a backend owes some thirty answers that
are its language's and nobody else's, so its scaffold is a valid shape answering none of them, and the loader's
refusal — one line naming every member still missing — is the publisher's worklist. Its browser-app half has
four answers and a tree, every one with a placeholder that is not wrong, so a frontend scaffold
(`--parts frontend`) loads and generates as written. A scaffold that fails for a reason it does not name is a
scaffold whose first lesson is that the tool is broken.

**The manifest is written from this keel's schema, not from a constant.** A package scaffolded today declares
the range this copy speaks, so it is current by construction and nobody has to know what to put there.
"""
from __future__ import annotations

import json
from pathlib import Path

from .assets import this_command
from .errors import GenerationError
from .extension_shape import OBLIGATIONS
from .language_shape import name_fault
from .language_templates import (
    BIOME_TREE,
    FRONTEND_TREE,
    LANGUAGE_BACKEND,
    LANGUAGE_FRONTEND_ANSWERS,
    LANGUAGE_FRONTEND_ENTRIES,
    LANGUAGE_FRONTEND_IMPORTS,
    LANGUAGE_MODULE,
    LANGUAGE_NO_BACKEND,
)
from .package_templates import (
    CHANGELOG,
    ENTRY_POINT,
    FIRST,
    FRAGMENTS,
    LANGUAGE_README,
    MAKEFILE,
    QUICKSTART_README,
    README,
    WORKFLOW,
)
from .target_templates import BOOTSTRAP_STACK, SCRIPT, SERVICE_STACK, SETUP_SCRIPT, TARGET_MODULE, TARGET_README

#: Where the reusable workflow a package's CI calls actually lives. Version 1's repository has a
#: `package.yml` too, with different inputs — a package pointed at it would fail on the first push with
#: inputs that workflow has never heard of. Version 2 merged back there (slice 8.5), so the two are one now.
KEEL_REPO = "ROBCOATVG/slipwai"
KINDS = ("extension", "language", "quickstart", "target")
#: The release a package that has cut none is a snapshot of, which is what `conformance.version_rule` asks
#: of one. Language, extension and target scaffolds open this release rather than claiming it was cut.
FIRST_RELEASE = "1.0.0"
#: The publisher's verbs, in the order they are used. `plugin` is the odd one and is here rather than in a
#: verb of its own on purpose: it renders a package of the keel's *own* material for a harness to install,
#: which is the publisher's job done by the keel, and a second top-level verb would have been a second
#: place a person looks for the thing that makes something installable.
VERBS = ("new", "check", "version", "release", "register", "key", "plugin", "harness")
#: What a scaffolded manifest declares it needs: this keel's schema, and everything up to the next major.
def core_range(schema: str) -> str:
    major = schema.split(".")[0]
    return f">={schema},<{int(major) + 1}"


def title_of(name: str) -> str:
    """A key as a human name: `ux-gates` becomes `Ux gates`, which the publisher then edits."""
    return name.replace("-", " ").capitalize()


def module_of(name: str) -> str:
    return f"slipwai_language_{name.replace('-', '_')}"


def target_module_of(name: str) -> str:
    """The module a target package's `TARGET` is imported from, derived from its name the way a language's is."""
    return f"slipwai_target_{name.replace('-', '_')}"


def checked(kind: str, name: str) -> str:
    """The name, or the refusal that says what a package may be called."""
    if kind not in KINDS:
        raise GenerationError(f"a package is a {', a '.join(KINDS[:-1])} or a {KINDS[-1]}; "
                              f"`--kind {kind}` is none of them")
    fault = name_fault(kind, name)
    if fault is not None:
        raise GenerationError(f"{fault}. It becomes a directory, a key and part of a command, so it is held "
                              f"to what all three allow")
    return name


def extension_files(name: str, schema: str) -> dict[str, str]:
    """An extension package: its manifest, an entry point that already meets the six, and a README saying so."""
    manifest = {
        "key": name,
        "name": title_of(name),
        "description": f"TODO: one sentence `./init`'s menu shows for {name}. What it installs, and what it "
                       f"is for — the menu is the only place most people read about it.",
        "kind": "extension",
        "core": core_range(schema),
        # Both points this entry point answers, written out rather than left to `hooks.DEFAULTS`: a
        # publisher reading their own manifest should see what their script is attached to.
        "hooks": {"init": "init.py", "project": "init.py"},
    }
    obligations = "\n".join(f"{index}. **{said[0].upper()}{said[1:]}** — `{key}`."
                            for index, (key, said) in enumerate(OBLIGATIONS, start=1))
    return {
        "extension.json": json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        "VERSION": f"{FIRST_RELEASE}.dev0\n",
        "init.py": ENTRY_POINT.format(name=name, title=title_of(name)),
        "README.md": README.format(name=name, title=title_of(name), obligations=obligations,
                                   command=this_command()),
        "Makefile": MAKEFILE.format(name=name, kind="extension"),
        ".github/workflows/verify.yml": WORKFLOW.format(name=name, kind="extension", keel=KEEL_REPO),
        "CHANGELOG.md": CHANGELOG.format(name=name),
        "changelog.d/README.md": FRAGMENTS,
        f"changelog.d/first-{name}.md": FIRST.format(name=name, kind="extension"),
    }


#: What a language package may ship: services, browser apps, or both (`docs/frontend-protocol.md`).
PARTS = ("backend", "frontend")


def language_module(name: str, parts: tuple[str, ...], frontend: str) -> str:
    """The package's Python: the family, a backend answering nothing yet where it ships services, and a browser
    app that loads as written where it ships one."""
    front = "frontend" in parts
    filled = {
        "@IMPORTS@": LANGUAGE_FRONTEND_IMPORTS if front else "",
        "@ANSWERS@": LANGUAGE_FRONTEND_ANSWERS if front else "",
        "@ENTRIES@": LANGUAGE_FRONTEND_ENTRIES if front else "",
        "@BACKENDS@": LANGUAGE_BACKEND if "backend" in parts else LANGUAGE_NO_BACKEND,
    }
    text = LANGUAGE_MODULE
    for token, value in filled.items():
        text = text.replace(token, value)
    for token, value in (("@NAME@", name), ("@TITLE@", title_of(name)), ("@FRONTEND@", frontend)):
        text = text.replace(token, value)
    return text


def language_files(name: str, schema: str, parts: tuple[str, ...] = ("backend",)) -> dict[str, str]:
    """A language package of `parts`: its fragment, its `VERSION`, the Python the loader imports, and — where it
    ships a browser app — the app's trees under `assets/frontends/<name>-web/` and the Biome they are linted with.

    A backend loads as far as the members it has not answered, and the loader's refusal names each one: that
    list is the work. A frontend loads and generates as written, beside any backend, because what a browser app's
    family is asked is four answers and a tree, and every one of them has a placeholder that is not wrong.
    """
    unknown = [part for part in parts if part not in PARTS]
    if unknown or not parts:
        raise GenerationError(f"a language ships {' and/or '.join(PARTS)}; {', '.join(unknown) or 'nothing'} "
                              "is not one of them")
    frontend = f"{name}-web"
    fragment: dict = {
        "name": name,
        "core": core_range(schema),
        "order": 100,
        "family": name,
        # `targets` is required of a row, and `none` is the one every backend can be generated under.
        "backends": {name: {"label": f"{title_of(name)} — TODO: the framework, in a few words",
                            "targets": ["none"]}} if "backend" in parts else {},
    }
    if "frontend" in parts:
        fragment["frontends"] = {frontend: {
            "label": f"{title_of(name)} web — TODO: the framework and bundler, in a few words",
            "stack": "TODO: the stack, as a project's docs name it",
            "gate": "TODO: what the app's own gate runs",
            "capabilities": ["frontend"],
            "features": {},
        }}
    module = module_of(name)
    files = {
        "language.json": json.dumps(fragment, indent=2, ensure_ascii=False) + "\n",
        "VERSION": f"{FIRST_RELEASE}.dev0\n",
        f"{module}/__init__.py": language_module(name, parts, frontend),
        "README.md": LANGUAGE_README.format(name=name, title=title_of(name), command=this_command()),
        "Makefile": MAKEFILE.format(name=name, kind="language"),
        ".github/workflows/verify.yml": WORKFLOW.format(name=name, kind="language", keel=KEEL_REPO),
        "CHANGELOG.md": CHANGELOG.format(name=name),
        "changelog.d/README.md": FRAGMENTS,
        f"changelog.d/first-{name}.md": FIRST.format(name=name, kind="language"),
    }
    if "frontend" in parts:
        files.update({f"assets/frontends/{frontend}/{path}": text for path, text in FRONTEND_TREE.items()})
        files.update(BIOME_TREE)
    return files


def target_files(name: str, schema: str) -> dict[str, str]:
    """A target package: its row, the module answering the protocol, both stacks and the two scripts.

    Managed, and whole. A scaffold that declared itself unmanaged would owe the protocol nothing and would
    teach a publisher nothing about what a cloud has to answer; this one answers every required member with
    files it also writes, so it passes `check` the moment it is written and every TODO in it is visible.
    """
    manifest = {
        "name": name,
        "label": f"{title_of(name)} — TODO: what a project deployed here actually runs on, in a line. "
                 f"This is the sentence the target prompt shows.",
        "description": f"TODO: one sentence `slipwai search` shows for {name}.",
        "kind": "target",
        "core": core_range(schema),
        "managed": True,
        # Every managed target deploys something a deploy can be proved against, which is what `/health` is
        # for. Declared rather than assumed: a target that genuinely deploys no HTTP service removes it.
        "requires": ["http"],
    }
    module = target_module_of(name)
    return {
        "target.json": json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        # A snapshot of the first release, which is what the version rule asks of a package that has not cut
        # one: `1.0.0` is open, `changelog.d/` holds the fragment that will become its entry, and
        # `slipwai package version .` closes it. A scaffold carrying a release number would fail its own
        # `check` on the line that says the release has no entry — which is the scaffold teaching the
        # publisher that the tool is broken.
        "VERSION": f"{FIRST_RELEASE}.dev0\n",
        f"{module}/__init__.py": TARGET_MODULE.format(name=name, title=title_of(name)),
        "bootstrap/main.tf": BOOTSTRAP_STACK.format(name=name),
        "service/main.tf": SERVICE_STACK.format(name=name),
        "scripts/bootstrap.py": SCRIPT.format(name=name, what="Create what has to exist before",
                                              what_lower="create the account's standing resources"),
        "scripts/deploy.py": SCRIPT.format(name=name, what="Deploy",
                                           what_lower="apply the service stack for one environment"),
        "scripts/setup.py": SETUP_SCRIPT.format(name=name),
        "README.md": TARGET_README.format(name=name, title=title_of(name), module=module,
                                          command=this_command()),
        "Makefile": MAKEFILE.format(name=name, kind="target"),
        ".github/workflows/verify.yml": WORKFLOW.format(name=name, kind="target", keel=KEEL_REPO),
        "CHANGELOG.md": CHANGELOG.format(name=name),
        "changelog.d/README.md": FRAGMENTS,
        f"changelog.d/first-{name}.md": FIRST.format(name=name, kind="target"),
    }


#: Which scaffold each kind gets. One mapping rather than a chain of `if kind ==`, because a fourth kind


def quickstart_files(name: str, schema: str) -> dict[str, str]:
    """A quickstart package: the document, and the version a release of it is of.

    No Makefile and no workflow, and that is not an omission. A quickstart holds no code, so there is
    nothing for a gate to run that `package check` does not already do — and a scaffold that wrote a CI
    workflow which only ever ran one command would be teaching a publisher to maintain a file for nothing.
    """
    document = {
        "quickstart": 1,
        "name": name,
        "suits": f"TODO: one sentence about the product {name} suits — what it is like, not which packages "
                 f"it names. This is the row `slipwai generate` offers it by, to somebody who has never "
                 f"heard of a chandlery.",
        "core": core_range(schema),
        "answers": {"profile": "event-modelling"},
        "languages": [{"name": "todo-the-language-this-starts-from", "version": ">=1.0,<2"}],
        "extensions": [],
    }
    return {
        "quickstart.json": json.dumps(document, indent=2, ensure_ascii=False) + "\n",
        "VERSION": "0.1.0\n",
        "README.md": QUICKSTART_README.format(name=name, title=title_of(name), command=this_command()),
        "CHANGELOG.md": CHANGELOG.format(name=name),
        "changelog.d/README.md": FRAGMENTS,
        f"changelog.d/first-{name}.md": FIRST.format(name=name, kind="quickstart"),
    }


#: should be a row here and nothing else.
SCAFFOLDS = {"extension": extension_files, "language": language_files, "target": target_files,
             "quickstart": quickstart_files}
#: What a scaffold writes that is run rather than read, and so lands with its executable bit set. A script
#: a person has to `chmod` before it works is a script whose first run fails for a reason nothing said.
EXECUTABLE = {"extension": ("init.py",), "target": ("scripts/bootstrap.py", "scripts/deploy.py")}


def write(kind: str, name: str, into: Path, schema: str, parts: tuple[str, ...] = ("backend",)) -> list[str]:
    """Write the package under `into/<name>`, or refuse a directory that already holds something. `parts` is a
    language's: whether it ships services, browser apps or both."""
    checked(kind, name)
    root = into / name
    if root.exists() and any(root.iterdir()):
        raise GenerationError(f"{root} already holds something. A scaffold writes a whole package, so it "
                              f"writes into an empty directory or none at all")
    files = language_files(name, schema, parts) if kind == "language" else SCAFFOLDS[kind](name, schema)
    for path, text in files.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    for path in EXECUTABLE.get(kind, ()):
        (root / path).chmod(0o755)
    return [f"{root / path}" for path in files]
