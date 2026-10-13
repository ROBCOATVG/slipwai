"""The backend protocol and the registry that holds every backend's answers to it.

`PROTOCOL` declares every per-backend answer a language gives, and which are required. A `Backend` or a
`Family` carries its `answers`, keyed by the `Member` constant; `Registry.answer` reads a backend's own
answer and otherwise its family's. Presence is the test, so `None` is an answer rather than a gap. `load`
refuses a registry the protocol cannot hold, in one line naming every fault at once rather than the first.

This module imports nothing from the answers or parts tiers, so a callable's signature stays loose here,
and it never imports a language: a package is found through the loader, by name, at call time. The shapes
are fixed in `docs/backend-protocol.md`, and `tests/test_registry.py` holds that page's member table to
`PROTOCOL` — the page and the code cannot drift.

`registry()` is the built-once-per-process entry point. Its body reaches for `slipwai.loaded` by name at
call time, not at import, which is what lets the catalogue import this module while the loader imports the
catalogue. The conformance suite builds its own with `load` instead, from one package and nothing else.
"""

from __future__ import annotations

import functools
import importlib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Generic, Literal, TypeVar, cast

from .assets import ROOT
from .family_only import refusals as family_only
from .renamed import MISSING, held

T = TypeVar("T")


class RegistryError(ValueError):
    """The registry, or the catalog it is held to, is wrong — said in one line."""


@dataclass(frozen=True)
class Member(Generic[T]):
    """One answer a backend gives: where it normally lives, who moves it, and the shape it must have."""

    name: str
    level: Literal["family", "backend"]
    required: bool
    kind: Any
    shape: str
    was: Member[Any] | None = None


# Declared, in the contract's order. A member is `required` only once every backend answers it; a new one
# arrives optional and flips in the commit that deletes the table it replaced. A renamed one carries `was`,
# the member it replaced, whose answer is read for the window `docs/backend-protocol.md` names (`renamed`).
M = Member  # a declaration is one line where it fits, so the protocol reads as the contract's table does
SERVICE_FILES: Member[Any] = M("service_files", "backend", True, Callable, "(event, selection, target) -> files")
NAME_SERVICE: Member[Any] = M("name_service", "backend", True, Callable, "(project, service, files) -> files")
REPOSITORY_FILES: Member[Any] = M("repository_files", "backend", True, Callable, "once per family -> files")
READY_PATH: Member[str] = M("ready_path", "backend", True, str, "the path answering send-me-traffic")
HEALTH_BODY: Member[str] = M("health_body", "backend", True, str, "the liveness body, as prose quotes it")
TOOLING: Member[Any] = M("tooling", "backend", True, dict, "backends.Tooling, fields unchanged")
FEATURE_TOOLING: Member[Any] = M("feature_tooling", "backend", True, dict, "feature -> tooling overrides")
EXECUTABLES: Member[Any] = M("executables", "backend", True, frozenset, "paths under APP")
DEV_COMMAND: Member[Any] = M("dev_command", "backend", True, Callable, "(qualifier, path, verify) -> str")
COMPOSE_CACHES: Member[Any] = M("compose_caches", "backend", True, tuple, "cache mounts")
EVENT_STORE_DIRECTORY: Member[Any] = M("event_store_directory", "backend", False, Callable, "(path) -> str")
PERSISTENCE_DIRECTORY: Member[Any] = M("persistence_directory", "backend", True, Callable, "(path) -> str",
                                       was=EVENT_STORE_DIRECTORY)
