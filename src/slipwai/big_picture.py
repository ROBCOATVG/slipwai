"""The big picture of a repository the keel did not make: who acts, what it talks to, what starts.

Phase 1 of the modelling method maps the territory once for the whole system and then stops — the nine
steps are done per capability, where work lands. For a generated project that first pass is a
conversation. For an adopted one most of it is already written down, in the routes the code serves and the
authorisation it puts in front of them, and asking a person for what a file says is how a question set
becomes a wall to skim.

So this reads it, under the survey's own rule: proposed only from a line that says so, with the file and
the line number it was said on, and nothing at all where nothing says. Three readings and one refusal.

**Actors from the authorisation.** A role named in a guard is somebody the system already distinguishes.
What that actor *does* is the surfaces its own role guards; what it **cannot** do is the surfaces some
other role guards and it is never named on — which is the one row a slice's `actor` field has nowhere to
carry, and the first thing a security pass and an access classification both ask for. A guard and the route
it guards are written next to each other in every framework this reads — a decorator above a handler, a
middleware argument on the route line — so nearness in the same file is the join, and it is deliberately
narrow: a role whose guard is nowhere near a route contributes an actor and no surfaces.

**External systems from the calls out and the hooks in.** A host in a URL literal is somewhere this code
reaches; a route whose path says hook, webhook or callback is somewhere that reaches it. Hosts every
repository carries — a schema namespace, a documentation link, a loopback address — are not systems and
are named here as not being them.

**Major processes from the entry points.** `structure.py` already finds where anything starts, per
ecosystem; this is that list read as *what this system does*, one proposed slice each.

**And no event.** A name for something that happened is a reading of *behaviour*, which costs the nine
steps against one capability and is `/observe`'s work. The big picture that invents `OrderUpdated` from a
route called `PUT /orders/:id` is the failure the whole of phase 15's adoption half exists to avoid.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .services import App, wrapped_of
from .structure import LANGUAGES, Structure, code_files, prefixed

#: How far below an application's directory the big picture reads. The structure reader's own depth: a
#: route declared six directories down is in a tree this keel has nothing useful to say about anyway.
DEPTH = 4
#: How many lines apart a guard and the route it guards may be. Three, because that is a decorator, an
#: annotation and a blank line between them; a larger window joins a role to a route it never guarded, and
#: a wrong `cannot` is worse than a missing one — it is a permission somebody will design against.
NEAR = 3
#: How much of one file is read. A minified bundle or a generated client is megabytes of one line, and
#: nothing in either is a fact about the business.
MOST = 4000

#: A role named in an authorisation rule, by the convention that names it. One capture group: the role.
#: Narrow on purpose — each of these is a framework saying *this surface is for that role* and nothing
#: else says it, so a match is evidence and a miss is silence rather than a guess.
ROLE_RULES: tuple[re.Pattern[str], ...] = (
    # Spring Security, and the same expressions in Kotlin.
    re.compile(r"""has(?:Any)?(?:Role|Authority)\(\s*['"]([A-Za-z][\w-]*)['"]"""),
    # ASP.NET Core.
    re.compile(r"""\[Authorize\s*\(\s*Roles\s*=\s*"([A-Za-z][\w-]*)"""),
    # Express, Nest, Fastify and the hand-rolled middleware every Node codebase grows.
    re.compile(r"""(?:require|has|check|assert|ensure)(?:Any)?Roles?\(\s*\[?\s*['"]([A-Za-z][\w-]*)['"]"""),
    re.compile(r"""@Roles\(\s*['"]?([A-Za-z][\w-]*)['"]?"""),
    # Flask-Security, Django, FastAPI dependencies, and Rails before_action.
    re.compile(r"""roles?_(?:required|accepted)\(\s*['"]([A-Za-z][\w-]*)['"]"""),
    re.compile(r"""(?:require|authorize)_(?:role|as)[\s(:]+['"]?:?([A-Za-z][\w-]*)['"]?"""),
    # The constant every codebase eventually writes: ROLE_ADMIN, Role.MANAGER.
    re.compile(r"""\bROLE_([A-Z][A-Z0-9_]*)\b"""),
    re.compile(r"""\bRoles?\.([A-Z][A-Za-z0-9]*)\b"""),
)
#: A route declared, by the convention that declares it. One capture group: the path, which is what an
#: actor reaches and what a hook arrives on.
ROUTE_RULES: tuple[re.Pattern[str], ...] = (
    # Express, Fastify, Koa, Hono, Go's chi and gorilla, Laravel, Sinatra and Rails' routes file.
    re.compile(r"""\.(?:get|post|put|patch|delete|all)\(\s*['"`]([/:][^'"`]*)['"`]"""),
    re.compile(r"""(?:HandleFunc|Handle)\(\s*['"`]([/][^'"`]*)['"`]"""),
    re.compile(r"""Route::(?:get|post|put|patch|delete|any)\(\s*['"]([/][^'"]*)['"]"""),
    # FastAPI, Flask, Django and Starlette.
    re.compile(r"""@\w+\.(?:get|post|put|patch|delete|route)\(\s*['"]([/][^'"]*)['"]"""),
    re.compile(r"""\b(?:path|re_path|url)\(\s*r?['"]([^'"]*)['"]"""),
    # Spring, JAX-RS and ASP.NET Core.
    re.compile(r"""@(?:Get|Post|Put|Patch|Delete|Request)Mapping\(\s*(?:value\s*=\s*)?['"]([^'"]*)['"]"""),
    re.compile(r"""@Path\(\s*['"]([^'"]*)['"]"""),
    re.compile(r"""\[Http(?:Get|Post|Put|Patch|Delete)\(\s*"([^"]*)"""),
    re.compile(r"""\.Map(?:Get|Post|Put|Patch|Delete)\(\s*"([/][^"]*)"""),
)
#: A job that runs on a clock, which is a system actor and never a person.
SCHEDULE_RULES: tuple[re.Pattern[str], ...] = (
    re.compile(r"""cron\.schedule\(|@Scheduled\(|@shared_task|celery\.task|schedule\.every\(|setInterval\("""),
    re.compile(r"""\bCronTrigger\b|\bAddCronJob\b|\bwhenever\b"""),
)
#: Somewhere this code reaches out to. The host is the system; the scheme and the path are not.
OUTBOUND = re.compile(r"""https?://([a-z0-9][a-z0-9.-]*\.[a-z]{2,})""", re.IGNORECASE)
#: A route that receives a call from somewhere else, named as such by whoever wrote it.
INBOUND = re.compile(r"hook|callback", re.IGNORECASE)
#: Hosts that are in every repository and are nobody's system: a namespace, a licence, a specification, a
#: documentation site, a package registry, a placeholder. Matched on the whole host or its registrable end.
NOT_A_SYSTEM = (
    "w3.org", "example.com", "example.org", "localhost", "127.0.0.1", "schema.org", "json-schema.org",
    "opensource.org", "apache.org", "gnu.org", "mozilla.org", "python.org", "nodejs.org", "golang.org",
    "oracle.com", "microsoft.com", "developer.mozilla.org", "npmjs.com", "npmjs.org", "pypi.org",
    "maven.apache.org", "nuget.org", "rubygems.org", "github.com", "gitlab.com", "readthedocs.io",
    "stackoverflow.com", "spring.io", "fastapi.tiangolo.com", "expressjs.com", "creativecommons.org",
)


