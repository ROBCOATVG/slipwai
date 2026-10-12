"""`slipwai package new`: a language, an extension or a target package that loads on the first try.

Every kind of package is a directory, a manifest and some files, and each has a shape the loader refuses for
reasons a publisher cannot guess from the outside — a `core` range, a module name derived from the package's
own, a `LANGUAGE` the fragment has to agree with, an entry point meeting six obligations, a `TARGET`
answering every member a managed target owes. Version 1 had no scaffold for any of them, and every package
anyone wrote started as a copy of one that already worked, carrying whatever was wrong with it.

**So the keel writes the skeleton, and the skeleton is one the keel loads.** What `package new` emits passes
`extension check` or installs as a language the moment it is written, with the parts a publisher has to fill
marked `TODO` rather than left out. A scaffold that does not load is a scaffold whose first lesson is that
the tool is broken.

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
from .package_templates import (
    CHANGELOG,
    ENTRY_POINT,
    FIRST,
    FRAGMENTS,
    LANGUAGE_MODULE,
    LANGUAGE_README,
    MAKEFILE,
    README,
    WORKFLOW,
)
from .target_templates import BOOTSTRAP_STACK, SCRIPT, SERVICE_STACK, TARGET_MODULE, TARGET_README

#: Where the reusable workflow a package's CI calls actually lives. Version 1's repository has a
#: `package.yml` too, with different inputs — a package pointed at it would fail on the first push with
#: inputs that workflow has never heard of. This becomes `ROBCOATVG/slipwai` when version 2 merges back
#: there (slice 8.5), and that row says so.
KEEL_REPO = "ROBCOATVG/slipwai_v2_Fork"
KINDS = ("extension", "language", "target")
#: The release a package that has cut none is a snapshot of, which is what `conformance.version_rule` asks
#: of one. The other two kinds' scaffolds were written before that rule was and still carry `0.1.0`, which
#: fails their own `version` check; a target's does not.
FIRST_RELEASE = "1.0.0"
#: The publisher's verbs, in the order they are used. `plugin` is the odd one and is here rather than in a
#: verb of its own on purpose: it renders a package of the keel's *own* material for a harness to install,
#: which is the publisher's job done by the keel, and a second top-level verb would have been a second
#: place a person looks for the thing that makes something installable.
VERBS = ("new", "check", "version", "release", "register", "key", "plugin")
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
        "VERSION": "0.1.0\n",
        "init.py": ENTRY_POINT.format(name=name, title=title_of(name)),
        "README.md": README.format(name=name, title=title_of(name), obligations=obligations,
                                   command=this_command()),
        "Makefile": MAKEFILE.format(name=name, kind="extension"),
        ".github/workflows/verify.yml": WORKFLOW.format(name=name, kind="extension", keel=KEEL_REPO),
        "CHANGELOG.md": CHANGELOG.format(name=name),
        "changelog.d/README.md": FRAGMENTS,
        f"changelog.d/first-{name}.md": FIRST.format(name=name, kind="extension"),
    }


def language_files(name: str, schema: str) -> dict[str, str]:
    """A language package: its fragment, its `VERSION`, and the Python module the loader imports."""
    fragment = {
        "name": name,
        "core": core_range(schema),
        "order": 100,
        "family": name,
        "backends": {name: {"label": f"{title_of(name)} — TODO: the framework, in a few words",
                            "family": name}},
    }
    module = module_of(name)
    return {
        "language.json": json.dumps(fragment, indent=2, ensure_ascii=False) + "\n",
        "VERSION": "0.1.0\n",
        f"{module}/__init__.py": LANGUAGE_MODULE.format(name=name, module=module, title=title_of(name)),
        "README.md": LANGUAGE_README.format(name=name, title=title_of(name), command=this_command()),
        "Makefile": MAKEFILE.format(name=name, kind="language"),
        ".github/workflows/verify.yml": WORKFLOW.format(name=name, kind="language", keel=KEEL_REPO),
        "CHANGELOG.md": CHANGELOG.format(name=name),
        "changelog.d/README.md": FRAGMENTS,
        f"changelog.d/first-{name}.md": FIRST.format(name=name, kind="language"),
    }


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
        "README.md": TARGET_README.format(name=name, title=title_of(name), module=module,
                                          command=this_command()),
        "Makefile": MAKEFILE.format(name=name, kind="target"),
        ".github/workflows/verify.yml": WORKFLOW.format(name=name, kind="target", keel=KEEL_REPO),
        "CHANGELOG.md": CHANGELOG.format(name=name),
        "changelog.d/README.md": FRAGMENTS,
        f"changelog.d/first-{name}.md": FIRST.format(name=name, kind="target"),
    }


#: Which scaffold each kind gets. One mapping rather than a chain of `if kind ==`, because a fourth kind
#: should be a row here and nothing else.
SCAFFOLDS = {"extension": extension_files, "language": language_files, "target": target_files}
#: What a scaffold writes that is run rather than read, and so lands with its executable bit set. A script
#: a person has to `chmod` before it works is a script whose first run fails for a reason nothing said.
EXECUTABLE = {"extension": ("init.py",), "target": ("scripts/bootstrap.py", "scripts/deploy.py")}


def write(kind: str, name: str, into: Path, schema: str) -> list[str]:
    """Write the package under `into/<name>`, or refuse a directory that already holds something."""
    checked(kind, name)
    root = into / name
    if root.exists() and any(root.iterdir()):
        raise GenerationError(f"{root} already holds something. A scaffold writes a whole package, so it "
                              f"writes into an empty directory or none at all")
    files = SCAFFOLDS[kind](name, schema)
    for path, text in files.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    for path in EXECUTABLE.get(kind, ()):
        (root / path).chmod(0o755)
    return [f"{root / path}" for path in files]
