"""The plugin is the generated project's material with the project taken away.

The whole risk of shipping a second install route is that it becomes a second source of truth: somebody
edits a command in the plugin, the generated project keeps the old one, and the two answers to "what does
`/sail` say" are both live. So the test that matters is not that a plugin can be written — it is that every
file in it is byte-for-byte what `./init` writes at the same path, because one is rendered from the other.
"""
from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import checkout_packages

from slipwai import plugin
from slipwai.assets import VERSION
from slipwai.cli_package import package_main
from slipwai.examples import EXAMPLE_MARKER, stamp_pseudocode_note
from slipwai.layout import AT_ROOT
from slipwai.package_new import VERBS
from slipwai.project.agent_settings import harness_hooks
from slipwai.project.agents import agent_files
from slipwai.project.commands import command_files
from slipwai.scaffold import project_files
from slipwai.selection import resolve_selection
from slipwai.services import default_apps
from slipwai.toolkit import skill_of


class ManifestTest(unittest.TestCase):
    """`.claude-plugin/plugin.json`: the one file the harness reads before it reads anything else."""

    def manifest(self, profile: str = "standard") -> dict:
        return json.loads(plugin.files(profile)[plugin.MANIFEST])

    def test_the_manifest_names_the_plugin_and_carries_the_keels_version(self) -> None:
        """One version, from `VERSION`, like everything else — never a number written twice."""
        found = self.manifest()
        self.assertEqual(found["name"], plugin.NAME)
        self.assertEqual(found["version"], VERSION)
        self.assertTrue(found["description"])

    def test_the_manifest_is_json_a_harness_can_read(self) -> None:
        """It ends with a newline and has no trailing comma: it is read by somebody else's parser."""
        text = plugin.files()[plugin.MANIFEST]
        self.assertTrue(text.endswith("\n"))
        json.loads(text)

    def test_a_profile_the_catalogue_has_not_got_is_refused_by_name(self) -> None:
        """Not an empty plugin: a typo'd profile that rendered the standard one would ship the wrong commands."""
        with self.assertRaises(Exception) as caught:
            plugin.files("event-modeling")
        self.assertIn("event-modeling", str(caught.exception))


class RenderedNotKeptTest(unittest.TestCase):
    """Nothing here holds a second copy: every file is the function `scaffold.py` calls for that path."""

    rendered: dict[str, str]

    @classmethod
    def setUpClass(cls) -> None:
        cls.rendered = plugin.files("standard")

    def test_every_generated_command_is_what_command_files_answers_for_that_path(self) -> None:
        for path, text in command_files(False, [], "none", AT_ROOT, None).items():
            self.assertEqual(self.rendered.get(path), text, path)

    def test_the_commands_the_toolkit_ships_whole_come_through_as_they_are(self) -> None:
        """`/chart`, `/example-map` and `/mockups` are prose, not a rendering of anything."""
        for path in ("commands/chart.md", "commands/example-map.md", "commands/mockups.md"):
            self.assertIn(path, self.rendered)

    def test_sail_is_there_because_it_is_what_a_person_types_first(self) -> None:
        self.assertIn("commands/sail.md", self.rendered)

    def test_every_agent_type_is_what_agent_files_answers(self) -> None:
        found = {path: text for path, text in self.rendered.items() if path.startswith("agents/")}
        self.assertEqual(found, agent_files(AT_ROOT))

    def test_it_renders_the_three_canonical_directories_and_the_hooks_and_nothing_else(self) -> None:
        own = {plugin.MANIFEST, plugin.HOOKS}
        strays = sorted(path for path in self.rendered
                        if path not in own and not path.startswith(("commands/", "agents/", "skills/")))
        self.assertEqual(strays, [])


