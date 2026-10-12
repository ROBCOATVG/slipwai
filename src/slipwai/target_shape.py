"""What a `target.json` declares: the third manifest, and the declaration half of a target package.

A target is a package the way a language and an extension are. Its manifest carries exactly the row
`catalog.json` has always held for a cloud — the label a prompt shows, the axes the target cannot take the
no-infrastructure answer to, the words its cloud refuses inside a project's name, and whether the keel
provisions it at all — so a target arriving as a package adds a row to those tables rather than a second
set of branches. The executable half is the `TARGET` object (`target_protocol.py`); this is what can be
read without importing anything of the package.

**Checked on the publisher's machine.** The same rule the other two manifests are held by: a manifest that
is wrong is wrong where it was written, and finding it out at `slipwai generate` makes it the fault of
somebody who only wanted a project.

**The reserved-word classes are `targets.py`'s, not a second spelling of them.** A cloud does not always
refuse a word the same way, and the three classes a catalog row may use are declared once, where the check
that applies them to a project's name lives.

**`none` is not a name a package may take.** Local only is the one row every catalog carries and the answer
an axis always has somewhere to fall back to; a package claiming that name would replace it.
"""
from __future__ import annotations

from typing import Any

from .language_shape import name_fault, strings
from .targets import RESERVED_CLASSES, RESERVED_WORD

KIND = "target"
#: The name the keel keeps for itself: local only, which every catalog carries and no package provides.
LOCAL_ONLY = "none"
#: What every target's manifest declares. `name` is the key the catalog's `targets` block lists it under and
#: what `--target <name>` is typed as; `label` is the sentence the prompt shows, which is a cloud's own prose
#: and not a slug. `core` is the keel range, as both the other manifests carry.
REQUIRED = ("name", "label", "description", "kind", "core")
#: Declarable and not required. The four that make a catalog row, what a listing shows, and the three that
#: say what this target does to the *menus*: the keel answers it offers, what each of them is provisioned as
#: there, and the answers that are its own. Those three are why a cloud can leave the keel at all — every
#: option that named a cloud named it because the cloud offered it, and that is the cloud's statement to make.
OPTIONAL = ("managed", "requires", "reserved", "publisher", "tags", "offers", "provisions", "axes")


def validate(manifest: dict) -> None:
    """A `target.json`, or a refusal naming the field and what it is for."""
    if not isinstance(manifest, dict):
        raise ValueError("a target.json is an object")
    for field in REQUIRED:
        if not isinstance(manifest.get(field), str) or not manifest[field].strip():
            raise ValueError(f"a target declares a non-empty `{field}`; this one does not")
    if (fault := name_fault(KIND, manifest["name"])) is not None:
        raise ValueError(f"{fault}. The name becomes a directory and part of `--target <name>`, so it is "
                         f"held to what both allow; `label` is where the cloud's own prose goes")
    if manifest["name"] == LOCAL_ONLY:
        raise ValueError(f"`{LOCAL_ONLY}` is local only — the one target every catalog carries and the answer "
                         f"an axis always falls back to — so no package may be called it")
    if manifest["kind"] != KIND:
        raise ValueError(f"`kind` is `{KIND}` for a target; this one says `{manifest['kind']}`. A language "
                         f"declares `language.json` and an extension `extension.json`, and the loader reads "
                         f"the three apart")
    if not isinstance(manifest.get("managed", False), bool):
        raise ValueError("`managed` is true where the keel provisions this target — its stacks, its images, "
                         "its pipeline — and false where a project deploys somewhere the keel does not own")
    if not strings(manifest.get("requires", [])):
        raise ValueError("`requires` is a list of the axes this target cannot take the no-infrastructure "
                         "answer to, as `aws` requires `http`: a deploy nothing can prove is not a deploy")
    reserved_fault(manifest)
    if "tags" in manifest and not strings(manifest["tags"]):
        raise ValueError("`tags` is a list of strings, which is what `slipwai search` matches against")
    menu_fault(manifest)
    if unknown := set(manifest) - set(REQUIRED) - set(OPTIONAL):
        raise ValueError(f"a target declares {', '.join(sorted(unknown))}, which the keel does not read. "
                         f"It may declare: {', '.join(sorted({*REQUIRED, *OPTIONAL}))}")


