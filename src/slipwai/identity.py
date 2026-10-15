"""Who signs in to this product, asked once, and the two identity axes an answer settles.

Two axes carry identity, and they are two for a good reason: `auth` is the people who *run* the product —
staff, operators, support — and `users` is the people it is *for*, with self-registration, verification and
password reset and a login the browser app owns. A product with an admin console behind the company
directory and customers in front of a separate tenant genuinely has two answers, and the day somebody runs
the two together is the day staff accounts can be created from the internet.

**Both were nevertheless asked of everybody, and that is the fault this module fixes.** Most projects have
one login and one set of people, and that project met two prompts a paragraph apart, worded alike, each
offering the same list of providers. Answering the same name twice looked like a formality and was in fact
a request for two realms; answering only one left the reader unsure which half they had turned off. The
question a person can actually answer is the one about people, so that is the question asked, and the axes
are filled in from it.

**The answers map onto the axes, never beside them.** Nothing downstream learns a new word: `generate`
still takes `--auth` and `--users`, a quickstart still answers both, and what comes out of here is the pair
of flags somebody could have typed. This is the interview's shape, not a sixth axis, which is why `axes.py`
still holds the catalogue to exactly five.

**One provider for everybody is the external axis.** That is the half whose login the browser app really
owns and whose sign-up and reset are real; the internal axis is the one that assumes somebody else makes
the account. Staff-only is the internal axis for the same reason read the other way: an internal tool that
had been given the external answer would ship with public self-registration switched on, which is the one
mistake this question exists to prevent.
"""
from __future__ import annotations

from collections.abc import Mapping

from .catalog import CATALOG, axis_applies

#: The two axes that carry identity, in the order the catalogue asks them.
INTERNAL, EXTERNAL = "auth", "users"
AXES = (INTERNAL, EXTERNAL)
#: What the question is called where an answer is written down. Not a flag and never an axis: what it
#: decides is which axes get asked, and `settled` turns it back into the two answers that are.
WHO = "who"
LABEL = "Who signs in"
PROMPT = "Who signs in to this product?"
EVERYONE, STAFF, SEPARATELY = "everyone", "staff", "separately"
#: The commonest answer first, and the pair last: a reader meeting this list should recognise their own
#: product in the first row or the second, and reach the third only by having a reason.
ROWS: tuple[tuple[str, str], ...] = (
    (EVERYONE, "everyone, through one identity provider — the people who run it and the people it is for"),
    (STAFF, "people who work here, and nobody else — no public sign-up"),
    (SEPARATELY, "staff and customers, through separate issuers — a realm or tenant each, asked separately"),
)
DEFAULT = EVERYONE
WHY = ("Identity is two things in a system that has two kinds of people, and one thing in a system that "
       "has one. Answer this and the right question follows; `--auth` and `--users` are still there to "
       "give separately, and `./init` can change either later.")
#: What the provider question is called once this has been answered. The catalogue's own two prompts where
#: both are asked, because there the distinction is the point; plain words where one answer serves, because
#: there "internal" and "external" are a distinction nobody has made.
CALLED = {EVERYONE: "Authentication", STAFF: "Staff authentication"}
SAYS = {
    EVERYONE: "Who signs everybody in. One OIDC issuer for the whole product, with sign-up, verification "
              "and password reset, and a login the browser app owns. Answer `none` to leave identity until "
              "later — nothing here is hard to add afterwards.",
    STAFF: "Who signs the people who work here in. One OIDC issuer, and no public sign-up: an account is "
           "made for somebody rather than by them. Answer `none` to leave identity until later.",
}


def applies(profile: str, backend: str, target: str) -> bool:
    """Whether to ask this at all: only where both axes could have been asked anyway.

    Asked of the catalogue rather than assumed, because the two axes carry a `requires` of their own — a
    service with no inbound HTTP has nobody to sign in — and a question standing in for two that are not
    being asked would be a question about nothing.
    """
    return all(axis_applies(axis, profile, backend, target) for axis in AXES)


def asks(who: str) -> tuple[str, ...]:
    """The identity axes this answer leaves to be asked, in the catalogue's own order."""
    if who == SEPARATELY:
        return AXES
    return (EXTERNAL,) if who == EVERYONE else (INTERNAL,)


def absent(axis: str) -> str:
    """The no-infrastructure answer to one axis: what the axis nobody is signed in on is given."""
    return str(CATALOG["axes"][axis]["absent"])


def label(who: str, axis: str) -> str:
    """What the provider question for this axis is headed, given who was said to sign in."""
    return str(CATALOG["axes"][axis]["prompt"]) if who == SEPARATELY else CALLED[who]


def says(who: str, axis: str) -> str:
    """The paragraph printed under that heading."""
    return str(CATALOG["axes"][axis]["description"]) if who == SEPARATELY else SAYS[who]


def settled(who: str, given: Mapping[str, str | None]) -> dict[str, str]:
    """Both axes, answered: what was chosen on the axis that was asked, and `absent` on the one that was not.

    Written out for both, always. An axis left as `None` would fall through to the generator's own default,
    and "nobody asked you about staff accounts" and "you said there are none" have to be the same answer
    here or the question would quietly decide less than it appears to.
    """
    asked = asks(who)
    return {axis: (given.get(axis) or absent(axis)) if axis in asked else absent(axis) for axis in AXES}


def implied(answers: Mapping[str, str | None]) -> str:
    """Which answer a pair of axis answers already given stands for.

    What the question shows as its default when a quickstart has answered both, so a person reading the
    board sees the shape they were given rather than this module's own first guess.
    """
    held = {axis: (answers.get(axis) or "") for axis in AXES}
    staff = held[INTERNAL] not in ("", absent(INTERNAL))
    customers = held[EXTERNAL] not in ("", absent(EXTERNAL))
    if staff and customers:
        return SEPARATELY
    return STAFF if staff else EVERYONE


__all__ = ["AXES", "EXTERNAL", "INTERNAL", "ROWS", "WHO", "applies", "asks", "implied", "label", "says",
           "settled"]
