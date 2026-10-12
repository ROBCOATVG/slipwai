"""Where one captain works, and the allocation policy that stops two of them colliding on one machine.

A berth is the provisioned place a fairway is worked in: a git worktree, a block of ports, a database, a
scratch directory, and a sandbox. In the experiment and in MANDA this was an operator's job and lived in
their head — five berths on one machine, the port numbers chosen by hand, and a load average of 198 when
nobody was counting. What goes wrong is not dramatic: two berths take one port, one of them fails to start,
and the failure reads as a broken service rather than as a collision.

**So the policy is arithmetic, not a table somebody maintains.** A berth's ports are a block derived from
its index, its database is suffixed with its own name, and both fall out of the berth existing. Nobody
chooses a number, so nobody chooses the same number twice.

**And the arithmetic is per machine, because two of them share a database server and nothing else.** Ports
needed nothing: a port is reachable from one machine, so two machines' blocks are not in the same space at
all and shifting one of them by machine would waste the very arithmetic that makes a block safe. The
database was the whole exposure, and only where people point at a shared instance — every generated default
is local, being in-memory, a SQLite file, or a container from the project's own compose file. So the
machine's identity goes *into the name*, `app_<machine>_<berth>`, which removes the collision instead of
refusing the configuration. It arrives as an argument rather than being looked up here: this module is
carried into a generated project byte for byte and may import nothing beside it, and `logs.machine()` is
where the one identity lives.

**A berth holds no credential.** Not for the forge, not for the cloud, not for the chandlery. Anything
needing one goes through the harbourmaster, which holds them and checks each request against what a run
never does. A berth that held a token would be a sandbox with a way out of it.

The provisioning itself — making a worktree, starting a sandbox — is slice 5.14b, and its macOS question is
still a person's: `sandbox-exec` is deprecated by Apple and undocumented, and the alternative is a container
per berth, which costs a Docker dependency on every laptop. This module is the part that needs no answer to
that: what a berth *is*, and which numbers it gets.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

#: Where a berth's record lives. One file per berth, so two berths never write one file — the same rule the
#: deck logs and the per-fairway decisions follow, for the same reason.
BERTHS = ".slipwai/berths"
#: The first port a berth may use. Above the generator's own defaults (3000 for a service, 5173 for a web
#: app) so that a berth never collides with a project started the ordinary way outside one.
FIRST_PORT = 8100
#: How many ports one berth owns. Wide enough for several services, their databases and a web app, with
#: room left: a block that is exactly big enough today is a block that is too small at the next service.
BLOCK = 20
#: A berth's name, which becomes a database suffix and a directory, so it is held to what all three allow.
NAME = re.compile(r"^[a-z][a-z0-9-]{0,30}$")


@dataclass(frozen=True)
class Berth:
    """One berth's record, as `.slipwai/berths/<name>.json` holds it."""

    name: str
    index: int
    machine: str
    worktree: str
    database: str
    scratch: str
    sandbox: str

    @property
    def ports(self) -> range:
        return port_block(self.index)


def port_block(index: int) -> range:
    """The ports this berth owns. Blocks never overlap, because the arithmetic cannot make them."""
    base = FIRST_PORT + index * BLOCK
    return range(base, base + BLOCK)


def database_of(name: str, machine: str) -> str:
    """One database per berth per machine, named after both.

    Suffixing rather than sharing with a schema per berth: a migration that drops a table drops it for
    everybody in a shared database, and the failure arrives in a fairway that changed nothing. The machine
    is in the name for the same reason one step out — two people pointing two harbours at one instance is
    the same collision with nothing local to make it visible — and `machine` is required rather than
    defaulted, so a caller that has not decided whose berth this is cannot quietly make one that collides.
    """
    return f"app_{machine.replace('-', '_')}_{name.replace('-', '_')}"


def named(name: str) -> str:
    """The name, or a refusal saying what a name may be.

    It becomes a database name, a directory and part of a port allocation, so it is held to the narrowest
    of the three rather than to whichever one happens to complain first.
    """
    if not NAME.match(name):
        raise ValueError(f"a berth is named in lower case, starting with a letter, with digits and hyphens "
                         f"after it, up to 31 characters: {name!r} is not. The name becomes a database name "
                         f"and a directory, so it is held to what both allow")
    return name


def berth(name: str, index: int, machine: str, sandbox: str = "none", root: str = ".") -> Berth:
    """One berth's record from its name, its index and the machine it is on. The rest is derived."""
    checked = named(name)
    return Berth(
        name=checked,
        index=index,
        machine=machine,
        worktree=f"{root}/../{checked}",
        database=database_of(checked, machine),
        scratch=f"{BERTHS}/{checked}/scratch",
        sandbox=sandbox,
    )


def allocate(names: list[str], machine: str, sandbox: str = "none", root: str = ".") -> list[Berth]:
    """Every berth, in the order given, each with a block no other berth on this machine has."""
    return [berth(name, index, machine, sandbox, root) for index, name in enumerate(names)]


def collisions(berths: list[Berth]) -> list[str]:
    """Anything two berths share. Empty by construction, and checked because 'by construction' is a claim.

    Ports are compared within a machine and databases across every machine given, which is the split the
    arithmetic rests on: a port is local and a database server is not. Hand it two machines' berths and it
    is the check that the machine in the name does what it is there for.
    """
    found: list[str] = []
    seen_ports: dict[tuple[str, int], str] = {}
    seen_databases: dict[str, str] = {}
    for one in berths:
        for port in one.ports:
            if (one.machine, port) in seen_ports:
                found.append(f"{one.name} and {seen_ports[(one.machine, port)]} both take port {port} "
                             f"on {one.machine}")
            seen_ports[(one.machine, port)] = one.name
        if one.database in seen_databases:
            found.append(f"{one.name} and {seen_databases[one.database]} both use {one.database}")
        seen_databases[one.database] = one.name
    return found
