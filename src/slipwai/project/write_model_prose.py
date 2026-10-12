"""The paragraphs of the generated pages that change with the rung a service is on.

A service's write model is how it decides and records a write: `events`, where the log is the truth and
state is a fold of it, or `state`, where the service keeps current state and the events the model names are
contracts raised after the write and never replayed. Phase 15 made that an axis answered per service, and
`metadata.sourced` is the one place that reads it. This module is the other half of the same claim — what
the pages then say — because until now they said it off the profile, which answers *is there a model?* and
was being read as *is there a log?*. A product with one context that earned the log beside three that did
not could not be generated, so no page ever had to describe one.

Here rather than inline in each page for two reasons. The first is that the rung is a single claim — what a
write locks, what it leaves behind, and whether any of it may be folded back — and every page that carries
its own copy is a copy that can drift: the README would go on promising a replay long after `AGENTS.md` had
stopped. The second is budget, which is the shape of the first: `guidance.py` sat three lines under
check-structure's module budget and `readme.py` sat exactly on it, so a sentence that now has two endings
had nowhere to grow in either of them.

The section it writes into `docs/architecture.md` is called *The write model* and was called *Backend event
bundle*, because the bundle is the thing phase 15 took apart: Event Modeling and event sourcing were
selected together and the heading said so.

Nothing here decides a rung. `sourced` does, and these functions ask it, so a service the keel did not make
and a browser app are on the one side of every sentence below without this module knowing why.
"""
from __future__ import annotations

from ..registry import PERSISTENCE_DIRECTORY, registry
from ..services import App, services_of, web_apps
from .metadata import sourced


def sourced_services(apps: list[App]) -> list[App]:
    """The generated services whose truth is their log."""
    return [service for service in services_of(apps) if sourced(service)]


def state_services(apps: list[App]) -> list[App]:
    """The generated services that keep current state, which is every other one.

    Not the complement of a feature test: a service that was never asked the axis reads `state` from the
    axis's `absent`, so a standard-profile project's services land here without having answered anything.
    """
    return [service for service in services_of(apps) if not sourced(service)]


def paths_of(services: list[App]) -> str:
    """The services named as a reader would say them: `apps/orders` and `apps/billing`."""
    quoted = [f"`{service.path}`" for service in services]
    return quoted[0] if len(quoted) == 1 else ", ".join(quoted[:-1]) + f" and {quoted[-1]}"


def architecture_write_model(apps: list[App]) -> str:
    """`docs/architecture.md`'s section on what each service's write side is, by rung.

    One bullet per rung rather than one per service: what is true of a state-stored service is true of every
    state-stored service, and a reader with six services does not want the same paragraph six times. The
    services are named in the bullet so that the page stays checkable against `project.json` — a reader who
    cannot tell which half a service is in has been told nothing.
    """
    logged, stored = sourced_services(apps), state_services(apps)
    if not logged and not stored:
        return ""
    bullets = ""
    if logged:
        bullets += f"""- {paths_of(logged)} keep{"s" if len(logged) == 1 else ""} the events: the log is the truth, current state is a
  fold of it, and a slice's `stream` is the identity an append is made at an expected version of. Event
  names, schemas, stream identity, optimistic concurrency and the global model change together.
"""
    if stored:
        bullets += f"""- {paths_of(stored)} keep{"s" if len(stored) == 1 else ""} current state: a write loads the row it owns, decides, and saves at
  the version it read, and the events the model names are raised by the use case once that write has
  committed. They are contracts the rest of the product reads, not a history to replay — nothing folds them
  back, and a slice this service owns may name no `guard` and no `folds`, there being no log to query or to
  fold.
"""
    web = web_apps(apps)
    boundary = (
        f" {paths_of(web)} may render commands and read models, but {'they are' if len(web) > 1 else 'it is'} "
        f"not event-sourced and never read{'' if len(web) > 1 else 's'} the event store."
        if web and logged
        else ""
    )
    return f"""
## The write model

Event Modeling covers the end-to-end product journey, and it covers it the same way whichever service a
slice lands in. What differs per service is the write model — how a write is decided and what it leaves
behind — which `project.json` records as `eventSourced` on each deployable:

{bullets}
Events are immutable facts on either rung; never invent or rename one merely to unblock implementation, and
never raise one claiming something the service did not record at the time. The rung itself is the one answer
about a service that cannot be walked back once it holds data: state can be turned into a log from the day
somebody decides, but not backwards into history it never kept.{boundary}
"""


