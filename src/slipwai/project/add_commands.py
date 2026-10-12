"""The commands about the keel that made this project: `add-service`, `add-frontend`, `catch-up`.

Split from `commands.py` because these are a different kind of command. The others drive a slice through the
project's own workflow; these are about the relationship with the keel. An agent asked for "a payments
service" and given no command will copy `apps/service` by hand and edit the nine files that name it, which
is the state `add-service` exists to end; the command is where it learns that the keel does this, what
has to be decided first, and what to check afterwards.

`catch-up` is the third and at the other end. A migration merges the keel's newer output, and the work
left over is code the keel has never seen being held to a rule that did not exist when it was written.
Left uncommanded that becomes "make verify is red, so change whatever makes it green" — which, faced with a
factory-owned gate script, is exactly the wrong repair. Unlike the other two it runs no factory command:
`slipwai migrate` writes what the versions crossed ask for into the project before it returns, and this reads
it there. One command to run, not two — the second is the one that would be forgotten, because a merge is
visible in `git status` and an obligation is not.

The first two name the project's current applications, so they change when one is added — which means
`add-service` regenerates them, and the file an agent reads always lists what is there now.

Both pages are under `assets/toolkit/commands/`, and each says *Find the keel* and *Run it* in full rather
than sharing a Python template with the other. They are not the same words: the verb differs, the
invocation differs, and what to say afterwards differs — and a page a person edits a paragraph at a time
is worth more than the three lines the template saved.
"""
from __future__ import annotations

from ..assets import TOOLKIT_ROOT
from ..catalog import CATALOG, families
from ..loaded_targets import answer
from ..services import App, contexts_phrase, services_of, web_apps
from ..target_protocol import ADD_COMMANDS
from ..targets import managed
from ..toolkit import example_of
from .prose import page

# Where the pages live: beside the three a project has always received verbatim.
COMMANDS = TOOLKIT_ROOT / "commands"


def listed(apps: list[App]) -> str:
    """The project's applications, one line each, so the file says what is there now."""
    lines = [
        f"- `{app.name}` — {app.backend}, port {app.port}; {contexts_phrase(app)}"
        + (f" — {app.purpose}" if app.purpose else " — no purpose recorded")
        for app in services_of(apps)
    ]
    lines += [f"- `{app.name}` — browser app on port {app.port}, `/api` to `{app.api}`" for app in web_apps(apps)]
    return "\n".join(lines)


# What adding a service or a frontend means for a project with a destination: one more image, one more
# deployable, and — on some clouds — a repository the bootstrap stack has to create first. Said in the
# command because the report says it once and the agent reads the command every time, and asked of the
# target because every noun in it is that cloud's.
def afterwards(target: str, what: str) -> str:
    """What `add-service` or `add-frontend` says afterwards about the destination, or nothing where there
    is no destination to say anything about."""
    if not managed(CATALOG, target):
        return ""
    return str(answer(target, ADD_COMMANDS, default={}).get(what, ""))


def values(apps: list[App] | None = None, target: str = "none") -> dict[str, str]:
    """Every value the two pages here may name, and the whole of what one may name.

    All of it is read off the catalogue, the target or the project's own list: which applications are here,
    which language and answers a new one inherits, what the axes and the frameworks are called, and what
    this project's destination says to do afterwards. Nothing on either page is a sentence somebody edits
    through this dictionary — the pages say what they say in their own words.
    """
    apps = [] if apps is None else apps
    services = services_of(apps)
    example_name, example_path = example_of(apps)
    frameworks = sorted(
        {backend["framework"] for backend in CATALOG["backends"].values() if backend.get("framework")}
    )
    return {
        "example-name": example_name,
        "example-path": example_path,
        "applications": listed(apps),
        "axes": ", ".join(f"`--{axis}`" for axis in CATALOG["axes"]),
        "languages": "|".join(families()),
        "frameworks": "|".join(frameworks),
        "default-language": (
            f"without `--language` the new service is `{services[0].backend}`, like `{services[0].name}`."
            if services
            else "this project has no service the factory made to take a language from, so `--language` is required."
        ),
        "inherits": (
            f"inherits `{services[0].name}`'s answer where the new backend offers it, and takes that\n  backend's own "
            "default where it cannot (a transport is per framework)."
            if services
            else "takes the backend's own default."
        ),
        "default-api": (
            f"Without it, `{services[0].name}`."
            if services
            else "This project has no service the factory made, so `--api` has to name one — `/add-service` first."
        ),
        "after-service": afterwards(target, "service"),
        "after-web": afterwards(target, "web"),
    }


def add_service_command(apps: list[App], target: str = "none") -> str:
    return page(COMMANDS, "add-service.md", values(apps, target))


def add_frontend_command(apps: list[App], target: str = "none") -> str:
    """The sentence saying there is no browser app yet is a whole section, and a project that has one has
    nothing to say about not having one."""
    return page(COMMANDS, "add-frontend.md", values(apps, target),
                () if web_apps(apps) else ("no-browser-app",))


def add_command_files(apps: list[App], target: str = "none") -> dict[str, str]:
    """The commands that run the keel from inside the project: two that grow it, one that catches it up."""
    return {
        "commands/add-service.md": add_service_command(apps, target),
        "commands/add-frontend.md": add_frontend_command(apps, target),
    }
