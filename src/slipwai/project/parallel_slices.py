"""The two sentences of `commands/sail.md`'s concurrency rules that a declaration decides, and nothing else.

Ready-set selection used to end with "one slice per session; name the rest so another session can claim a
sibling" — the parallelism the method promises (slices that share only an event schema are independent, and
Principle V makes it true in the tests) exploited only by running `/sail` twice. Once the contract is
settled a session can run every ready slice at once, one delegate per slice, and the reference
implementations — Nebulit's build kits, Dilger's Ralph loop — show the three things that have to be true
for that to work: a claim, so two drivers never take the same slice; a written shared-surface rule, held
at the gate; and one slice per delegate, strictly sequential inside it.

Those rules are the asset's own words now — `assets/toolkit/commands/sail.md`, *Ready-set selection*
through *Fairways* — because they are the same words in every project. What is left here is the three
places they branch, and each is a branch inside a sentence rather than a section somebody could point at
the edges of (`docs/generated-prose.md`): what says a slice is finished, where the slice graph is read
from, and what makes two slices independent. The last of those is the shape 16.3 met — the alternatives
are whole sentences, but the paragraph they open carries on past them, so neither marker could sit at the
branch's end.

What "done" means changed with the rules: a slice's plan and tasks live under `slices/<id>/` from the day
they are written, so their being there no longer says the slice shipped — the model's `status` does on the
event profile, and the register at `slices/README.md` does otherwise.
"""
from __future__ import annotations


def done_marker(event: bool) -> str:
    """What says a slice is finished, per profile — read by the ready set, the board and Phase 4 alike."""
    if event:
        return "`status: implemented` in `docs/event-model/model.yaml`"
    return "a row in the register at `specs/<feature>/slices/README.md`"


def slice_graph(event: bool) -> str:
    """Where the slice graph is, said inside the sentence that tells a session to read it."""
    if event:
        return "each slice's `depends_on` in\n   `docs/event-model/model.yaml`, or `## Slice graph` in the split"
    return "`## Slice graph` in the split"


def independence(event: bool) -> str:
    """Why two ready slices may run at once, named for the contract this profile actually has.

    Both answers open the *Running ready slices concurrently* paragraph and the paragraph goes on past
    them, which is what keeps this a value rather than a section of the page.
    """
    if event:
        return ("Slices that share an event schema are independent: the schema is the contract between them, and\n"
                "Principle V — seed from synthetic events — is what makes that true in the tests.")
    return ("Slices that share only a written contract — a route, a schema, a port — are independent: neither\n"
            "has to be built first, and each is tested against the contract rather than against the other.")