NATIVE_COMMANDS: Member[Any] = M("native_commands", "backend", True, Callable, "(path, verify) -> dict")
FORMATTER: Member[Any] = M("formatter", "family", True, (str, type(None)), "the format recipe line, or None")
IMAGE_BUILDER: Member[Any] = M("image_builder", "backend", True, dict, "the entry as today, no descriptor")
MIGRATIONS_IN_PRODUCTION: Member[Any] = M("migrations_in_production", "backend", True, dict, "as today")
POSTGRES_SSLMODE: Member[Any] = M("postgres_sslmode", "backend", True, dict, "database kind -> sslmode")
SERVICE_DESCRIPTORS: Member[Any] = M("service_descriptors", "backend", True, dict, "descriptor file -> text")
CI_TOOLCHAIN_SETUP: Member[Any] = M("ci_toolchain_setup", "family", True, Callable, "(services) -> str")
WRITE_SIDE_FILES: Member[Any] = M("write_side_files", "backend", True, dict, "feature -> asset -> path")
READ_SIDE_FILES: Member[Any] = M("read_side_files", "backend", True, dict, "feature -> asset -> path")
FLAG_READER: Member[Any] = M("flag_reader", "backend", True, object, "flags.FlagReader")
ENTRY_WIRING: Member[Any] = M("entry_wiring", "backend", True, dict, "HTTP option -> EntryWiring")
FLAG_RESOURCE: Member[Any] = M("flag_resource", "backend", True, dict, "HTTP option -> Resource")
ENTRY_STORE: Member[Any] = M("entry_store", "backend", True, object, "EntryStore, or None")
SHARED_CODE: Member[Any] = M("shared_code", "family", True, str, "the architecture page's paragraph")
GITIGNORE: Member[Any] = M("gitignore", "backend", True, str, "lines ending in a newline")
AGENT_PERMISSIONS: Member[Any] = M("agent_permissions", "backend", True, list, "permission entries")
GATE_DESCRIPTION: Member[Any] = M("gate_description", "backend", True, str, "what the gate runs, in prose")
EVENT_MODEL_PATHS: Member[Any] = M("event_model_paths", "backend", True, Callable, "(project, service) -> dict")
FAST_TARGETS: Member[Any] = M("fast_targets", "backend", False, tuple, "targets fast enough per increment")
MUTATION_TOOL: Member[Any] = M("mutation_tool", "backend", True, str, "the mutation tool's name")
PROCFILE: Member[Any] = M("procfile", "backend", True, (Callable, type(None)), "(project, service) -> str")
PIN_FILES: Member[Any] = M("pin_files", "family", True, dict, "path at the root -> text")
MAKEFILE_VARIABLES: Member[Any] = M("makefile_variables", "family", True, (Callable, type(None)), "(paths)")
RENOVATE_RULES: Member[Any] = M("renovate_rules", "family", True, tuple, "renovate.RenovateRules")
OPT_IN_FLAG_TRANSPORTS: Member[Any] = M("opt_in_flag_transports", "backend", True, frozenset, "targets")
# Never required: absence is the answer "nothing to say", read with `answer_or`.
MUTATION_NOTE: Member[Any] = M("mutation_note", "backend", False, str, "the note above make mutation")
IDENTITY_OUTSTANDING: Member[Any] = M("identity_outstanding", "family", False, dict, "feature -> what is owed")
MUTATION_SCOPING: Member[Any] = M("mutation_scoping", "backend", False, str, "the scoped-run paragraph")
NPM_WORKSPACE: Member[Any] = M("npm_workspace", "family", False, tuple, "npm_workspace.NpmWorkspace")
# A family and not a backend: a browser app is one more package in the workspace the family already owns, and
# two frameworks answering would be two dependency trees npm hoists into one (`docs/backend-protocol.md`).
BROWSER_APPS: Member[Any] = M("browser_apps", "family", False, dict, "frontend name -> npm_workspace.BrowserApp")
PRUNE_ROWS: Member[Any] = M("prune_rows", "family", True, dict, "marked, owned, package edits, manifest")