def reserved_fault(manifest: dict) -> None:
    """The reserved block, held to the three classes and the words a project's name could actually carry.

    The same three checks `targets.validate_targets` makes of a catalog row, made here instead because a
    package's row never passes through a hand-written catalog: the publisher is the only person who can fix
    a cloud's refusal list, and the fault has to reach them rather than the project that installed it.
    """
    reserved = manifest.get("reserved", {})
    name = manifest["name"]
    if not isinstance(reserved, dict) or not set(reserved) <= set(RESERVED_CLASSES):
        raise ValueError(f"`reserved` is a mapping from how a word is refused ({', '.join(RESERVED_CLASSES)}) "
                         f"to the words refused that way: a cloud that refuses `{name}` anywhere in a name "
                         f"and `login` only at the start cannot say so with one flat list")
    for how, words in reserved.items():
        if not strings(words) or not words:
            raise ValueError(f"`reserved`'s {how} words are a non-empty list of strings, or the class is left out")
        if not all(RESERVED_WORD.fullmatch(word) for word in words):
            raise ValueError(f"`reserved`'s {how} words are lowercase alphanumeric words, separated by '.', "
                             f"'_' or '-' as a project name may be, each one a name may not carry")
    if any(reserved.values()) and not manifest.get("managed"):
        raise ValueError(f"target {name} provisions nothing, so it names nothing after the project and "
                         f"reserves no words")


def catalogue_entry(manifest: dict) -> dict[str, Any]:
    """The row the catalog's `targets` block gets for it: the four fields it has ever held, and no more.

    What is not declared is left out rather than written empty, because a row carrying `"requires": []`
    reads as a decision somebody made about this target and an absent key does not.
    """
    entry: dict[str, Any] = {"label": manifest["label"]}
    if manifest.get("requires"):
        entry["requires"] = list(manifest["requires"])
    if manifest.get("reserved"):
        entry["reserved"] = {how: list(words) for how, words in manifest["reserved"].items() if words}
    if manifest.get("managed"):
        entry["managed"] = True
    return entry


def menu_fault(manifest: dict) -> None:
    """The three blocks that say what this target does to the menus, held to their shapes and no further.

    *Which* axis and *which* option is a fact about the keel that reads the manifest, not about the manifest,
    so it is checked at the merge and not here: a target built against a keel that declared `auth` is not
    wrong on the publisher's machine because this keel renamed the axis. What is wrong here is a block that
    could not be read at all, whatever the keel.
    """
    offers = manifest.get("offers", {})
    if not isinstance(offers, dict) or not all(strings(options) for options in offers.values()):
        raise ValueError("`offers` is a mapping from an axis to the keel options this target offers under "
                         "it: an option named a cloud because the cloud offered it, and that is the cloud's "
                         "to say")
    provisions = manifest.get("provisions", {})
    if not isinstance(provisions, dict) or not all(
        isinstance(options, dict) and all(isinstance(as_what, str) and as_what for as_what in options.values())
        for options in provisions.values()
    ):
        raise ValueError("`provisions` is a mapping from an axis to what each option becomes here, as "
                         "`{\"persistence\": {\"postgres\": \"rds\"}}`: provisioning an option offers it")
    axes = manifest.get("axes", {})
    if not isinstance(axes, dict) or not all(
        isinstance(options, dict) and all(isinstance(option, dict) for option in options.values())
        for options in axes.values()
    ):
        raise ValueError("`axes` is a mapping from an axis to the options this target brings itself, each "
                         "one the entry the catalogue's `options` block holds: an answer that exists only "
                         "where this target is installed belongs to it and not to the keel")
    if axes and not manifest.get("managed"):
        raise ValueError(f"target {manifest['name']} provisions nothing, so it brings no answer of its own: "
                         f"an option offered only here would be one nothing here could build")