@dataclass(frozen=True)
class Read:
    """One thing the big picture names, and the line of code it was read off."""

    what: str
    where: str  # `apps/api/routes.ts:42`
    how: str  # what the line was taken to say, in a few words


@dataclass(frozen=True)
class Actor:
    """One role the code already distinguishes, with what it reaches and what it does not.

    `cannot` is the whole reason this is a file of its own. It is written from the surfaces another role
    guards, which is what the code says rather than what the business means — the catalogue says so, and
    the question of what the business means is one of the `/gaps` lines.
    """

    name: str
    kind: str  # `human` for a role, `system` for a job or a consumer
    does: tuple[str, ...]
    cannot: tuple[str, ...]
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class Gap:
    """One Phase 1 question the code cannot answer, as the agent that leaves it has to leave it.

    `intention` and `assumption` are not decoration. The agent posting this is working where nobody is
    watching, and a question arriving on its own weeks later tells a person what was unknown and not what
    was done about it — which is the only part they can now disagree with.
    """

    question: str
    intention: str
    assumption: str


@dataclass(frozen=True)
class BigPicture:
    """Phase 1, read off the tree: the actors, the systems either side, the processes, and the questions."""

    actors: tuple[Actor, ...] = ()
    externals: tuple[Read, ...] = ()
    processes: tuple[Read, ...] = ()
    gaps: tuple[Gap, ...] = ()

    @property
    def empty(self) -> bool:
        return not (self.actors or self.externals or self.processes)


