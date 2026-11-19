"""What an `extension.json` declares, and the six obligations an extension's entry point has to meet.

An extension is a package like a language is, and this is its half of the loader's contract. The difference
between the two kinds is narrow and worth stating: a language is asked at `slipwai generate`, to write the
skeleton; an extension is elected at `./init`, after the skeleton exists, and never changes generated code.
Everything else — found through the chandlery, signed, installed into a directory, loaded by the same loader
— is the same, which is why the manifests differ only in what they declare.

**The six obligations are not style.** Each is a failure somebody had.

1. **Replaceably idempotent.** Running `./init --extension <key>` twice does what running it once did.
   Anything else makes "did it work?" into "how many times has it run?".
2. **Installs what it needs, and is non-fatal when it cannot.** A dev tool that is not on this machine is
   not a reason a project cannot be set up. It says what is missing and the project still works.
3. **Projects a marker-fenced block into `AGENTS.md`.** Fenced, so the next projection replaces exactly
   that block and leaves what a person wrote around it.
4. **Gates whatever state can go stale.** An extension that writes an index, a cache or a lock ships a
   `check-<key>.py`, because stale state that nothing checks is state nobody trusts and everybody rebuilds.
5. **Names a recovery command on every failure path.** The house rule for every refusal in this repository:
   a message saying what is wrong and not what to do about it costs the reader a search.
6. **Merges rather than overwrites a file a person hand-edited.** Anything else means a person's edit is
   lost by an install they ran for an unrelated reason, which is how a tool becomes something people avoid
   running.
"""
from __future__ import annotations

from .extension_tools import declared as declared_tools
from .guards import declared as declared_guards
from .hooks import declared as declared_hooks
from .language_shape import name_fault

KIND = "extension"
#: What every extension's manifest declares. `key` is what a person types — `./init --extension <key>` — and
#: what the directory is called; `name` is what the menu shows, which is a product's name and not a slug.
#: Separating them is the one thing a language's manifest does not have to do, because a language's name is
#: both. `core` is the keel range, as a language's manifest carries.
REQUIRED = ("key", "name", "description", "kind", "core")
#: Declarable and not required. `ignore` is the gitignore text its local state needs — version 1's catalogue
#: entry carried exactly this and nothing else, which is why it is still spelled the same.
OPTIONAL = ("ignore", "publisher", "tags", "hooks", "guards", "tools", "withhold", "writes")
#: The six, in the order `docs/extensions.md` sets them, each as the conformance suite names its check.
OBLIGATIONS = (
    ("idempotent", "running it twice does what running it once did"),
    ("non-fatal", "a tool it cannot install is said, not fatal"),
    ("projects", "its AGENTS.md block is marker-fenced and replaced whole"),
    ("gated", "state that can go stale ships a check-<key>.py"),
    ("recovers", "every failure path names the command that fixes it"),
    ("merges", "a hand-edited file is merged, never overwritten"),
)