PROTOCOL: tuple[Member[Any], ...] = (
    SERVICE_FILES, NAME_SERVICE, REPOSITORY_FILES, READY_PATH, HEALTH_BODY, TOOLING, FEATURE_TOOLING, EXECUTABLES,
    DEV_COMMAND, COMPOSE_CACHES, PERSISTENCE_DIRECTORY, EVENT_STORE_DIRECTORY, NATIVE_COMMANDS, FORMATTER,
    IMAGE_BUILDER, MIGRATIONS_IN_PRODUCTION, POSTGRES_SSLMODE, SERVICE_DESCRIPTORS, CI_TOOLCHAIN_SETUP,
    WRITE_SIDE_FILES, READ_SIDE_FILES, FLAG_READER, ENTRY_WIRING, FLAG_RESOURCE, ENTRY_STORE, SHARED_CODE, GITIGNORE,
    AGENT_PERMISSIONS, GATE_DESCRIPTION, EVENT_MODEL_PATHS, FAST_TARGETS, MUTATION_TOOL, MUTATION_NOTE, PRUNE_ROWS,
    PROCFILE, PIN_FILES, MAKEFILE_VARIABLES, RENOVATE_RULES, OPT_IN_FLAG_TRANSPORTS, IDENTITY_OUTSTANDING,
    MUTATION_SCOPING, NPM_WORKSPACE, BROWSER_APPS,
)
# What core reads from a family itself and never through a backend (`family_answer`, a family's `answers`): a
# backend's answer to one is never read, so a backend that gives one its family does not is refused at load (A73).
# `formatter` is read so only for the family the browser app is written in: the one answering `npm_workspace`.
READ_PER_FAMILY: tuple[Member[Any], ...] = (PIN_FILES, RENOVATE_RULES, SHARED_CODE, NPM_WORKSPACE, BROWSER_APPS)
# What core reads through `Registry.answer` but once per family, from the family's first service (`ci_workflows.py`,
# `project/languages`, `native_commands.py`): a framework answering one differently from its family would be heard or
# ignored by service order, so it is refused at load (D113, D118 (6)). Of `tooling`, and of each `feature_tooling`
# entry, only these fields; a later MINOR that makes CI per service lifts the refusal for what it serves.
FAMILY_ONLY: tuple[Member[Any], ...] = (TOOLING, CI_TOOLCHAIN_SETUP, REPOSITORY_FILES, MAKEFILE_VARIABLES,
                                        FEATURE_TOOLING)


@dataclass(frozen=True)
class Family:
    """What every backend of one language shares: its name, and the answers written once for all of them."""

    name: str
    answers: Mapping[Member[Any], object] = field(default_factory=dict)


@dataclass(frozen=True)
class Backend:
    """One catalog backend: its key, the family it belongs to, and its own answers."""

    key: str
    family: str
    answers: Mapping[Member[Any], object] = field(default_factory=dict)


@dataclass(frozen=True)
class Language:
    """What one language module exports as `LANGUAGE`."""

    families: tuple[Family, ...] = ()
    backends: tuple[Backend, ...] = ()


@dataclass(frozen=True)
class Registry:
    """Every loaded family by name and backend by key. Built only by `load`; `roots` are set for a loaded package."""

    families: Mapping[str, Family]
    backends: Mapping[str, Backend]
    roots: Mapping[str, Path] = field(default_factory=dict)

    def root(self, owner: str) -> Path:
        """The directory holding `owner`'s `assets/`: its package's, else core's own for a built-in language."""
        return self.roots.get(owner, ROOT)

    def sources(self, key: str) -> tuple[Path, ...]:
        """Where `key`'s files are found, in order: its own root, then its family's where that is another one."""
        backend = self.backends.get(key)
        return tuple(dict.fromkeys((self.root(key), *(() if backend is None else (self.root(backend.family),)))))

    def answer(self, key: str, member: Member[T]) -> T:
        """The backend's own answer, else its family's, else the name it replaced; `None` is an answer."""
        backend = self.backends[key]
        found = held((backend, self.families.get(backend.family)), member)
        if found is MISSING:
            raise KeyError(f"backend {_n(key)} does not answer {_n(member.name)}")
        return cast(T, found)

    def family_answer(self, name: str, member: Member[T]) -> T:
        """A family's own answer, for what is read per family rather than per backend (`pin_files`, `shared_code`)."""
        return cast(T, self.families[name].answers[member])

    def answer_or(self, key: str, member: Member[T], default: T) -> T:
        """`answer`, or `default` where neither the backend nor its family answers: a member whose absence is one."""
        backend = self.backends[key]
        found = held((backend, self.families.get(backend.family)), member)
        return default if found is MISSING else cast(T, found)