def lines_of(path: Path) -> list[str]:
    """The file as lines, or nothing where it cannot be read as text or is too big to be hand-written."""
    try:
        if path.stat().st_size > MOST * 200:
            return []
        return path.read_text(errors="replace", encoding="utf-8").splitlines()[:MOST]
    except OSError:
        return []


def source_files(root: Path, apps: list[App], delivery: str = ".") -> list[tuple[str, list[str]]]:
    """Every code file of every wrapped application, as `(path, lines)`, the keel's own left out."""
    found: list[tuple[str, list[str]]] = []
    seen: set[str] = set()
    for app in wrapped_of(apps):
        here = root if app.path == "." else root / app.path
        for path in code_files(here, DEPTH):
            if path.suffix not in LANGUAGES:
                continue
            relative = prefixed(app.path, path.relative_to(here).as_posix())
            if relative in seen or (delivery != "." and relative.startswith(f"{delivery}/")):
                continue
            seen.add(relative)
            found.append((relative, lines_of(path)))
    return sorted(found)


def matched(rules: tuple[re.Pattern[str], ...], lines: list[str]) -> list[tuple[int, str]]:
    """Every capture one of `rules` makes, with the 1-based line it was made on, in file order."""
    return [
        (number, match.group(1))
        for number, line in enumerate(lines, start=1)
        for rule in rules
        for match in rule.finditer(line)
    ]


def roles_and_routes(files: list[tuple[str, list[str]]]) -> tuple[dict[str, dict], list[str]]:
    """Each role the code names — where it was read, and the routes written next to it — and every route.

    Nearness in one file is the join and is the whole of it: a guard and the route it guards are adjacent
    in every framework here, and anything looser attributes a surface to a role that never guarded it.
    """
    roles: dict[str, dict] = {}
    routes: list[str] = []
    for path, lines in files:
        found_routes = matched(ROUTE_RULES, lines)
        routes += [route for _, route in found_routes]
        for number, role in matched(ROLE_RULES, lines):
            name = role.lower()
            record = roles.setdefault(name, {"evidence": [], "does": []})
            where = f"{path}:{number}"
            if where not in record["evidence"]:
                record["evidence"].append(where)
            # The *nearest* route and not every route within the window: two routes declared on consecutive
            # lines are the commonest shape there is, and a window that takes both gives each role the
            # other's surface — which is a `cannot` that is wrong, and a wrong `cannot` is worse than a
            # missing one, because somebody designs against it.
            near = [(abs(at - number), at, route) for at, route in found_routes if abs(at - number) <= NEAR]
            if near:
                route = min(near)[2]
                if route not in record["does"]:
                    record["does"].append(route)
    return roles, list(dict.fromkeys(routes))


def human_actors(roles: dict[str, dict]) -> tuple[Actor, ...]:
    """One actor per role, each with the surfaces another role guards and it is never named on."""
    guarded = {route: {name for name, record in roles.items() if route in record["does"]} for route in
               {route for record in roles.values() for route in record["does"]}}
    return tuple(
        Actor(
            name=name,
            kind="human",
            does=tuple(sorted(record["does"])),
            cannot=tuple(sorted(route for route, holders in guarded.items() if name not in holders)),
            evidence=tuple(record["evidence"]),
        )
        for name, record in sorted(roles.items())
    )


def system_actors(files: list[tuple[str, list[str]]]) -> tuple[Actor, ...]:
    """The actors that are not people: today, the clock.

    `cannot` is empty and stays empty. A job's limits are a business statement — *it may expire a hold and
    may not issue a refund, because money leaving needs a person* — and nothing in a scheduler says it. The
    blank is a question (`gaps_of`), which is what the modelling skill asks for in place of a guess.
    """
    where = [
        f"{path}:{number}"
        for path, lines in files
        for number, line in enumerate(lines, start=1)
        if any(rule.search(line) for rule in SCHEDULE_RULES)
    ]
    if not where:
        return ()
    return (Actor("systems/cron", "system", ("runs work on a clock",), (), tuple(where[:4])),)