def validate(manifest: dict) -> None:
    """An `extension.json`, or a refusal naming the field and what it is for.

    Checked here rather than at election time: a manifest that is wrong is wrong on the publisher's machine,
    where they can fix it, and discovering it at `./init` makes it somebody else's problem entirely.
    """
    if not isinstance(manifest, dict):
        raise ValueError("an extension.json is an object")
    for field in REQUIRED:
        if not isinstance(manifest.get(field), str) or not manifest[field].strip():
            raise ValueError(f"an extension declares a non-empty `{field}`; this one does not")
    if (fault := name_fault("extension", manifest["key"])) is not None:
        raise ValueError(f"{fault}. The key becomes a directory and part of `./init --extension <key>`, so it "
                         f"is held to what both allow; `name` is where the product's own name goes")
    if manifest["kind"] != KIND:
        raise ValueError(f"`kind` is `{KIND}` for an extension; this one says `{manifest['kind']}`. A "
                         f"language declares `language.json` instead, and the loader reads the two apart")
    if "ignore" in manifest and not isinstance(manifest["ignore"], str):
        raise ValueError("`ignore` is gitignore text, as a string, for whatever local state this leaves")
    if "tags" in manifest and not (isinstance(manifest["tags"], list)
                                   and all(isinstance(tag, str) for tag in manifest["tags"])):
        raise ValueError("`tags` is a list of strings, which is what `slipwai search` matches against")
    unknown = set(manifest) - set(REQUIRED) - set(OPTIONAL)
    if unknown:
        raise ValueError(f"an extension declares {', '.join(sorted(unknown))}, which the keel does not read. "
                         f"It may declare: {', '.join(sorted({*REQUIRED, *OPTIONAL}))}")
    declared_hooks(manifest)
    # The second closed set, checked the same way and for the same reason: a guard the keel has not
    # got would leave the extension installed, the manifest valid, and nothing happening for ever.
    declared_guards(manifest)
    # `tools` is not a closed set — a tool name is the harness's spelling, not the keel's — so only its
    # shape is held. What it buys is 6.1c: the tool name belongs to whoever brings the tool, rather than
    # sitting in the keel's harness registry where every project is handed it, elected or not.
    declared_tools(manifest)
    # What a project is not given of the package, beyond the conventional repository-only paths (#119).
    withheld(manifest)
    # What it writes in a project outside its own directory, so an un-election can name what is left (#119).
    written(manifest)


#: What a manifest names its own repository-only paths under.
WITHHOLD = "withhold"


def withheld(manifest: dict) -> tuple[str, ...]:
    """The paths a manifest adds to what a project is not given of the package (`extension_given`), or a
    refusal saying what one is."""
    block = manifest.get(WITHHOLD)
    if block is None:
        return ()
    wrong = (f"`{WITHHOLD}` is a list of paths inside the package that a project is not given, each relative to the "
             f"package root with `/` between its parts, a folder ending in `/`")
    if not isinstance(block, list):
        raise ValueError(wrong)
    for rule in block:
        if not isinstance(rule, str) or not rule.strip() or "\\" in rule or rule.startswith("/") \
                or ".." in rule.split("/"):
            raise ValueError(f"{wrong}; `{rule}` is not one")
    return tuple(rule.strip() for rule in block)


#: What a manifest names the project paths it writes outside its own directory under.
WRITES = "writes"


def written(manifest: dict) -> tuple[str, ...]:
    """The paths an extension says it writes in a project outside `scripts/extensions/<key>/`, in one order, or a
    refusal saying what one is.

    Declared, not observed: the keel does not watch what a hook does, so this is the extension's own word, and
    the record an un-election reads to name what is still there. A file the extension shares with others —
    `AGENTS.md`, a harness's MCP file — is not one of these; it holds an entry, and the `remove` hook takes
    that back."""
    block = manifest.get(WRITES)
    if block is None:
        return ()
    wrong = (f"`{WRITES}` is a list of the paths this extension writes in a project outside its own directory, "
             f"each relative to the project root with `/` between its parts")
    if not isinstance(block, list):
        raise ValueError(wrong)
    own = f"scripts/extensions/{manifest.get('key')}/"
    for path in block:
        if not isinstance(path, str) or not path.strip() or "\\" in path or path.startswith("/") \
                or ".." in path.split("/") or path.strip().startswith(own):
            raise ValueError(f"{wrong}; `{path}` is not one")
    return tuple(sorted({path.strip() for path in block}))


def catalogue_entry(manifest: dict) -> dict:
    """What the loader merges into `CATALOG["extensions"]`, which `./init`'s menu already reads.

    Only the three fields the menu has ever used. An extension's manifest carries more than the catalogue
    needs — its publisher, its hooks, its keel range — and merging all of it would make a menu that renders
    whatever the newest manifest happened to add.
    """
    entry = {"name": manifest["name"], "description": manifest["description"]}
    if manifest.get("ignore"):
        entry["ignore"] = manifest["ignore"]
    return entry


def obligations() -> tuple[str, ...]:
    """The names the conformance suite reports, in order."""
    return tuple(name for name, _ in OBLIGATIONS)