def _n(name: object) -> str:
    """A name as a refusal shows it: bare, unless it has a character that would break the line, then quoted."""
    text = str(name)
    return text if text.isprintable() else repr(text)


def _kind_name(kind: Any) -> str:
    """What a member's kind is called in a refusal: `str`, or `str or NoneType` for a tuple of kinds."""
    return " or ".join(k.__name__ for k in kind) if isinstance(kind, tuple) else str(kind.__name__)


def _wrong(what: str, value: object, kind: str, show: bool = False) -> str:
    """One refusal for a value that is not what `load` reads it as: `what`, the kind found, and if asked the value."""
    return f"{what} is not {kind}, but {type(value).__name__}" + (f": {value!r}" if show else "")


def _unreadable(answers: object) -> str | None:
    """Why `load` cannot read these answers at all, or None: not a mapping, or one that raises when asked."""
    if not isinstance(answers, Mapping):
        return f"are not a mapping, but {type(answers).__name__}"
    try:
        _ = SERVICE_FILES in answers
        list(answers)
    except Exception as error:  # a mapping in name only: whatever it raises is the refusal, not a crash
        return f"cannot be read: {type(error).__name__}"
    return None


def _malformed_answers(owner: str, answers: object) -> list[str]:
    """What is wrong with one owner's answers: unreadable, or a key that is not a `Member`."""
    if (why := _unreadable(answers)) is not None:
        return [f"{owner} has answers that {why}"]
    keys = list(cast(Mapping[Any, object], answers))
    return [
        f"{owner} answers a key that is not a protocol member: {key!r}" for key in keys if not isinstance(key, Member)
    ]


def _not_a_sequence(what: str, value: object, verb: str = "that are") -> str:
    """One refusal for a value `load` reads as a sequence and is not."""
    return f"{what} {verb} not a sequence, but {type(value).__name__}"


def _is_sequence(value: object) -> bool:
    """A list or tuple of things, which a bare string, though iterable, is not."""
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))


