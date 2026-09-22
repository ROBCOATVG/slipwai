"""The switch that turns on the reshaped adoption intro before it is the only one.

Brownfield adoption is experimental as a whole (#74; `AGENTS.md` says what the word means here), and the
exemption it carries is permission for its *shape* to change in a MINOR. That is not permission to change
the shape under somebody mid-adoption without warning, so the reshaping of the intro — the terminal reduced
to what a terminal can answer, the applications left as candidates for the agent to confirm, `./init` run as
part of the adoption rather than after it — arrives behind this switch first. Default off: `slipwai adopt`
asks exactly what it asked before. On, by `--experimental-intro` or `SLIPWAI_EXPERIMENTAL_INTRO=1` in the
environment, it is the new intro, and the report says so.

One predicate, read in one place, so that turning the new intro on by default is deleting this module and
its callers rather than hunting for the conditions it grew.
"""
from __future__ import annotations

import os

VARIABLE = "SLIPWAI_EXPERIMENTAL_INTRO"
FLAG = "--experimental-intro"
# What the report and `--help` call it, so the same words appear wherever a person meets the switch.
BANNER = (
    "the reshaped intro (experimental, and experimental within an experiment): the terminal asks only what it "
    "can answer, and the agent confirms the rest"
)
HELP = (
    f"use the reshaped adoption intro rather than the interview this version asks by default "
    f"(or set {VARIABLE}=1); its shape is still moving, and what it gets wrong belongs on issue #74"
)
# Anything but an empty string or a written-out no: the variable is a switch, and a person who sets it to
# `false` means off, not "a non-empty string, therefore on".
OFF = frozenset(("", "0", "no", "off", "false"))


def from_environment() -> bool:
    return os.environ.get(VARIABLE, "").strip().lower() not in OFF


def reshaped_intro(flag: bool = False) -> bool:
    """Whether this run uses the reshaped intro: the flag, or the environment variable."""
    return bool(flag) or from_environment()