def a_system(host: str) -> bool:
    host = host.lower().rstrip(".")
    return not any(host == known or host.endswith(f".{known}") for known in NOT_A_SYSTEM)


def externals_of(files: list[tuple[str, list[str]]]) -> tuple[Read, ...]:
    """What this code calls out to, and what calls in: by host, and by the route named for the caller."""
    found: dict[str, Read] = {}
    for path, lines in files:
        for number, line in enumerate(lines, start=1):
            for match in OUTBOUND.finditer(line):
                host = match.group(1).lower()
                if a_system(host):
                    found.setdefault(host, Read(host, f"{path}:{number}", "an outbound call to this host"))
        for number, route in matched(ROUTE_RULES, lines):
            if INBOUND.search(route):
                found.setdefault(route, Read(route, f"{path}:{number}", "an inbound hook arrives here"))
    return tuple(found.values())


def processes_of(shape: Structure) -> tuple[Read, ...]:
    """The major processes, which are the entry points the structure reader already lists.

    Read as *what this system does*, one proposed slice each, and no further: what the process is called in
    the business is a question, and the nine steps against it are a capability's work rather than Phase 1's.
    """
    return tuple(
        Read(entry.what, entry.path, f"runs `{entry.runs}`" if entry.runs else "an entry point of this system")
        for app in shape.apps
        for entry in app.entry_points
    )


def gaps_of(found: BigPicture) -> tuple[Gap, ...]:
    """Phase 1's questions the code cannot answer, each with what it was for and what was assumed meanwhile."""
    gaps = [Gap(
        question="Does this list of actors match the roles the business actually has — and is any one of "
                 "them two different people, or two of them one?",
        intention="Phase 1 names who acts, so that every later slice has an `actor` field somebody can "
                  "check. A role in code is a permission, and a role in the business is a person's job.",
        assumption="That each role the authorisation names is one actor, under the name the code gives it.",
    )]
    if any(actor.cannot for actor in found.actors):
        gaps.append(Gap(
            question="Each `cannot` below is what the code enforces. Is it what the business means — and "
                     "is there anything an actor may not do that no route stops them doing?",
            intention="The role catalogue is the statement an implementation is later checked against, so "
                      "it has to say what is intended rather than what is currently true.",
            assumption="That a surface another role guards and this one is never named on is a surface "
                       "this one may not reach.",
        ))
    for actor in found.actors:
        if actor.kind == "system" and not actor.cannot:
            gaps.append(Gap(
                question=f"What may `{actor.name}` **not** do? Nothing in a scheduler says it.",
                intention="A system actor without a `cannot` is the one the next incident is about: work "
                          "that runs with nobody watching and no stated limit.",
                assumption="That it does what its jobs do today and that nothing else was intended.",
            ))
    if found.externals:
        gaps.append(Gap(
            question="Which of these systems does this one depend on to serve an actor, and which could be "
                     "switched off this afternoon without anybody noticing?",
            intention="An external system on the timeline is a swimlane and a translation slice; one that "
                      "is only a library call is neither.",
            assumption="That every host called out to and every hook received is a system worth naming, "
                       "which over-names rather than under-names on purpose.",
        ))
    gaps.append(Gap(
        question="What does this system do that none of these entry points reaches — work done by hand, in "
                 "a console, in a spreadsheet, or by somebody telephoning somebody?",
        intention="The processes below are what the code starts. A business process the code does not "
                  "start is invisible to every reading of this repository and is usually the expensive one.",
        assumption="That the entry points are the whole of what this system does, which they are not.",
    ))
    return tuple(gaps)


def big_picture(root: Path, apps: list[App], shape: Structure, delivery: str = ".") -> BigPicture:
    """Phase 1 for a repository the keel did not make, read off its own code."""
    files = source_files(root, apps, delivery)
    roles, _ = roles_and_routes(files)
    found = BigPicture(
        actors=(*human_actors(roles), *system_actors(files)),
        externals=externals_of(files),
        processes=processes_of(shape),
    )
    return BigPicture(found.actors, found.externals, found.processes, gaps_of(found))
