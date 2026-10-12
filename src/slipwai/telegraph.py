"""The telegraph: one lever a person rings, and the nine numbers it sets.

A run has a dozen numbers that all mean the same thing in different units — how many berths are lit, how many
delegates each captain may have, what a slice may spend, what a day may spend, how long a stage may take.
Changing "go slower" from one to another is eight edits, and anybody doing it in a hurry gets some of them.

**So there are five positions, and each is a whole set of numbers.** `full-ahead`, `half-ahead`,
`slow-ahead`, `dead-slow`, `stop`, in that order, which is also the order they are stepped down in. A person
rings a position; every number moves together.

**The numbers stay individually settable, because the positions will be wrong.** `--set boilers=2` changes
one and the fleet board then says `half-ahead, adjusted` — adjusted, not a new position, because a board that
reported a position the numbers do not match is a board that is lying. Ringing a position again resets
everything, which is what makes a hurried adjustment safe to make.

**Banking the fires is the same lever, pulled by the clock instead of a person.** When the day's bunker is
spent the harbourmaster steps the position down one notch at a time, writing `fires-banked` with what it
stepped to and why. One notch at a time, and not straight to `stop`: a run that stops dead at the end of the
day loses whatever was in flight, and a run that slows keeps finishing what it started.

`stop` is not a crash. Every captain parks at its *next boundary*, which is the thing a captain was built to
have: a place where ending costs nothing and the log says exactly where it got to.

In the experiment none of these numbers existed. 104 hours and hundreds of millions of input tokens on one
slice, and the only signals were a person noticing and the bill arriving. Both are late.
"""
from __future__ import annotations


class Refused(ValueError):
    """A position or a number that is not one, said as the one line a person reads.

    A `ValueError` and not the keel's own refusal: this module is carried into a generated project by
    `make shared`, and a project has no slipwai to import `GenerationError` from. The command line wraps it.
    """


#: Every position, in the order the fires are banked. Slower to the right; `stop` is the last notch.
POSITIONS = ("full-ahead", "half-ahead", "slow-ahead", "dead-slow", "stop")
#: What each number is, in a phrase, so one table says it for `--help`, the file's comment and the board.
MEANS = {
    "boilers": "berths lit at once",
    "fanout": "delegates one captain may have running",
    "bunker_per_slice": "thousands of input tokens one slice may spend",
    "bunker_per_day": "thousands of input tokens the harbour may spend in a day",
    "stage_scale": "what every stage budget in `stages` is multiplied by",
    "bar": "the severity at or above which an adversary finding must close before a merge",
    "decision_ceiling": "decisions that may stand unread before a fairway parks",
    "wait_bound": "minutes a wait may go with the harbour log silent before it is a parked line",
    # Added with slice 7.8, which needed a retry bound and found that `cycle` is not one — `cycle` is the
    # TDD unit (`rule` or `example`), not a count, and the captain needs to know how many times it may
    # re-dispatch `/sail` for one slice before parking. A send-back at the demo is the case that matters:
    # the person who sent it back is present and has just given notes, so trying again beats parking, and
    # a bound stops "trying again" from being the whole afternoon.
    "attempts": "times one slice may be re-dispatched before the fairway parks",
}
#: Each position's numbers. Not a formula: `bar` and `decision_ceiling` tighten as the run slows because a
#: slower run is one somebody is already unhappy about, and that is a judgement rather than an arithmetic.
#: `half-ahead` is a fresh harbour's, and its row is exactly `project/harbour.py`'s documented defaults —
#: so a generated project reads `half-ahead` and not `half-ahead, adjusted` on the day it is made.
#: A *lower* bar is stricter, so slowing lowers it: a run somebody has slowed down is one where less gets
#: deferred, not more.
SETTINGS: dict[str, dict[str, object]] = {
    "full-ahead": {"boilers": 5, "fanout": 3, "bunker_per_slice": 1500, "bunker_per_day": 20000,
                   "stage_scale": 1.0, "bar": "HIGH", "decision_ceiling": 12, "wait_bound": 90,
                   "attempts": 3},
    "half-ahead": {"boilers": 3, "fanout": 2, "bunker_per_slice": 1000, "bunker_per_day": 10000,
                   "stage_scale": 1.0, "bar": "MEDIUM", "decision_ceiling": 10, "wait_bound": 60,
                   "attempts": 2},
    "slow-ahead": {"boilers": 2, "fanout": 1, "bunker_per_slice": 700, "bunker_per_day": 5000,
                   "stage_scale": 0.75, "bar": "MEDIUM", "decision_ceiling": 5, "wait_bound": 30,
                   "attempts": 2},
    "dead-slow": {"boilers": 1, "fanout": 1, "bunker_per_slice": 400, "bunker_per_day": 2000,
                  "stage_scale": 0.5, "bar": "LOW", "decision_ceiling": 3, "wait_bound": 20,
                  "attempts": 1},
    "stop": {"boilers": 0, "fanout": 0, "bunker_per_slice": 0, "bunker_per_day": 0,
             "stage_scale": 0.0, "bar": "LOW", "decision_ceiling": 0, "wait_bound": 0,
             "attempts": 0},
}
#: Mirrored from `.specify/sail.json` so a person sets every width in one place. The telegraph does not own
#: them — `/sail` does — so a position never sets them and `--set` writes them back where they came from.
#: **Both are words, not numbers**, which is what their values are: `delegate` is how much of a slice one
#: delegate is handed, `cycle` is how many failing tests a RED-GREEN-REFACTOR cycle opens with. They were
#: described here as numbers and parsed as numbers, so `--set delegate=story` and `--set cycle=rule` — the
#: only values either takes — were both refused, and `--set cycle=3` was accepted. `scripts/agents/sail.py`
#: owns these sets; `tests/test_telegraph.py` holds the two in step, because a project has no slipwai to
#: import and this is the second copy either way.
MIRRORED = {
    "delegate": ("how much of a slice one delegate is handed", ("story", "rule", "task")),
    "cycle": ("how many failing tests one RED-GREEN-REFACTOR cycle opens with", ("rule", "example")),
}
NUMBERS = tuple(MEANS)