class NoLanguageTest(unittest.TestCase):
    """The keel names no language, and a plugin is rendered with no project to ask."""

    rendered: dict[str, str]

    @classmethod
    def setUpClass(cls) -> None:
        cls.rendered = plugin.files("standard")

    def test_no_rendered_file_carries_an_unanswered_example_marker(self) -> None:
        """A marker that reached a person's machine is a skill whose code block says `{{example: ...}}`."""
        for path, text in self.rendered.items():
            self.assertIsNone(EXAMPLE_MARKER.search(text), path)

    def test_a_skill_written_around_a_languages_code_is_left_out_whole(self) -> None:
        """Not half of it: a skill whose SKILL.md resolved and whose resources did not is worse guidance
        than one that is not there."""
        shipped = {skill_of(path) for path in self.rendered if path.startswith("skills/")}
        for left_out in ("domain-driven-design", "event-sourcing", "hexagonal-architecture", "testing"):
            self.assertNotIn(left_out, shipped)

    def test_the_skills_that_need_no_language_are_all_still_there(self) -> None:
        """`tdd`, `refactoring`, `find-gaps` — the way work is done here, which is most of the catalogue."""
        shipped = {skill_of(path) for path in self.rendered if path.startswith("skills/")}
        for kept in ("tdd", "refactoring", "find-gaps", "architecture-decisions"):
            self.assertIn(kept, shipped)
        self.assertGreater(len(shipped), 30)


@unittest.skipUnless(checkout_packages.installed("toy"), "compares against a generated project")
class AgainstAGeneratedProjectTest(unittest.TestCase):
    """What `./init` writes at these paths, against what the plugin renders for them."""

    rendered: dict[str, str]
    generated: dict[str, str]

    @classmethod
    def setUpClass(cls) -> None:
        cls.rendered = plugin.files("standard")
        selection = resolve_selection({}, "standard", "toy-plain", "none")
        cls.generated = project_files(
            "plugin-proof", "standard", "none", default_apps("toy-plain", "none", selection), AT_ROOT, None)

    def test_every_skill_the_project_also_has_is_that_project_file_without_its_own_disclaimer(self) -> None:
        """The one difference, and it is the project's to carry: a project whose language is not TypeScript
        stamps every skill holding a raw TypeScript fence with a note saying whose language it is not
        (`examples.stamp_pseudocode_notes`). That note names the project's languages, and a plugin has
        none, so the skill is shipped as it is written. Everything else is the same bytes."""
        shared = [path for path in self.rendered if path.startswith("skills/") and path in self.generated]
        self.assertTrue(shared)
        for path in shared:
            theirs, ours = self.generated[path], self.rendered[path]
            self.assertIn(theirs, (ours, stamp_pseudocode_note(ours, ["toy"])), path)

    def test_every_agent_type_the_plugin_ships_is_the_projects_own_file(self) -> None:
        agents = {path: text for path, text in self.rendered.items() if path.startswith("agents/")}
        self.assertTrue(agents)
        for path, text in agents.items():
            self.assertEqual(text, self.generated[path], path)

    def test_the_plugin_ships_every_command_a_project_of_this_profile_has(self) -> None:
        """The *set* is the same, which is what "the same files" means. The text of one is adapted to a
        project's own toolchain — `/mutation` names the backends it has — and a plugin has no toolchain to
        name, so parity here is the path list and the function behind each path, not the bytes."""
        plugins = {path for path in self.rendered if path.startswith("commands/")}
        projects = {path for path in self.generated if path.startswith("commands/")}
        self.assertEqual(projects - plugins, set())

    def test_it_ships_every_skill_the_project_has_that_needs_no_language(self) -> None:
        """A project prunes the catalogue against what it can do; a plugin has nothing to prune against and
        ships all of it. So the project's set is inside the plugin's, never the other way round."""
        theirs = {skill_of(path) for path in self.generated if path.startswith("skills/")}
        ours = {skill_of(path) for path in self.rendered if path.startswith("skills/")}
        needs_a_language = plugin.languages_own(plugin.sources("standard"))
        # `run-the-app` is written per project — it names that project's own applications.
        self.assertEqual(theirs - ours - needs_a_language - {"run-the-app"}, set())

    def test_nothing_is_rendered_that_a_generated_project_has_not_got(self) -> None:
        """Bar the skills a project pruned away, which a plugin cannot know it would have."""
        own = {plugin.MANIFEST, plugin.HOOKS}
        theirs = {skill_of(path) for path in self.generated if path.startswith("skills/")}
        for path in self.rendered:
            if path in own or (path.startswith("skills/") and skill_of(path) not in theirs):
                continue
            self.assertIn(path, self.generated, f"{path} is in the plugin and in no generated project")


