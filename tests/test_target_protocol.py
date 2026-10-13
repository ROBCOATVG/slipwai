"""The target protocol: what a `TARGET` object answers, and what the keel refuses when it does not.

The executable half of a target package. `target.json` is the declaration a catalog row is made from; this
is the part that has to be imported — the stacks, the scripts, the docs page, the preflight tools, the
image registry and the pipeline's sign-in — and it is declared here as the backend protocol is declared in
`registry.py`, so a page and a check cannot drift from each other.

**Required means required of a *managed* target.** A target the keel does not provision — the shape
`existing` has, where a project deploys somewhere the keel does not own — answers none of it, and holding
it to the stacks it has no business shipping would make the one honest unmanaged row impossible.
"""
from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401

from slipwai import target_protocol
from slipwai.target_protocol import SHAPES, Target, faults

ANSWERS: dict = {
    target_protocol.SHAPES: {"bootstrap": ("bootstrap/main.tf",), "service": ("service/main.tf",)},
    target_protocol.SCRIPTS: {"scripts/deploy.py": "scripts/deploy.py"},
    target_protocol.TOOLS: (("tofu", "what applies the stacks", "https://opentofu.org"),),
    target_protocol.IMAGE_REGISTRY: {"cloud": "Cumulus", "registry": "CR",
                                     "example": "cumulus.invalid/", "runtime": "Boxes"},
    target_protocol.PIPELINE: {"cli": "", "credentials": "      - uses: cumulus/login@v1\n",
                               "build_cli": "", "registry_login": "      - run: cumulus registry login\n",
                               "environment": "  CUMULUS_REGION: ${{ vars.CUMULUS_REGION }}\n"},
    target_protocol.README_WORDS: {"runtime": "one box per app", "site": " The browser app is a bucket.",
                                   "credentials": "a sign-in the `cumulus` CLI can find"},
    target_protocol.AGENT_RULES: "- This project deploys to Cumulus from the pipeline, and nothing else does.\n",
    target_protocol.ADD_COMMANDS: {"service": "- one more box\n", "web": "- the site is behind the edge\n"},
    target_protocol.DOCS_PAGES: {"docs/deployment.md": lambda project, apps: "# Where this goes\n"},
}


def target(changes: dict | None = None) -> Target:
    """A whole target with those members changed; a member set to None is one it does not answer."""
    answers = {**ANSWERS, **(changes or {})}
    return Target(name="cumulus", answers={k: v for k, v in answers.items() if v is not None})


class ProtocolTest(unittest.TestCase):
    def test_every_member_the_protocol_declares_has_a_name_a_kind_and_a_shape(self) -> None:
        for member in target_protocol.PROTOCOL:
            with self.subTest(member=member.name):
                self.assertTrue(member.name and member.shape)
                self.assertIsNotNone(member.kind)

    def test_no_member_is_declared_twice(self) -> None:
        names = [member.name for member in target_protocol.PROTOCOL]
        self.assertEqual(sorted(names), sorted(set(names)))

    def test_both_shapes_are_named_where_the_protocol_can_be_read(self) -> None:
        """A managed target has two stacks and always has: the account's, written once, and the service's,
        applied per environment. The pair is declared, not left to each package to name."""
        self.assertEqual(target_protocol.BOTH_SHAPES, ("bootstrap", "service"))


class FaultsTest(unittest.TestCase):
    def test_a_whole_managed_target_has_no_faults(self) -> None:
        self.assertEqual(faults(target(), managed=True), [])

    def test_a_missing_required_member_is_named(self) -> None:
        found = faults(target({target_protocol.SHAPES: None}), managed=True)
        self.assertEqual(found, ["target cumulus is missing shapes"])

    def test_an_unmanaged_target_owes_none_of_it(self) -> None:
        self.assertEqual(faults(Target(name="elsewhere"), managed=False), [])

    def test_a_member_answered_with_the_wrong_kind_is_named_with_both_kinds(self) -> None:
        found = faults(target({target_protocol.TOOLS: "tofu"}), managed=True)
        self.assertEqual(len(found), 1)
        self.assertIn("tools", found[0])
        self.assertIn("str", found[0])
        self.assertIn("tuple", found[0])

    def test_a_key_that_is_not_a_member_is_refused_rather_than_ignored(self) -> None:
        one = Target(name="cumulus", answers={**ANSWERS, "shapes": {}})  # type: ignore[dict-item]
        found = faults(one, managed=True)
        self.assertEqual(len(found), 1)
        self.assertIn("not a protocol member", found[0])

    def test_a_shape_the_protocol_does_not_know_is_refused_naming_the_two(self) -> None:
        found = faults(target({SHAPES: {"bootstrap": ("a.tf",), "service": ("b.tf",), "extra": ("c.tf",)}}),
                       managed=True)
        self.assertEqual(len(found), 1)
        self.assertIn("extra", found[0])

    def test_a_shape_left_out_is_refused_by_name(self) -> None:
        found = faults(target({SHAPES: {"bootstrap": ("a.tf",)}}), managed=True)
        self.assertEqual(len(found), 1)
        self.assertIn("service", found[0])

    def test_a_shape_with_no_files_in_it_is_a_stack_that_applies_nothing(self) -> None:
        found = faults(target({SHAPES: {"bootstrap": (), "service": ("b.tf",)}}), managed=True)
        self.assertEqual(len(found), 1)
        self.assertIn("bootstrap", found[0])

    def test_a_tool_that_does_not_say_why_and_where_is_refused(self) -> None:
        found = faults(target({target_protocol.TOOLS: (("tofu",),)}), managed=True)
        self.assertEqual(len(found), 1)
        self.assertIn("where to get it", found[0])

    def test_the_name_a_target_gives_itself_is_held_to_what_a_name_may_be(self) -> None:
        found = faults(Target(name="Cumulus Cloud", answers=ANSWERS), managed=True)
        self.assertEqual(len(found), 1)
        self.assertIn("lower-case name", found[0])

    def test_every_fault_is_named_at_once_rather_than_the_first(self) -> None:
        one = Target(name="cumulus", answers={target_protocol.TOOLS: "tofu"})
        self.assertEqual(len(faults(one, managed=True)), len(target_protocol.required()))


