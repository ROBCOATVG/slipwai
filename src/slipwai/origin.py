"""How a repository came to have the factory's material, and the facts an adoption recorded about what was there.

A generated project has no origin to speak of: the factory made it, and `project.json` says nothing. An
adopted one — the method installed around code that already existed (experimental as `AGENTS.md`
defines the word) — records `"origin": "adopted"` and, beside the applications it wrapped, what the survey
found and the person confirmed about the repository as a whole: why the work is being done, where the
database schema is versioned, where the deployment infrastructure is described, and what else the tree
carried. Each of the two homes is one of `here`, `elsewhere`, `unmanaged` or `none`, with provenance, and
`elsewhere` names the repository, because that is the one answer the tree cannot give.

Written once by `adopt`, read back by every command that regenerates the manifest — `replay`, `add-service` —
so that the record survives them byte for byte, and read by the pages that explain the adoption.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .errors import GenerationError

ORIGINS = ("generated", "adopted")
HOMES = ("here", "elsewhere", "unmanaged", "none")
# Which forge runs CI, which decides what shape the gate's CI configuration can take: an Actions workflow for
# `github` and `gitea` (Gitea and Forgejo run the same files), an includable job for `gitlab`, nothing the
# factory can write for `other`, and `none` where the repository has no CI at all.
FORGES = ("github", "gitea", "gitlab", "other", "none")
# How a change reaches production today — the first Minimum CD fact, and one the tree only sometimes says.
# `unknown` is recorded as such, with `unrecorded` provenance, rather than guessed at.
RELEASE_PATHS = ("pipeline", "scripted", "manual", "unknown")
# What a wrapped application can be recorded as. `application` is the one that says nothing: a buildable
# directory whose role the tree did not give away and nobody has said — kept open, with `unrecorded` provenance.
WRAPPED_KINDS = ("service", "library", "tool", "tests", "application")
# How this repository changes, recommended by `strategy.py` and decided by an ADR. `in-place` climbs the ladder's
# rungs without moving the architecture; the two beside it are Fowler's patterns; *leave it* is an answer like any
# other. Named here rather than in `strategy.py`, which reads this module.
STRATEGIES = ("leave-it", "in-place", "modular-monolith", "strangler-fig", "rewrite")
# What the same strategies were called up to 1.12, when the axis was `modernisation`: read, never written.
OLD_STRATEGIES = {"modernise-in-place": "in-place"}
# What an axis was called by an older factory, mapped forward as the manifest is read so that everything which
# writes the manifest again — `replay`, `add-service`, `migrate`, not only `/survey` — writes the current name.
# A row left under the old name would fail the shipped `check-convergence`, which knows only the current rungs.
OLD_AXES = {"modernisation": "strategy"}


@dataclass(frozen=True)
class Adoption:
    """The project-level facts of an adopted repository, as `project.json` records them after `layout`."""

    # The business trigger — end-of-life runtime, cloud exit, cannot hire, cannot ship — recorded like a
    # service's `purpose`: it decides the change strategy more than the code does.
    why: str | None = None
    # `{"schema": home, "tools": [...], "drivers": [...], "repository": url | None, "provenance": ...}`
    database: dict = field(default_factory=dict)
    # `{"home": home, "describedBy": [...], "repository": url | None, "provenance": ...}`
    infrastructure: dict = field(default_factory=dict)
    # What else the survey saw: `{"ci": [...], "containers": [...], "makefile": bool, "readme": bool}`
    survey: dict = field(default_factory=dict)
    # `{"forge": one of FORGES, "gate": the CI file adopt wrote for it | None, "evidence": ..., "provenance": ...}`
    ci: dict = field(default_factory=dict)
    # `{"path": one of RELEASE_PATHS, "evidence": [...], "provenance": ...}` — how a change reaches production.
    release: dict = field(default_factory=dict)
    # The convergence map: one row per axis — `axis`, `rung`, `target`, `evidence`, `provenance`, `planned` —
    # as `convergence.py` computes and `adopt --refresh` reconciles it.
    convergence: list = field(default_factory=list)
    # `{"recommended": strategy, "trigger", "because": [...], "before": [...], "stop", "decided": strategy | None,
    # "adr": path | None, "finished": bool, "provenance"}` — what `why` and the map recommend, and what an ADR decided.
    strategy: dict = field(default_factory=dict)
    # `{"snapshot": the support table's date, "dated": the day it was read, "products": [{app, product, title, version,
    # cycle, status, eol, evidence}], "provenance"}` — what the applications run on, dated (`platform.py`).
    platform: dict = field(default_factory=dict)
    # `{"with": version, "from": the delivery directory the material moved out of}` once `slipwai converge` has run:
    # every row read *as generated*, the material is at the root, and `origin: adopted` is history from then on.
    converged: dict = field(default_factory=dict)

    def record(self) -> dict:
        """The keys after `layout`, in the order the manifest writes them."""
        return {
            **({"why": self.why} if self.why else {}),
            **({"database": self.database} if self.database else {}),
            **({"infrastructure": self.infrastructure} if self.infrastructure else {}),
            **({"ci": self.ci} if self.ci else {}),
            **({"release": self.release} if self.release else {}),
            **({"platform": self.platform} if self.platform else {}),
            **({"strategy": self.strategy} if self.strategy else {}),
            **({"convergence": self.convergence} if self.convergence else {}),
            **({"survey": self.survey} if self.survey else {}),
            **({"converged": self.converged} if self.converged else {}),
        }


def origin_of(document: dict) -> str | None:
    """`origin` as the manifest records it, or None where it records none — which is a generated project."""
    origin = document.get("origin")
    if origin is not None and origin not in ORIGINS:
        raise GenerationError(f"project.json records origin as {origin!r}; this factory knows {' and '.join(ORIGINS)}")
    return origin


def home_of(record: dict, key: str, what: str) -> None:
    home = record.get(key)
    if home not in HOMES:
        raise GenerationError(f"project.json's {what} records {key} as {home!r}; this factory knows {', '.join(HOMES)}")
    if home == "elsewhere" and not isinstance(record.get("repository"), str):
        raise GenerationError(f"project.json's {what} is {key} elsewhere but names no repository")


def current(name: object) -> str:
    """A strategy as this factory spells it: a name an older factory wrote, mapped forward."""
    return OLD_STRATEGIES.get(str(name), str(name))


def renamed(strategy: dict) -> dict:
    """The strategy record with any name an older factory wrote replaced by the current one, so that what is written
    back is always current. Only the two keys that hold a strategy, and only where one is written: `decided` is
    `None` until an ADR decides. Everything else `strategy.py` derives again."""
    return {
        key: current(value) if key in ("recommended", "decided") and value else value
        for key, value in strategy.items()
    }


def adoption_of(document: dict) -> Adoption | None:
    """The adoption a manifest records, carried as written; None for a generated project."""
    if origin_of(document) != "adopted":
        return None
    why = document.get("why")
    if why is not None and not isinstance(why, str):
        raise GenerationError("project.json's why is not a sentence")
    facts = {key: document.get(key, {}) for key in ("database", "infrastructure", "survey", "ci", "release")}
    for key, value in facts.items():
        if not isinstance(value, dict):
            raise GenerationError(f"project.json's {key} is not an object")
    if facts["database"]:
        home_of(facts["database"], "schema", "database")
    if facts["infrastructure"]:
        home_of(facts["infrastructure"], "home", "infrastructure")
    if facts["ci"] and facts["ci"].get("forge") not in FORGES:
        raise GenerationError(
            f"project.json's ci records forge as {facts['ci'].get('forge')!r}; this factory knows {', '.join(FORGES)}"
        )
    if facts["release"] and facts["release"].get("path") not in RELEASE_PATHS:
        raise GenerationError(
            f"project.json's release records path as {facts['release'].get('path')!r}; this factory knows "
            f"{', '.join(RELEASE_PATHS)}"
        )
    # `strategy` was `modernisation` up to 1.12, and `in-place` was `modernise-in-place`: a repository adopted by an
    # older factory is read as it stands and written back under the current names, so nothing already adopted has to
    # be renamed before its next `/survey` (CHANGELOG, *To catch up*).
    strategy = document.get("strategy", document.get("modernisation", {}))
    if not isinstance(strategy, dict) or (strategy and current(strategy.get("recommended")) not in STRATEGIES):
        raise GenerationError("project.json's strategy does not record a strategy this factory knows")
    strategy = renamed(strategy)
    platform = document.get("platform", {})
    if not isinstance(platform, dict) or not isinstance(platform.get("products", []), list):
        raise GenerationError("project.json's platform is not a record with a list of products")
    convergence = document.get("convergence", [])
    rows_ok = isinstance(convergence, list) and all(
        isinstance(r, dict) and "axis" in r and "rung" in r for r in convergence
    )
    if not rows_ok:
        raise GenerationError("project.json's convergence is not a list of rows with an axis and a rung")
    convergence = [{**r, "axis": OLD_AXES.get(str(r["axis"]), r["axis"])} for r in convergence]
    converged = document.get("converged", {})
    if not isinstance(converged, dict) or (converged and not isinstance(converged.get("with"), str)):
        raise GenerationError("project.json's converged does not say which factory converged it")
    return Adoption(
        why, facts["database"], facts["infrastructure"], facts["survey"], ci=facts["ci"], release=facts["release"],
        convergence=convergence, strategy=strategy, platform=platform, converged=converged,
    )