class HooksTest(unittest.TestCase):
    """`hooks/hooks.json`: the same points and the same verbs as `.claude/settings.json`, guarded."""

    def hooks(self) -> dict:
        return json.loads(plugin.files()[plugin.HOOKS])["hooks"]

    def test_every_point_the_settings_file_declares_is_declared_here(self) -> None:
        self.assertEqual(sorted(self.hooks()), sorted(harness_hooks(AT_ROOT)))

    def test_every_verb_the_settings_file_fires_is_fired_here(self) -> None:
        """The verbs are the closed set `session.py` answers; a plugin that fired a different one would be
        a second control plane rather than the same one reached another way."""
        self.assertEqual(plugin.verbs(self.hooks()), plugin.verbs(harness_hooks(AT_ROOT)))

    def test_a_hook_whose_script_is_not_there_does_nothing_rather_than_failing(self) -> None:
        """A plugin is installed once and used in every directory, most of which are not projects. A hook
        naming `scripts/agents/session.py` where there is no project would fail on every tool call, for
        ever, in all of them — so the command runs the script only where it exists, and the script's own
        exit code (2 refuses the call) is what the harness sees where it does."""
        for rows in self.hooks().values():
            for row in rows:
                for hook in row["hooks"]:
                    self.assertIn(plugin.GUARD, hook["command"], hook["command"])
                    self.assertTrue(hook["command"].endswith(tuple(plugin.verbs(self.hooks()))))


class WrittenTest(unittest.TestCase):
    """What `slipwai package plugin` leaves on disk."""

    def test_it_writes_every_rendered_file_under_the_directory_it_was_given(self) -> None:
        into = Path(tempfile.mkdtemp()) / "slipwai-plugin"
        written = plugin.write(into, "standard")
        self.assertEqual(sorted(written), sorted(plugin.files("standard")))
        self.assertTrue((into / plugin.MANIFEST).is_file())
        self.assertEqual((into / "commands/sail.md").read_text(encoding="utf-8"),
                         plugin.files("standard")["commands/sail.md"])


class VerbTest(unittest.TestCase):
    """`slipwai package plugin <directory>`: the fourth thing the publisher's verb does."""

    def test_the_verb_renders_the_plugin_and_says_what_it_wrote(self) -> None:
        into = Path(tempfile.mkdtemp()) / "slipwai-plugin"
        said = io.StringIO()
        with contextlib.redirect_stdout(said):
            package_main(["plugin", str(into)])
        self.assertTrue((into / plugin.MANIFEST).is_file())
        self.assertIn(plugin.MANIFEST, said.getvalue())
        self.assertIn("commands/sail.md", said.getvalue())

    def test_a_profile_the_catalogue_has_not_got_is_a_refusal_rather_than_a_traceback(self) -> None:
        """And it names the profiles there are: a refusal that does not say what to type costs a search."""
        into = Path(tempfile.mkdtemp()) / "slipwai-plugin"
        said = io.StringIO()
        with contextlib.redirect_stderr(said), self.assertRaises(SystemExit):
            package_main(["plugin", str(into), "--profile", "event-modeling"])
        self.assertIn("event-modelling", said.getvalue())
        self.assertFalse(into.exists())

    def test_plugin_is_one_of_the_verbs_the_help_lists(self) -> None:
        self.assertIn("plugin", VERBS)


if __name__ == "__main__":
    unittest.main()
