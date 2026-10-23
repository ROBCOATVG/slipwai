"""The hand protocol of `commands/cruise.md`: what `/cruise` does at the demo stop instead of handing the slice
to a person.

Split from `cruise.py` because this is the one section that reads a
setting a delegate cannot see for itself — `hand`, where the hand's ladder starts — and the one that undoes
what the ladder does for a person: `commands/sail.md` leaves the demo's app running for the actor to open,
and under `/cruise` no actor is coming, so the app is stopped once the verdict is in or the next slice's demo
finds its port taken.
"""
from __future__ import annotations

from .cruise_agents import BROWSER, DEMO_LOG, EVIDENCE, HAND
from .cruise_record import DEMO_ENTRY

CONFIG = ".specify/cruise.json"


def hand_section(make: str) -> str:
    return f"""## Demonstrating: the hand protocol

At the demo stop, compose everything `commands/sail.md` says the stop must contain — the board, the literal
command or URL, the seed data, the expected result, the running process — and hand it, with the slice's
acceptance script, to one fresh `{HAND}` delegate instead of a person. Where Try it is running, the URL and
the links are Try it's (`python3 scripts/agents/try_it.py status` prints `url` and the capability's
`links[]`), so the hand walks the app a person would open rather than one started for the walk. The brief also names where the hand's
ladder starts, which is `{CONFIG}`'s `hand` and nothing the delegate can read for itself: `browser` is
`{BROWSER}` where the slice has a screen, then a browser tool the harness exposes, then HTTP, then the CLI;
`http` starts at HTTP; `cli` at the CLI — each rung falling through to the next where it cannot run and saying
so, and none climbing back above the one the setting names. Its verdict is the actor's: `accepted`
continues to *After acceptance*, `behaviour` re-enters the ladder at the stage that owns the change with the
example that shows it, `implementation` is a task. Record `outcome=` on the demo entry from the verdict, and
write `accepted-by: {HAND}` beside the register row or status flip, so a person can tell which demos a person
has seen.

**Then stop what the demo started.** The ladder leaves the app running past the end of the turn because the
actor's first action is opening it; here the actor was the hand, and it has finished. Try it is not what the
demo started and is never stopped here — a person has it open. Once the verdict is recorded, end what was — `{make} demo-down` or `{make} services-down` where the demo used them, otherwise the process
the stop started — before Phase 4 or the next slice's delegate, which starts what its own demo needs and would
otherwise find the port taken; the captain ends anything a stage still leaves running. The hand's writes are
`{DEMO_LOG}` — one section per demo — and its evidence under `{EVIDENCE}`:

```markdown
{DEMO_ENTRY}
```
"""
