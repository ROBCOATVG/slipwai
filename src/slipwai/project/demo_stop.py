"""The demo stop of `commands/drive.md`: what a pause for feedback has to hand the actor, and open with.

Its own module because it is the one part of the ladder that faces the product owner rather than the agent,
and because it has grown by evidence: the running process (a demo whose server the turn had already stopped),
the question at the end (a stop that looked like a pause), and now the board at the top — a product owner who
had to ask how many slices there were, and read fifty-eight tasks as fifty-eight features. The board is
read off artifacts like the entry stage is, so the sources are named per profile: every profile archives its
accepted slices, and the event profile also carries a `status` per slice in the model.
"""
from __future__ import annotations


def board_sources(event: bool) -> str:
    """Where the progress board is read from, per profile — shared with `/where-are-we`, which draws the same
    board between demos, so the two commands cannot name different artifacts."""
    claims = (
        "and the forge's `slice/<id>` branches (`git ls-remote --heads origin 'slice/*'`), which are the claims —"
        " read, never assumed: where that command fails the board says the claims could not be read, and"
        " shows no slice as unclaimed on the strength of a failed read"
    )
    sources = (
        "the ordered split and its `## Slice graph`, the register at `specs/<feature>/slices/README.md` — a row\n"
        "marks a slice accepted; a slice with `plan.md` under `slices/<id>/` and no row is in flight —\n"
        + claims
    )
    if event:
        sources = (
            "the ordered split and its `## Slice graph` (or each slice's `depends_on` in "
            "`docs/event-model/model.yaml`), each slice's `status` in `docs/event-model/model.yaml` —\n"
            "`implemented` is done, `planned` may run alongside a sibling, and `plan.md` under `slices/<id>/` "
            "alone means\nin flight —\n"
            + claims
        )
    return sources


def demo_stop(event: bool, baseline: str = "") -> str:
    """The `### What the demo stop has to contain` section, for the profile's artifacts.

    `baseline` is where this project's baseline styles live — each browser app's path, spelled as the
    project spells it — and empty in a project with no browser surface, which drops the one pre-demo check
    only a screen can fail. First slices kept arriving at the demo on browser defaults, Times New Roman on
    white, and an actor asked to judge whether the thing works reads an unstyled page as unfinished before
    they have used it.
    """
    section = DEMO_STOP.replace("{board_sources}", board_sources(event))
    return section.replace("{styled}", STYLED.replace("{baseline}", baseline) if baseline else "")


STYLED = """**Before the demo, check every screen this slice adds or changes is styled.** It uses the
project's own styles — `docs/design.md`, or the design notes in the constitution or under `specs/` — or, where
the slice needs something those do not cover, the baseline stylesheet and design tokens in {baseline} extended
rather than bypassed. A screen still on browser defaults is a reason not to demo yet: the actor is being asked
whether the thing works, and an unstyled page answers a different question first. Then read the files the
slice changed under the browser app against `skills/web-interface-guidelines` — labels, focus, forms, motion,
typography, the anti-patterns it lists — and fix what it finds before the demo rather than carrying it as a
note. Record both checks with the others, naming the screens, where their styles came from, and what the
review found.

"""
DEMO_STOP = """### What the demo stop has to contain

The stop is a pause for feedback, so it opens with where the product stands and ends with the thing the
actor uses and a question only they can answer.

**It opens with the progress board.** The actor should never have to ask how many slices there are or how
far along the work is: that question, asked, means the board was missing — and between demos, `/where-are-we`
draws the same board on demand. Seven parts, in this order, every
line in the actor's vocabulary rather than a slice id or a test name:

- ✅ **Works now** — every accepted slice, one line each, as the thing the actor can do
- 🆕 **New in this demo** — what this slice added: the thing about to be shown
- ⬜ **Still to come** — the remaining slices of the split, in order and by name, headed by one line of
  counts: `N of M slices accepted`
- ⚠️ **Not working yet** — every deliberate stub and every release constraint still in force, named as
  such, so a hole reads as "not yet" and not as a fault the actor has to find
- 🔀 **Ready (parallel)** — every slice that can start now: not done, every `depends_on` done, and not
  pre-empted by an open `CRITICAL` — in two groups, *claimed* (a `slice/<id>` branch on the forge, by whom
  and how long ago) and *unclaimed*, so another session knows which sibling is free
- ➡️ **Next (this session)** — the slices this `/drive` will take: every unclaimed ready slice whose
  contract is settled, concurrently; or the earliest ready slice in split order where the harness cannot
  delegate, unless the user picks another ready one
- ⛔ **Blocked** — remaining slices waiting on unmet `depends_on`, or an open `CRITICAL` ahead of them

The board is derived from artifacts, not memory, the way the entry stage is:
{board_sources}.

The task count is not on it. Tasks stay in `tasks.md` for whoever is doing the work; the board counts
slices, because a slice is a thing the actor can use and a task is not, and fifty-eight tasks over two
slices reads as fifty-eight features to somebody who did not write them.

**It ends with the thing the actor uses.** The final turn states, in its own words:

- the literal command or URL that runs it — the exact text to paste, not a description of where to look
- the seed data it needs, or that it needs none
- the result to expect, in the actor's vocabulary rather than a test name

**When "the thing the actor uses" is a long-lived process** — a dev server, a container — starting it to
verify the command works and then stopping it once verification passes is not a demo, it is a test you ran
alone. The actor's first action is opening what you just closed. Start it in the background, verify it, and
leave it running past the end of the turn; say plainly that it is still up rather than letting the actor
discover a dead port.

{styled}**When the slice touched how the application starts** — constructors, dependency injection, configuration,
module registration, the build — the demo is the application starting with the change in place, by the command
`run-the-app` records (`make smoke` where one is recorded), and never the suite passing in its place: a suite
that never builds the context cannot see a constructor the container cannot call, and slices have shipped that
way, converged and green, with an application that no longer started.

Then it asks directly what using it revealed. A summary of what was built, a compliance table, or a green
gate report is evidence *for* a demo and never the demo itself: it hands the actor nothing to use and asks
them nothing. **A turn that reaches the demo without asking that question has not paused for feedback — it
has stopped**, and from the outside those look identical until the slice sits idle waiting for an
invocation nobody knew was needed.
"""
