"""`slipwai list` and `slipwai language list|install|upgrade|remove`: what this copy can do, and its languages.

`list` is every section a project maker chooses from — languages, frontends, targets, axes, extensions, and what
adoption does with no language at all — and takes no argument. `language list` is its first section.
Each row that is not installed names the command that installs it, as this machine would run it. An index that cannot
be read is said, with the local-source form, and what is installed is still shown: never an empty list.
"""
from __future__ import annotations

import argparse
from collections.abc import Callable

from .browser_app import frontend_rows
from .catalog import CATALOG, UNREACHABLE_NOTES, families
from .errors import GenerationError, refuse
from .index_schema import LANGUAGE
from .language_directory import directory
from .language_index import Index, Release, Unreachable, offered, read_index, snapshots
from .language_install import builtin, installed, this_command
from .language_plan import SCHEMA, answers, install, local_form, needs_newer_core, no_release
from .language_upkeep import remove, upgrade
from .loaded import refusals
from .registry import registry
from .targets import offered_backends
from .versions import key

ADOPTION = (
    "  slipwai adopt installs the delivery method around a repository this factory did not make, whatever its "
    "languages,\n  with no language installed. slipwai converge, which ends an adoption, is the verb that needs the "
    "language of each\n  service it reads as generated."
)


def reach(prerelease: bool, kind: str | None = LANGUAGE) -> tuple[Index | None, dict[str, Release], list[str]]:
    """The index, what it offers this keel of one `kind`, and the lines saying it could not be read.

    The languages' kind by default, because every caller here lists those and the index lists four: without
    it a target arrived as a language — a target's manifest names no `family`, so `family == name` let it
    through — and `slipwai list` offered `language install` for a cloud. The packages tab passes `None`.
    """
    try:
        found = read_index()
    except Unreachable as error:
        return None, {}, [f"  {error}", f"  install from a local source: {local_form()}"]
    return found, offered(found, SCHEMA, prerelease, kind), []


def grouped(rows: dict[str, tuple[str, str]]) -> list[str]:
    """`name → (family, text)` as lines, each framework two spaces under its family's row."""
    order = list(registry().families)
    families = sorted({family for family, _ in rows.values()}, key=lambda f: (order.index(f) if f in order else 99, f))
    lines: list[str] = []
    for family in families:
        lines.append(f"    {rows[family][1]}" if family in rows else f"    {family}  (not installed)")
        lines += [f"      {text}" for name, (owner, text) in sorted(rows.items()) if owner == family and name != family]
    return lines


def languages_section(prerelease: bool) -> tuple[list[str], dict[str, Release], Index | None]:
    """The languages: installed (built in, loaded or refused), then what the index offers that is not installed."""
    found, offer, unreachable = reach(prerelease)
    have, built = installed(directory()), builtin()
    refused = {line.split(" ", 2)[1]: line for line in refusals() if line.startswith("language ")}
    rows: dict[str, tuple[str, str]] = {name: (family, f"{name}  built in") for name, family in built.items()}
    for name, package in have.items():
        text = f"{name} {package.version}"
        if name in refused:
            text += f"  refused: {refused[name]}"
        newer = offer.get(name)
        if newer is not None and key(newer.version) > key(package.version):
            text += f"  ({newer.version} available: {this_command()} language upgrade {name})"
        rows[name] = (package.family or name, text + UNREACHABLE_NOTES.get(name, ""))
    lines = [f"  installed (in {directory()}):", *grouped(rows)]
    if found is None:
        return [*lines, *unreachable], offer, None
    shown = {name: (str(release.fragment.get("family", name)),
                    f"{name} {release.version} — {this_command()} language install {name}")
             for name, release in offer.items() if name not in have and name not in built}
    lines.append(f"  available from the language index at {found.url}:")
    nothing = ["    nothing this core can load that is not installed"]
    return [*lines, *(grouped(shown) if shown else nothing)], offer, found