if __name__ == "__main__":
    unittest.main()


def whole(changes: dict | None = None) -> Target:
    """A managed target answering every member a managed target owes, with those changed."""
    return target(changes)


class ExtendedProtocolTest(unittest.TestCase):
    """The members 10.1 did not name, found by reading what the keel actually reads per target.

    10.1 named six from the five modules it read. 10.3 read the rest of the surface — the README's
    *Production* section, the agent rules, what `add-service` says afterwards, and the deploy workflow's own
    parts — and each of those is a table keyed by a cloud's name, which is exactly what a protocol member is
    for. A member each rather than one `prose` bag: a refusal has to be able to say which one is missing.
    """

    def test_a_whole_managed_target_answering_all_of_them_has_no_faults(self) -> None:
        self.assertEqual(faults(whole(), managed=True), [])

    def test_a_setup_hook_has_to_be_a_script_the_project_is_given(self) -> None:
        """A hook `./init` is never given is one it never runs, and nothing would say so until a machine
        turned out short a tool the target promised to install."""
        found = faults(Target("x", {target_protocol.SETUP: "scripts/setup.py", SHAPES: {}}), managed=False)
        self.assertTrue(any("setup hook" in line for line in found), found)
        carried = faults(Target("x", {target_protocol.SETUP: "scripts/setup.py",
                                      target_protocol.SCRIPTS: {"scripts/setup.py": "scripts/setup.py"}}),
                         managed=False)
        self.assertFalse(any("setup hook" in line for line in carried), carried)
        self.assertFalse(target_protocol.SETUP.required)

    def test_the_pipeline_is_a_member_a_managed_target_owes(self) -> None:
        self.assertIn("pipeline", [member.name for member in target_protocol.required()])

    def test_a_pipeline_short_a_part_the_workflow_reads_is_refused_naming_it(self) -> None:
        """The shape around the parts is the promise and not the cloud, so the keel reads each by name."""
        short = {key: "" for key in target_protocol.KEYS["pipeline"] if key != "credentials"}
        found = faults(whole({target_protocol.PIPELINE: short}), managed=True)
        self.assertEqual(len(found), 1)
        self.assertIn("credentials", found[0])

    def test_readme_words_short_a_noun_the_section_is_written_round_is_refused(self) -> None:
        short = {"runtime": "one box per app"}
        found = faults(whole({target_protocol.README_WORDS: short}), managed=True)
        self.assertEqual(len(found), 1)
        for noun in ("site", "credentials"):
            self.assertIn(noun, found[0])

    def test_add_commands_short_what_adding_a_frontend_means_is_refused(self) -> None:
        found = faults(whole({target_protocol.ADD_COMMANDS: {"service": "x"}}), managed=True)
        self.assertEqual(len(found), 1)
        self.assertIn("web", found[0])

    def test_an_image_registry_that_does_not_say_where_or_how_is_refused(self) -> None:
        found = faults(whole({target_protocol.IMAGE_REGISTRY: {"cloud": "Cumulus"}}), managed=True)
        self.assertEqual(len(found), 1)
        for key in ("registry", "example", "runtime"):
            self.assertIn(key, found[0])

    def test_flag_transports_are_never_required(self) -> None:
        """Absence is the answer "this cloud has no flag store", which is an honest thing for one to say."""
        self.assertNotIn("flag_transports", [member.name for member in target_protocol.required()])

    def test_a_flag_transports_answer_that_names_no_default_is_refused(self) -> None:
        found = faults(whole({target_protocol.FLAG_TRANSPORTS: {"opt_in": "appconfig"}}), managed=True)
        self.assertEqual(len(found), 1)
        self.assertIn("default", found[0])

    def test_an_unmanaged_target_owes_none_of_the_new_members_either(self) -> None:
        self.assertEqual(faults(Target(name="cumulus"), managed=False), [])
