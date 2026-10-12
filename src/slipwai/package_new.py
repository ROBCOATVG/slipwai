"""`slipwai package new`: a language or an extension package that loads on the first try.

Both kinds of package are a directory, a manifest and some files, and both have a shape the loader refuses
for reasons a publisher cannot guess from the outside — a `core` range, a module name derived from the
package's own, a `LANGUAGE` the fragment has to agree with, an entry point meeting six obligations. Version 1
had no scaffold for either, and every package anyone wrote started as a copy of one that already worked,
carrying whatever was wrong with it.

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
    QUICKSTART_README,
    README,
    WORKFLOW,
)

#: Where the reusable workflow a package's CI calls actually lives. Version 1's repository has a
#: `package.yml` too, with different inputs — a package pointed at it would fail on the first push with
#: inputs that workflow has never heard of. This becomes `ROBCOATVG/slipwai` when version 2 merges back
#: there (slice 8.5), and that row says so.
KEEL_REPO = "ROBCOATVG/slipwai_v2_Fork"
KINDS = ("extension", "language", "quickstart")
#: The publisher's verbs, in the order they are used.
VERBS = ("new", "check", "version", "release", "register", "key")
#: What a scaffolded manifest declares it needs: this keel's schema, and everything up to the next major.
def core_range(schema: str) -> str:
    major = schema.split(".")[0]
    return f">={schema},<{int(major) + 1}"


def title_of(name: str) -> str:
    """A key as a human name: `ux-gates` becomes `Ux gates`, which the publisher then edits."""
    return name.replace("-", " ").capitalize()


def module_of(name: str) -> str:
    return f"slipwai_language_{name.replace('-', '_')}"


def checked(kind: str, name: str) -> str:
    """The name, or the refusal that says what a package may be called."""
    if kind not in KINDS:
        raise GenerationError(f"a package is a {' or a '.join(KINDS)}; `--kind {kind}` is neither")
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


def write(kind: str, name: str, into: Path, schema: str) -> list[str]:
    """Write the package under `into/<name>`, or refuse a directory that already holds something."""
    checked(kind, name)
    root = into / name
    if root.exists() and any(root.iterdir()):
        raise GenerationError(f"{root} already holds something. A scaffold writes a whole package, so it "
                              f"writes into an empty directory or none at all")
    written = {"extension": extension_files, "language": language_files, "quickstart": quickstart_files}
    files = written[kind](name, schema)
    for path, text in files.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    if kind == "extension":
        (root / "init.py").chmod(0o755)
    return [f"{root / path}" for path in files]