def answering(offer: dict[str, Release], axis: str, option: str) -> list[str]:
    """The offered languages one of whose backends answers this axis option."""
    return [name for name, release in offer.items()
            if any(option in (row.get("options", {}).get(axis, []) if isinstance(row, dict) else [])
                   for row in (release.fragment.get("backends") or {}).values())]


def axes_section(offer: dict[str, Release]) -> list[str]:
    lines: list[str] = []
    for axis, spec in CATALOG["axes"].items():
        lines.append(f"  {axis} — {spec['prompt']}")
        for option, row in spec["options"].items():
            if row["backends"] or option == spec["absent"]:
                lines.append(f"    {option}" + (f" — {', '.join(row['backends'])}" if row["backends"] else ""))
                continue
            names = [name for name in answering(offer, axis, option) if name not in installed(directory())]
            would = "; ".join(f"{name} answers it: {this_command()} language install {name}" for name in names)
            lines.append(f"    {option} — no installed language answers it" + (f"; {would}" if would else ""))
    return lines


def everything(prerelease: bool) -> str:
    languages, offer, found = languages_section(prerelease)
    extensions = [f"  {name} — {spec['name']}" for name, spec in CATALOG["extensions"].items()]
    return "\n".join([
        "Languages", *languages, "", "Frontends", *frontend_rows(found, offer), "",
        "Targets", *[f"  {name} — {spec['label']}" for name, spec in CATALOG["targets"].items()], "",
        "Axes", *axes_section(offer), "", "Extensions (chosen at ./init --extension <key>)", *extensions, "",
        "Adoption (no language needed)", ADOPTION,
    ])


def braced(names: object) -> str:
    """The `{a,b}` argparse shows for a list of choices, for a flag that checks its own value."""
    return "{" + ",".join(str(name) for name in names) + "}"  # type: ignore[attr-defined]


def provider(test: Callable[[Release], bool]) -> tuple[Index | None, Release | None, str | None]:
    """The index, the first release it offers that passes `test`, and why it could not be asked (or None)."""
    try:
        found = read_index()
    except Unreachable as error:
        return None, None, str(error)
    return found, next((r for r in offered(found, SCHEMA, snapshots()).values() if test(r)), None), None


def backends_of(release: Release) -> dict[str, object]:
    rows = release.fragment.get("backends")
    return rows if isinstance(rows, dict) else {}


def refused_line(name: str) -> str | None:
    """The loader's line for the installed package `name`, where it refused it."""
    return next((line for line in refusals() if line.startswith(f"language {name} (")), None)


def refused_providing(test: Callable[[str, dict], bool]) -> str | None:
    """The loader's line for an installed package `test` accepts (by name and `language.json`) that it refused: such a
    package is installed, and its line names the fix — never the install line, which says "already installed"."""
    for name, have in installed(directory()).items():
        if test(name, have.fragment or {}) and (line := refused_line(name)) is not None:
            return f"is installed and the loader refused it — {line}"
    return None


def held(found: Index, name: str) -> str:
    """The ending for a language the index has only for another the keel schema, by direction."""
    said = no_release(found, name, snapshots())
    return f" and is held back: {said}" if needs_newer_core(found, name, snapshots()) else f", and {said}"


def provided(family: str) -> str:
    """A backend the index offers: a framework of a family loaded or installed (alone too, A106), or not."""
    if family in families() or family in installed(directory()):
        return f"a {family} framework that is not installed"
    return f"provided by the {family} language, which is not installed"


