"""The big picture, read off a repository on the day it is adopted (15.11).

Phase 1 of the modelling method maps the territory once for the whole system — who acts, what the major
processes are, which systems this one talks to — and it is cheap, which is why it is done once rather than
per capability. Nothing built it for a repository the keel did not make: the survey read delivery facts, the
structure reader read shape, and the modelling skill asked a person questions the code could already answer.

So this reads it, and the rule is the survey's rule: proposed only from a line that says so, with the file
and the line it was said on, and nothing at all where nothing says. Four claims.

**Actors come from the authorisation the code already holds**, one per role named in a guard, and each one
carries what it **cannot** do — the surfaces some other role guards and this one is never named on. That is
the row a slice's `actor` field has nowhere to put, and the first thing a security pass and an access
classification both ask for. **External systems come from outbound calls and inbound hooks**, by host and
by the route that receives them. **Major processes come from the entry points `structure.md` already
lists**, written as proposed slices. And **no event is invented anywhere**: a name for something that
happened is a reading of behaviour, which is `/observe`'s job and not this one's.

The fifth claim is about what the page does with what it cannot read: every question it leaves carries its
*intention* and the *assumption it proceeded on*, because the agent that posts it is working where nobody
is watching, and a question with neither is a note a person cannot act on weeks later.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.big_picture import BigPicture, big_picture
from slipwai.layout import Layout
from slipwai.origin import Adoption
from slipwai.project.big_picture_page import ACTORS, BIG_PICTURE, big_picture_files
from slipwai.services import App
from slipwai.structure import structure

DELIVERY = Layout("delivery")

ROUTES = """\
import express from 'express';
const app = express();

app.get('/orders', requireRole('clerk'), listOrders);
app.post('/orders/:id/refund', requireRole('manager'), refund);

app.post('/hooks/stripe', verifySignature, onStripeEvent);

export async function charge(amount) {
  return fetch('https://api.stripe.com/v1/charges', {method: 'POST'});
}
"""
JOB = """\
import cron from 'node-cron';