def position(name: str) -> str:
    """One position by name, or a refusal listing them in order. A near miss is still a refusal: ringing the
    wrong lever because a name was guessed at is the thing a closed set exists to stop."""
    if name not in SETTINGS:
        raise Refused(f"`{name}` is not a telegraph position. There are {len(POSITIONS)}, fastest "
                              f"first: {', '.join(POSITIONS)}")
    return name


def settings(name: str) -> dict[str, object]:
    """Every number this position sets, as a fresh dict the caller may keep."""
    return dict(SETTINGS[position(name)])


def slower(name: str) -> str | None:
    """The next notch down, or None at `stop`. One notch, because a run that stops dead loses what is in
    flight and a run that slows keeps finishing what it started."""
    found = POSITIONS.index(position(name))
    return POSITIONS[found + 1] if found + 1 < len(POSITIONS) else None


def parse_setting(text: str) -> tuple[str, object]:
    """`boilers=2` as a name and a value, or a refusal saying what may be set and what it means."""
    name, _, value = text.partition("=")
    name, value = name.strip(), value.strip()
    if not value:
        raise Refused(f"`--set` takes `<name>=<value>`; {text!r} has no value")
    if name not in MEANS and name not in MIRRORED:
        known = {**MEANS, **{one: said for one, (said, _) in MIRRORED.items()}}
        raise Refused(f"`{name}` is not a setting the telegraph has. It sets: "
                              + "; ".join(f"{one} ({said})" for one, said in known.items()))
    if name in MIRRORED:
        said, allowed = MIRRORED[name]
        if value not in allowed:
            raise Refused(f"`{name}` is {said}, which is one of {', '.join(allowed)}; {value!r} is not")
        return name, value
    if name == "bar":
        return name, value.upper()
    try:
        return name, float(value) if name == "stage_scale" else int(value)
    except ValueError:
        raise Refused(f"`{name}` is {MEANS[name]}, which is a number; {value!r} is not one") from None


def adjusted(name: str, held: dict) -> bool:
    """Whether the numbers differ from the position they claim to be at.

    What the fleet board shows, and the reason it is a question at all: a board reporting a position the
    numbers do not match is a board that is lying, and a person reading it would act on the lever rather
    than on what is actually set.
    """
    wanted = SETTINGS.get(name)
    return wanted is not None and any(held.get(key) != value for key, value in wanted.items())


def described(name: str, held: dict) -> str:
    """How a board says where the telegraph is: the position, and whether the numbers still match it."""
    return f"{name}, adjusted" if adjusted(name, held) else name


def applied(name: str, held: dict) -> dict:
    """`held` with this position's numbers over it. Ringing resets every one of them, which is what makes
    a hurried `--set` safe: there is one action that puts everything back."""
    return {**held, "position": position(name), **settings(name)}


def scaled(stages: dict, scale: float) -> dict:
    """Every stage budget multiplied by the position's scale, each kept at a minute and a token at least.

    Zero would be a budget no stage can meet, which reads as "every stage failed" rather than as `stop` —
    and `stop` is not a thing stages do, it is a thing captains do at their next boundary.
    """
    found: dict[str, dict[str, int]] = {}
    for stage, row in stages.items():
        if not isinstance(row, dict):
            continue
        found[stage] = {key: max(1, int(round(value * scale))) if isinstance(value, int | float) else value
                        for key, value in row.items()}
    return found