def load(languages: Sequence[Language], protocol: tuple[Member[Any], ...] = PROTOCOL) -> Registry:
    """Collect the languages into a registry, or raise one `RegistryError` naming every fault at once."""
    if not _is_sequence(languages):
        raise RegistryError(_not_a_sequence("languages", languages, "are"))
    faults: list[str] = []
    families: dict[str, Family] = {}
    backends: dict[str, Backend] = {}
    claimed: dict[str, int] = {}  # the language (the package) declaring each family: its claim (C004, D45)
    origin: dict[str, int] = {}  # and the one declaring each backend
    for index, language in enumerate(languages):
        if not isinstance(language, Language):
            faults.append(_wrong(f"language {index}", language, "a Language"))
            continue
        if not _is_sequence(language.families):
            faults.append(_not_a_sequence(f"language {index} has families", language.families))
        if not _is_sequence(language.backends):
            faults.append(_not_a_sequence(f"language {index} has backends", language.backends))
        for family in language.families if _is_sequence(language.families) else ():
            if not isinstance(family, Family):
                faults.append(_wrong(f"a family in language {index}", family, "a Family"))
            elif not isinstance(family.name, str):
                faults.append(_wrong("a family's name", family.name, "a str", show=True))
            else:
                if family.name in families:
                    faults.append(f"family {_n(family.name)} is declared twice")
                faults += _malformed_answers(f"family {_n(family.name)}", family.answers)
                families[family.name] = family
                claimed[family.name] = index
        for backend in language.backends if _is_sequence(language.backends) else ():
            if not isinstance(backend, Backend):
                faults.append(_wrong(f"a backend in language {index}", backend, "a Backend"))
            elif not isinstance(backend.key, str):
                faults.append(_wrong("a backend's key", backend.key, "a str", show=True))
            elif not isinstance(backend.family, str):
                faults.append(
                    _wrong(f"backend {_n(backend.key)} names a family that", backend.family, "a str", show=True)
                )
            else:
                if backend.key in backends:
                    faults.append(f"backend {_n(backend.key)} is declared twice")
                faults += _malformed_answers(f"backend {_n(backend.key)}", backend.answers)
                backends[backend.key] = backend
                origin[backend.key] = index
    families = {name: f for name, f in families.items() if _unreadable(f.answers) is None}
    backends = {key: b for key, b in backends.items() if _unreadable(b.answers) is None}
    faults += [
        f"backend {_n(key)} names family {_n(backend.family)}, which no loaded language declares"
        for key, backend in backends.items()
        if backend.family not in families
    ]
    for owner, answers in [(f"family {_n(name)}", f.answers) for name, f in families.items()] + [
        (f"backend {_n(key)}", b.answers) for key, b in backends.items()
    ]:
        faults += [
            f"{owner} answers {_n(member.name)}, which the protocol does not declare"
            for member in answers
            if isinstance(member, Member) and member not in protocol
        ]
    for key, backend in backends.items():
        home = families.get(backend.family)
        for member in (m for m in protocol if m.required):
            value = held((backend, home), member)
            if value is MISSING:
                faults.append(f"backend {_n(key)} is missing {_n(member.name)}")
                continue
            if not isinstance(value, member.kind):
                faults.append(f"backend {_n(key)} answers {_n(member.name)} with {type(value).__name__}, "
                              f"where the protocol wants {_kind_name(member.kind)}")
    for key, backend in backends.items():
        faults += unread(key, backend, families.get(backend.family))
    faults += family_only(families, backends, claimed, origin, [member.name for member in FAMILY_ONLY])
    if faults:
        raise RegistryError("; ".join(faults))
    return Registry(families, backends)


def unread(key: str, backend: Backend, family: Family | None) -> list[str]:
    """A fault for each member `backend` answers that core reads only from its family, where the family does not."""
    if family is None:
        return []
    per_family = (*READ_PER_FAMILY, *((FORMATTER,) if NPM_WORKSPACE in family.answers else ()))
    return [
        f"backend {_n(key)} answers {_n(m.name)}, which core reads from family {_n(family.name)}, and the family "
        "does not answer it"
        for m in per_family if m in backend.answers and m not in family.answers
    ]


def _catalog_family(entry: object) -> object:
    """The family a catalog backend names, or None where it names none."""
    return entry.get("family") if isinstance(entry, Mapping) else None


def check_catalog(catalog: dict[str, Any], registry: Registry) -> None:
    """Refuse a catalog and a registry that disagree about the backends, in one line naming each direction."""
    listed: dict[str, Any] = catalog["backends"]
    faults = [
        f"backend {_n(k)} is in catalog.json with no registry object" for k in listed if k not in registry.backends
    ]
    faults += [
        f"backend {_n(k)} is in the registry but not in catalog.json" for k in registry.backends if k not in listed
    ]
    faults += [f"backend {_n(k)} has no family in catalog.json" for k in listed if _catalog_family(listed[k]) is None]
    faults += [
        f"backend {_n(key)} is family {_n(_catalog_family(listed[key]))} in catalog.json "
        f"and {_n(backend.family)} in the registry"
        for key, backend in registry.backends.items()
        if key in listed and _catalog_family(listed[key]) not in (None, backend.family)
    ]
    if faults:
        raise RegistryError("; ".join(faults))


@functools.cache
def registry() -> Registry:
    """Every package in the package directory, built once per process. `loaded` is reached by name at
    call time, not imported here: it reads the catalogue, the catalogue reads this module, and a static
    import either way round is a cycle."""
    return cast(Registry, importlib.import_module("slipwai.loaded").registry())