def missing_backend(key: str) -> str:
    """FR-015: `--backend <key>` with nothing installed providing it — the language that does, and its install line."""
    refused = refused_providing(lambda name, fragment: name == key or key in (fragment.get("backends") or {}))
    if refused is not None:
        return f"--backend {key} {refused}"
    found, release, unreachable = provider(lambda release: key in backends_of(release))
    if release is not None:
        family = str(release.fragment.get("family", release.name))
        return f"--backend {key} is {provided(family)}: {this_command()} language install {release.name}"
    nobody = f"--backend {key} is not a backend any installed language provides"
    other = next((r for rs in (found.releases.values() if found else []) for r in rs if key in backends_of(r)), None)
    if found is not None and other is not None:
        return f"--backend {key} is {provided(str(other.fragment.get('family', other.name)))}{held(found, other.name)}"
    if found is None:
        family = key.rpartition("-")[0]
        by_name = (f"A package is installed by its own name, which is the backend's ({this_command()} language "
                   f"install {key}) or, for a package of several frameworks, its family's ({this_command()} language "
                   f"install {family})" if family else
                   f"A backend's package is installed by the backend's own name: "
                   f"{this_command()} language install {key}")
        return (f"{nobody}, and {unreachable}, so which language provides it cannot be said. {by_name}; from a local "
                f"source: {local_form()}")
    return (f"{nobody}, and the language index at {found.url} offers none: {this_command()} list shows what can be "
            f"installed (installed: {', '.join(CATALOG['backends']) or 'none'})")


def missing_language(name: str) -> str:
    """FR-015 for `--language <name>`."""
    if (refused := refused_providing(lambda installed_name, _: installed_name == name)) is not None:
        return f"--language {name} {refused}"
    found, release, unreachable = provider(lambda release: release.name == name)
    if release is not None:
        return f"--language {name} is not installed: {this_command()} language install {name}"
    if found is None:
        return (f"--language {name} is not installed, and {unreachable}: {this_command()} language install {name}; "
                f"from a local source: {local_form()}")
    if name in found.releases:
        return f"--language {name} is not installed{held(found, name)}"
    return (f"--language {name} is not a language any installed package provides, and the language index at "
            f"{found.url} offers none: {this_command()} list shows what can be installed")


def missing_framework(language: str, framework: str) -> str | None:
    """FR-015 for `--framework` of an installed family: the framework's own install line, or None where the index
    offers no such framework (the caller's own refusal then says what the family can be given)."""
    if (refused := refused_providing(lambda _, row: row.get("family") == language and answers(row, framework))):
        return f"--framework {framework} of {language} {refused}"
    found, release, unreachable = provider(lambda r: r.fragment.get("family") == language
                                           and answers(r.fragment, framework))
    if release is not None:
        line = f"{this_command()} language install {release.name}"
        return f"--framework {framework} is not installed for {language}: {line}"
    if found is None:
        return (f"--framework {framework} is not one installed for {language}, and {unreachable}: install it from a "
                f"local source: {local_form()}")
    return None


def list_main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(
        prog="slipwai list", description="What this slipwai can generate: languages, frontends, targets, axes and "
        "extensions, and what adoption does with no language")
    parser.add_argument("--pre", action="store_true", help="count snapshots in the index (implied on a snapshot)")
    args = parser.parse_args(argv)
    print(everything(snapshots(args.pre)))


def run(verb: Callable[..., list[str]], requests: list[str], prog: str, **options: object) -> None:
    try:
        lines = verb(requests, directory(), **options)
    except GenerationError as error:
        refuse(prog, error)
    print("\n".join(lines))


def language_main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(
        prog="slipwai language", description="List, install, upgrade or remove the languages this slipwai generates",
        epilog="A name is fetched from the language index (SLIPWAI_INDEX, else the uv receipt's, else the default); a "
        "path — a release file (<name>-<version>.tar.gz) or a package directory — is a local source, installed "
        "with no network. docs/languages.md has the whole of it.")
    verbs = parser.add_subparsers(dest="verb", required=True, metavar="list|install|upgrade|remove")
    listed = verbs.add_parser("list", help="installed languages, and the compatible ones the index offers")
    for name, help_text in (("install", "install languages, with the family a framework needs and the framework a "
                             "family defaults to"), ("upgrade", "upgrade installed languages"),
                            ("remove", "remove installed languages")):
        sub = verbs.add_parser(name, help=help_text)
        sub.add_argument("names", nargs="+", metavar="NAME|PATH", help="a language's name, or a local source's path")
        if name != "remove":
            sub.add_argument("--pre", action="store_true", help="count snapshots in the index")
    listed.add_argument("--pre", action="store_true", help="count snapshots in the index")
    args = parser.parse_args(argv)
    prog = f"slipwai language {args.verb}"
    if args.verb == "list":
        print("\n".join(["Languages", *languages_section(snapshots(args.pre))[0]]))
    elif args.verb == "install":
        run(install, args.names, prog, prerelease=snapshots(args.pre))
    elif args.verb == "upgrade":
        run(upgrade, args.names, prog, prerelease=snapshots(args.pre))
    else:
        run(remove, args.names, prog)