def agents_write_model(apps: list[App]) -> str:
    """`AGENTS.md`'s ownership bullets for the rung, which say what may not be written where.

    Phrased as what the code may not claim rather than as what the rung is, because this file is read by
    whoever is about to write a file: *this service keeps current state* is a fact, and *a fold written here
    is a claim about a log this service does not have* is the same fact at the moment it would be useful.
    """
    logged, stored = sourced_services(apps), state_services(apps)
    bullets = ""
    if logged:
        bullets += f"""- Event sourcing applies to {paths_of(logged)} and to nothing else here. Event Modeling may describe the full
  user journey, including UI frames, but the browser never owns streams, Deciders, replay, or event-store
  access.
"""
    if stored:
        bullets += f"""- {paths_of(stored)} keep{"s" if len(stored) == 1 else ""} current state, and the events of a slice it owns are files its use case raises
  once the write has committed. Nothing reads them back: a fold, a replay or a tag query written there is a
  claim about a log this service does not keep, and `make check-model` refuses the fields that would say so.
"""
    return bullets


def store_port_rule(apps: list[App]) -> str:
    """The driven-port bullet, named for what each rung's store is actually asked to hold.

    Both rungs ship an in-memory adapter beside whichever store was chosen, and both hold every adapter to
    one contract suite; what differs is which port it is a contract for. Saying *the event store is a driven
    port* in a project that has no event store sends the reader looking for a directory nobody generated.
    """
    rules = ""
    for name, services, port in (
        ("event store", sourced_services(apps), "event-store"),
        ("repository", state_services(apps), "repository"),
    ):
        holding = [service for service in services if service.selection.has("memory")]
        if not holding:
            continue
        adapters = ", ".join(
            f"`{registry().answer(service.backend, PERSISTENCE_DIRECTORY)(service.path)}`"
            for service in holding
        )
        rules += f"""- The {name} is a driven port on {paths_of(holding)}. Domain and application code name the {port} port,
  never a database type, and every adapter under {adapters} passes the same contract suite. Add a
  capability to it by extending that contract first, so the adapters cannot drift apart.
"""
    return rules


def readme_write_model(apps: list[App]) -> str:
    """The README's opening paragraph of its event-workflow section.

    The sentence this replaces — *this profile deliberately cannot be generated with Event Modeling or event
    sourcing alone* — stopped being true the day `write-model` became an axis, and it was the sentence that
    told a reader the two were one decision. What goes in its place has to leave them two.
    """
    logged, stored = sourced_services(apps), state_services(apps)
    where = ""
    if logged:
        where += (
            f"\n{paths_of(logged)} keep{'s' if len(logged) == 1 else ''} the events, so a slice's event contract and its"
            "\nstream identity are written together."
        )
    if stored:
        where += (
            f"\n{paths_of(stored)} keep{'s' if len(stored) == 1 else ''} current state, and raise{'s' if len(stored) == 1 else ''}"
            " a slice's events once its write has\ncommitted."
        )
    return f"""Start with `docs/event-model/model.yaml`, name commands and events with domain experts, then implement the
slice in the service that owns it. Event Modeling is the same on every service here; the write model is not,
and `project.json` records which rung each service is on.{where}
`docs/event-modeling-to-code.md` carries the table for each, and that is the page to read before writing a
slice in a service for the first time."""