cron.schedule('0 3 * * *', expireHolds);
"""


def wrapped(name: str = "shop", path: str = ".") -> App:
    return App(name, path, "service", "javascript", None, 0, generated=False, commands={"test": None},
               toolchain={"kind": "node", "ecosystem": "node"})


def repository(root: Path, routes: str = "", jobs: str = "") -> None:
    """A repository with a build the survey reads, and whatever source the case is about."""
    (root / "package.json").write_text('{"name": "shop", "scripts": {"start": "node src/routes.js"}}',
                                       encoding="utf-8")
    (root / "src").mkdir(parents=True, exist_ok=True)
    for name, text in (("routes.js", routes), ("jobs.js", jobs)):
        if text:
            (root / "src" / name).write_text(text, encoding="utf-8")


def read(root: Path) -> BigPicture:
    apps = [wrapped()]
    return big_picture(root, apps, structure(root, apps))


class ActorsTest(unittest.TestCase):
    """Who acts, read off the routes and the authorisation the code already holds."""

    def test_a_role_named_in_a_guard_is_an_actor_with_the_line_it_was_read_off(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository(root, ROUTES)
            found = read(root)
            named = {actor.name: actor for actor in found.actors}
            self.assertIn("clerk", named)
            self.assertIn("manager", named)
            self.assertEqual(named["clerk"].kind, "human")
            self.assertTrue(any("src/routes.js:4" in where for where in named["clerk"].evidence),
                            named["clerk"].evidence)

    def test_what_an_actor_does_is_the_surfaces_its_own_role_guards(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository(root, ROUTES)
            named = {actor.name: actor for actor in read(root).actors}
            self.assertEqual(named["clerk"].does, ("/orders",))
            self.assertEqual(named["manager"].does, ("/orders/:id/refund",))

    def test_what_it_cannot_do_is_a_surface_another_role_guards_and_it_is_never_named_on(self) -> None:
        """The one thing a slice's `actor` field has nowhere to carry, and the whole reason for the file."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository(root, ROUTES)
            named = {actor.name: actor for actor in read(root).actors}
            self.assertEqual(named["clerk"].cannot, ("/orders/:id/refund",))
            self.assertEqual(named["manager"].cannot, ("/orders",))

    def test_a_scheduled_job_is_a_system_actor_and_its_cannot_is_a_question_not_a_blank(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository(root, ROUTES, JOB)
            found = read(root)
            cron = next(actor for actor in found.actors if actor.name == "systems/cron")
            self.assertEqual(cron.kind, "system")
            self.assertEqual(cron.cannot, ())
            self.assertTrue(any("systems/cron" in gap.question for gap in found.gaps),
                            "a `cannot` the code cannot name is asked, never defaulted")

    def test_a_repository_whose_code_names_no_role_proposes_no_actor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository(root, "const app = require('express')();\napp.get('/health', ok);\n")
            self.assertEqual(read(root).actors, ())


class ExternalsTest(unittest.TestCase):
    """What this system talks to, by the call out and the hook in."""

    def test_an_outbound_host_is_an_external_system_with_its_line(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository(root, ROUTES)
            stripe = next(seen for seen in read(root).externals if seen.what == "api.stripe.com")
            self.assertEqual(stripe.where, "src/routes.js:10")
            self.assertIn("outbound", stripe.how)

    def test_a_route_that_receives_a_hook_is_an_external_system_calling_in(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository(root, ROUTES)
            hook = next(seen for seen in read(root).externals if seen.what == "/hooks/stripe")
            self.assertEqual(hook.where, "src/routes.js:7")
            self.assertIn("inbound", hook.how)

    def test_a_host_that_is_nobody_s_system_is_not_one(self) -> None:
        """A schema URL, a licence, a documentation link: noise every repository carries."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository(root, (
                "// see https://www.w3.org/TR/xml/ and https://example.com/docs\n"
                "const schema = 'http://localhost:5432/shop';\n"
            ))
            self.assertEqual(read(root).externals, ())


class ProcessesTest(unittest.TestCase):
    """The major processes, from the entry points the structure reader already lists."""

    def test_an_entry_point_is_a_proposed_slice_with_the_file_it_was_read_off(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository(root, ROUTES)
            found = read(root)
            self.assertTrue(found.processes, "the structure reader lists `npm start`")
            self.assertTrue(all(seen.where for seen in found.processes))


class PageTest(unittest.TestCase):
    """`survey/big-picture.md` and `docs/event-model/actors.yaml`, written on the day of adoption."""

    def files(self, root: Path) -> dict[str, str]:
        return big_picture_files(read(root), DELIVERY, Adoption())

    def test_the_page_names_the_actors_the_externals_and_the_processes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository(root, ROUTES, JOB)
            page = self.files(root)[DELIVERY.under(BIG_PICTURE)]
            self.assertIn("# The big picture", page)
            for expected in ("clerk", "manager", "systems/cron", "api.stripe.com", "/hooks/stripe",
                             "src/routes.js:4"):
                self.assertIn(expected, page)

    def test_the_page_names_no_event(self) -> None:
        """Phase 1 maps the territory. A name for something that happened is `/observe`'s to read."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository(root, ROUTES, JOB)
            page = self.files(root)[DELIVERY.under(BIG_PICTURE)]
            self.assertNotIn("`evt`", page)
            self.assertIn("names no event", page)

    def test_every_question_carries_its_intention_and_the_assumption_it_proceeded_on(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository(root, ROUTES, JOB)
            found = read(root)
            self.assertTrue(found.gaps)
            for gap in found.gaps:
                self.assertTrue(gap.intention, gap.question)
                self.assertTrue(gap.assumption, gap.question)
            page = self.files(root)[DELIVERY.under(BIG_PICTURE)]
            self.assertIn("*Intention:*", page)
            self.assertIn("*Proceeded on:*", page)

    def test_the_role_catalogue_is_the_shape_the_modelling_skill_writes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository(root, ROUTES, JOB)
            catalogue = self.files(root)[DELIVERY.under(ACTORS)]
            self.assertIn("version: 1", catalogue)
            self.assertIn("actors:", catalogue)
            self.assertIn("  - name: clerk", catalogue)
            self.assertIn("    kind: human", catalogue)
            self.assertIn("    does:", catalogue)
            self.assertIn("    cannot:", catalogue)
            self.assertIn("/orders/:id/refund", catalogue)

    def test_a_repository_the_code_says_nothing_about_gets_a_page_that_says_so(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository(root, "export const noop = () => undefined;\n")
            files = self.files(root)
            page = files[DELIVERY.under(BIG_PICTURE)]
            self.assertIn("nothing in the code names a role", page)
            self.assertNotIn(DELIVERY.under(ACTORS), files,
                             "a catalogue with no actor in it is a file that invents one later")


if __name__ == "__main__":
    unittest.main()