def nothing_to_generate(loaded: list[str]) -> str | None:
    """What `generate` says, before its first question, when no language is loaded: there is nothing it could
    generate an answer to, so it asks nothing (Story 3 scenario 9). None while any language is loaded."""
    if loaded:
        return None
    found, offer, unreachable = reach(snapshots())
    none = [f"  the language index at {found.url} offers none this core can load"] if found is not None else []
    said = unreachable if found is None else install_lines(offer) or none
    return "\n".join(["no language is installed, so there is nothing to generate yet; install one:", *said])


def install_lines(offer: dict[str, Release]) -> list[str]:
    """Each release's install line, indented under a refusal that ends "install one:" (D116 #6)."""
    return [f"  {name} {release.version} — {this_command()} language install {name}" for name, release in offer.items()]


def no_framework(family: str) -> str:
    """A family installed with no framework beside it (D116 #1): the install line of the package answering its
    `default_framework` — `<family>-<framework>`, read from its `language.json` — or, where the index is reachable and
    offers no such package or the family names no default, each framework the index offers, one line each."""
    if (refused := refused_providing(lambda name, fragment: fragment.get("family") == family != name)) is not None:
        return f"{family} has no framework loaded: its framework {refused}"  # installed: not an install line
    said, default = f"{family} has no framework installed", (getattr(installed(directory()).get(
        family), "fragment", None) or {}).get("default_framework")
    found, offer, unreachable = reach(snapshots())
    offered = {name: release for name, release in offer.items()
               if release.fragment.get("family") == family and name != family}
    if isinstance(default, str):
        if found is None:
            return f"{said}; {this_command()} language install {family}-{default}; {unreachable[0].strip()}; from a " \
                   f"local source: {local_form()}"
        named = next((name for name, release in offered.items() if answers(release.fragment, default)), None)
        if named is not None:
            return f"{said}; {this_command()} language install {named}"
    if found is None:
        return f"{said}, and {unreachable[0].strip()}: install one from a local source: {local_form()}"
    if not offered:
        return f"{said}, and the language index at {found.url} offers none for it: install one from a local source: " \
               f"{local_form()}"
    return "\n".join([f"{said}; install one:", *install_lines(offered)])


def nothing_loaded() -> str:
    """Why there is no backend to generate on: a family alone (its framework's line), an installed package the loader
    refused (named as refused, with its line), or nothing installed (each offered language's install line)."""
    alone = [family for family in registry().families if family not in families()]
    if len(alone) > 1:  # one refusal in D116 #6's shape: every family's candidates indented under it
        said = [no_framework(family).splitlines() for family in alone]
        return "\n".join([f"{', '.join(alone)} have no framework installed; install one:",
                          *(line for lines in said for line in (lines[1:] if len(lines) > 1 else [f"  {lines[0]}"]))])
    if alone:
        return no_framework(alone[0])
    refused = [line for line in refusals() if line.startswith("language ")]
    if refused:
        return "no language is loaded: " + "; ".join(
            f"{line.split(' ', 2)[1]} is installed and the loader refused it — {line}" for line in refused)
    return str(nothing_to_generate([]))


def undeclared_target(target: str) -> str | None:
    """`--target <t>` no loaded backend declares (D116 #5): the ones they do; None with none loaded at all."""
    if not CATALOG["backends"] or offered_backends(CATALOG, target):
        return None
    declared = [name for name in CATALOG["targets"] if offered_backends(CATALOG, name)]
    return f"--target {target} is not one any installed backend declares; they declare {', '.join(declared)}"