#: What `/run`'s *Seed it* section says about each store, by the rung the service keeping it is on. Keyed
#: `(store, sourced)` because both halves change the paragraph: the store decides whether anything has to be
#: started or migrated, and the rung decides what the thing being started actually holds. The pair is the
#: key rather than two nested tables because there is no sentence here that is true of a store on both rungs
#: — "deleting it deletes the entire truth of the system" is the log's claim, and on a state-stored service
#: it would be describing a row nobody promised was the truth of anything.
RUN_SEEDS = {
    ("postgres", True): """This project's event store is Postgres, which needs its container running and its migrations
applied before it can hold anything:""",
    ("postgres", False): """This project keeps its state in Postgres, which needs its container running and its
migrations applied before it can hold anything:""",
    ("sqlite", True): """This project's event store is a SQLite file, created by the process that opens it, so
there is nothing to start and nothing to migrate. The log is at `EVENT_STORE_PATH` (see `.env.example`) and
is git-ignored: deleting it deletes the entire truth of the system, which on a demo is usually what you
want between runs.""",
    ("sqlite", False): """This project keeps its state in a SQLite file, created by the process that opens it, so
there is nothing to start and nothing to migrate. The file is at `EVENT_STORE_PATH` (see `.env.example`) and
is git-ignored: deleting it puts the service back to an empty world, which on a demo is usually what you
want between runs.""",
    ("memory", True): """This project's event store is in memory, so every restart is a fresh world. Nothing to
start, nothing to migrate, and nothing to clean up — but also nothing to come back to: seed whatever the
demo needs through the app itself, in front of whoever is watching if the seeding is part of the story.""",
    ("memory", False): """This project keeps its state in memory, so every restart is a fresh world. Nothing to
start, nothing to migrate, and nothing to clean up — but also nothing to come back to: seed whatever the
demo needs through the app itself, in front of whoever is watching if the seeding is part of the story.""",
}

#: The shell block the two Postgres paragraphs share, and the sentence after it. `make migrate` applies
#: whichever migrations the rung put there — the log's table on `events`, the versioned state table on
#: `state` — so the commands are the same and only the word for what they fill changes.
POSTGRES_STEPS = """
```sh
make services-up   # starts Postgres, waits for it to accept connections
make migrate       # applies the migrations
```

`make demo` starts Postgres too, but it does **not** migrate — that is a write to a database and stays an
explicit act. Run `make migrate` once after the first `make demo`, and again whenever a migration is added."""


def run_seed(apps: list[App]) -> str:
    """`/run`'s *Seed it* paragraphs: one per distinct store-and-rung the generated services use.

    Two services on one store and one rung say it once, which is the rule this had before the rung existed.
    Two services on one store and *different* rungs say it twice, because they are two different things to
    start: one of them is a log whose deletion loses the truth, and the other is a table whose deletion
    loses this week.
    """
    seen = [
        (service.selection.option("persistence"), sourced(service))
        for service in services_of(apps)
        if "persistence" in service.selection.axes
    ]
    return "\n\n".join(
        RUN_SEEDS[key] + (POSTGRES_STEPS if key[0] == "postgres" else "")
        for key in dict.fromkeys(seen)
        if key in RUN_SEEDS
    )


def rung_question(proposed: list[dict]) -> str:
    """The rung, asked of the candidates whose own dependencies name an event store — and of no others.

    A question nobody has evidence for is a question that manufactures an answer, so this is not asked of a
    repository where the survey found nothing: a wrapped application with no answer here is `state`, which is
    the honest reading of *nobody has claimed this application's past*, and the rung is recorded only when
    somebody vouches for it (15.9).
    """
    if not proposed:
        return ""
    rows = "\n".join(
        f"   - `{row.get('name')}` — {row.get('writeModelEvidence')}" for row in proposed
    )
    return (
        "**Ask, of these and only these — the rung.** The survey found an event-store library in their own\n"
        "dependencies, which is the one thing a tree can say about whether an application's log is its truth:\n\n"
        f"{rows}\n\n"
        "   Ask whether that library is what this application's writes actually go through, or something a\n"
        "   corner of it uses. The answer matters because the model is read against it: a service on the\n"
        "   `events` rung is modelled against its own events module, and one on `state` against its tables and\n"
        "   the transitions in them. Say what you read in the code and why you think it is one or the other.\n\n"
        "   **Write:** `--write-model events` on that application's `--confirm`, and nothing at all where the\n"
        "   answer is no or the person does not know. Silence records `state`, which is what the record should\n"
        "   say while nobody has claimed this application's past — the detection alone never records a log.\n\n"
    )
