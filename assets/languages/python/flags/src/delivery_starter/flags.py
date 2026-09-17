"""Whether a feature flag is on — the service's half of a flag, and the only place it is read.

A flag is what makes merging and releasing two decisions. Every commit that passes `verify` on
`main` reaches production, so work that is not finished has to arrive there dark: the branch is
merged, the flag is off, and nobody outside sees it until somebody flips it.
`.specify/memory/constitution.md` requires exactly that, and this module is where the requirement
stops being prose.

One flag, one name
------------------
A flag is declared once, in `infra/service/flags.auto.tfvars`, under the service that reads it,
with a key in one spelling: `checkout-v2`. Ask by key and the declaration and the code cannot
drift apart — which is the whole reason a slice calls ``flag_enabled("checkout-v2")`` and never
reaches for a variable name of its own. A hand-derived variable is a typo waiting to happen, and a
typo reads as *absent*, which reads as *off*: the feature never turns on and the flip merely looks
broken.

Where a value comes from is one object, and it is not this function
------------------------------------------------------------------
A `FlagSource` answers two questions and no others: what this environment holds for one key, and
what it holds for all of them. Today there is one implementation and `default_source` returns it:
the stack turns each key into an SSM parameter and has ECS resolve it into this container's
environment as `FLAG_CHECKOUT_V2` — upper-cased, dashes to underscores — so `environment_source`
applies that transform and reads `os.environ`. `flag_variable` is the transform and `flag_key` is
its inverse, both written here and nowhere else, and both pinned by a test against the HCL that has
to agree with them.

The point of the seam is that it is keyed by the flag's own key rather than by a variable name. A
transport that is not an environment — an AppConfig agent beside this container, answered over
loopback, which is what a flag that has to move *without* a restart needs — is then a second
`FlagSource` and a one-line change to `default_source`, not a change to any call site, any test, or
the rule in `AGENTS.md` that points at this module. `docs/deployment.md` says which of the two this
project has and what a flip therefore costs.

`snapshot` is the second question because something has to answer it: the flags this service holds
are served to the browser app, which cannot read them itself. It is deliberately a *snapshot* and
not a subscription — the values as of the moment it was asked, which is all a transport polling an
agent can honestly promise.

Off is the answer to every question this cannot answer
------------------------------------------------------
`flag_enabled` is true only for the exact string ``"on"`` — the spelling `make flag` writes and
the only one `flags.auto.tfvars` seeds. ``"off"``, ``"true"``, ``"1"``, a value that never
arrived: all off. That is the safe direction, and it matters most in the window between merging
code that reads a flag and the apply that creates its parameter. A source answers ``None`` there
rather than raising the `KeyError` that ``os.environ[...]`` would, so a task starts with the
feature quietly off rather than dying on import.

The seam exists so both paths can be tested
-------------------------------------------
A test drives either path by passing a source, which is the whole reason the value is not read at
the point of use: ``fixed_source({"checkout-v2": "on"})`` for the on path and ``fixed_source({})``
for the one production is running while the flag is off. It is keyed by key, so a test never has to
know how this environment happens to carry a flag. `make check-flags` holds every declared flag to
having both paths covered, because while a flag is off the branch running in production is the one
the slice's own tests do not reach — and "it worked before the branch was added" is not evidence
about the code after it. `os.environ` is read here and nowhere else.

Locally there is no parameter store and no flip: the flag is whatever this process's environment
says, so ``FLAG_CHECKOUT_V2=on make dev`` is the whole of it.
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

# Only this value is on. A flag set to anything else, or to nothing, gates its feature shut.
ON = "on"

# The prefix the stack gives every flag variable, and the one `flag_key` will answer to.
PREFIX = "FLAG_"


class FlagSource(Protocol):
    """Where this service's flags come from.

    Keyed by the flag's key and not by an environment variable, so that a transport which is not
    an environment is an implementation of this and nothing more.
    """

    def value(self, key: str) -> str | None:
        """This environment's raw value for one flag, or None when it carries none."""

    def snapshot(self) -> dict[str, str]:
        """Every flag this source carries, by key, as of now.

        A snapshot rather than a subscription: a transport that polls an agent can promise the
        values it last saw and nothing stronger. Only flags with a value appear — an absent flag
        is off, and saying so by omission is the same answer `value` gives.
        """


def flag_variable(key: str) -> str:
    """The variable a flag's key is read from: `checkout-v2` -> `FLAG_CHECKOUT_V2`."""
    return PREFIX + key.upper().replace("-", "_")


def flag_key(variable: str) -> str | None:
    """The key a flag variable came from: `FLAG_CHECKOUT_V2` -> `checkout-v2`.

    None for a variable that is not a flag's. The inverse is exact only because a key may not
    contain an underscore — `check-flags.py` holds every declared key to ``[a-z0-9][a-z0-9-]*`` —
    so every underscore in the variable came from a dash. It is deliberately anchored on the
    prefix, which is why ``VITE_FLAG_CHECKOUT_V2``, the browser's spelling of the same flag, is not
    a flag variable here.
    """
    if not variable.startswith(PREFIX):
        return None
    return variable[len(PREFIX) :].lower().replace("_", "-")


@dataclass(frozen=True)
class _EnvironmentSource:
    """Flags carried by an environment, under the variable names `flags.tf` gives them."""

    variables: Mapping[str, str]

    def value(self, key: str) -> str | None:
        return self.variables.get(flag_variable(key))

    def snapshot(self) -> dict[str, str]:
        flags: dict[str, str] = {}
        for variable, value in self.variables.items():
            key = flag_key(variable)
            if key is not None:
                flags[key] = value
        return flags


@dataclass(frozen=True)
class _FixedSource:
    """Flags held by key, which is what a test drives both paths with."""

    values: Mapping[str, str]

    def value(self, key: str) -> str | None:
        return self.values.get(key)

    def snapshot(self) -> dict[str, str]:
        return dict(self.values)


def environment_source(environment: Mapping[str, str] | None = None) -> FlagSource:
    """Flags carried by an environment.

    Args:
        environment: the variables to read. The process's own by default.
    """
    return _EnvironmentSource(os.environ if environment is None else environment)


def fixed_source(values: Mapping[str, str]) -> FlagSource:
    """Flags held by key — the key itself, so a test never spells a variable name.

    A key the mapping does not carry is off, exactly as an unset variable is.
    """
    return _FixedSource(values)


def default_source() -> FlagSource:
    """Where this service's flags come from — the one line a change of transport is.

    Called per read rather than resolved once at import, so that a source with state of its own (a
    poller holding the last configuration it fetched) can memoize behind this and still be swapped
    in here alone.
    """
    return environment_source()


def flag_enabled(key: str, source: FlagSource | None = None) -> bool:
    """Whether `key` is on.

    Args:
        key: the flag's name as `infra/service/flags.auto.tfvars` declares it, in one spelling.
        source: where to read it from. This service's own by default; `fixed_source` in a test.
    """
    read = default_source() if source is None else source
    return read.value(key) == ON
