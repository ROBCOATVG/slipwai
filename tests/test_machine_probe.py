"""The machine's tools are asked off the request, once, kept, and bounded — and no board under test asks one.

Nothing here waits on a clock. A tool that is slow is a stand-in waiting on an event the test sets; time is
a number the test moves; and whether an asking was started is counted where it is started, on the thread
that read, rather than where it lands.
"""
from __future__ import annotations

import re
import tempfile
import threading
import unittest
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest import mock

import checkout_packages
from board_fixture import served

from slipwai import machine_card, machine_probe
from slipwai.bridge import serve
from slipwai.machine_probe import BOUND, CHECKING, KEEP, RETRY, UNANSWERED, Machine
from slipwai.prerequisites import TOOLS, Found, Tool


def has(tool: Tool) -> Found:
    return Found(tool, "found", f"/described/{tool.command}", "1.2.3")


class Held:
    """A machine a test describes: the time, which askings have been started, and when each is let answer."""

    def __init__(self, look: Callable[[Tool], Found] = has, slow: tuple[str, ...] = ()) -> None:
        self.now, self.slow = 0.0, slow
        self.started: list[str] = []
        self.waiting: dict[str, Callable[[], None]] = {}
        self.machine = Machine(look, lambda: self.now, self.start)

    def start(self, work: Any) -> None:
        key = work.args[0].key  # an asking is a `partial` of `Machine.ask`, and its tool comes first
        self.started.append(key)
        if key in self.slow:
            self.waiting[key] = work
        else:
            work()

    def states(self) -> dict[str, str]:
        return {one.tool.key: one.state for one in self.machine.read()}


class ReadingTest(unittest.TestCase):
    def test_a_read_answers_with_a_tool_still_out_and_a_second_read_asks_nothing_again(self) -> None:
        held = Held(slow=("git",))
        first = held.states()
        self.assertEqual(first["git"], CHECKING)
        self.assertEqual({state for key, state in first.items() if key != "git"}, {"found"})
        held.states()
        self.assertEqual(sorted(held.started), sorted(tool.key for tool in TOOLS))
        held.waiting.pop("git")()
        self.assertEqual(held.states()["git"], "found")
        self.assertEqual(len(held.started), len(TOOLS))

    def test_a_good_copy_is_kept_and_asked_again_only_when_that_runs_out(self) -> None:
        held = Held()
        held.states()
        held.now = KEEP - 1
        held.states()
        self.assertEqual(len(held.started), len(TOOLS))
        held.now = KEEP
        held.states()
        self.assertEqual(len(held.started), 2 * len(TOOLS))

    def test_a_tool_the_machine_lacks_is_asked_again_by_the_reload_after_an_install(self) -> None:
        held = Held(lambda tool: Found(tool, "missing") if tool.key == "node" else has(tool))
        self.assertEqual(held.states()["node"], "missing")
        held.now = RETRY - 1
        held.states()
        self.assertEqual(held.started.count("node"), 1)
        held.now = RETRY
        held.states()
        self.assertEqual(held.started.count("node"), 2)
        self.assertEqual(held.started.count("git"), 1)

    def test_a_tool_that_does_not_answer_is_unanswered_at_its_bound_and_holds_no_other(self) -> None:
        held = Held(slow=("git",))
        held.states()
        held.now = BOUND - 0.5
        self.assertEqual(held.states()["git"], CHECKING)
        held.now = BOUND
        said = held.states()
        self.assertEqual(said["git"], UNANSWERED)
        self.assertEqual(said["make"], "found")
        # What it says after the bound is `found` giving up, which it reports as missing: not taken.
        held.now = BOUND + 6
        held.waiting.pop("git")()
        self.assertNotIn("git", held.machine.kept)
        # Its thread is back, so the next read asks it again — it alone, the others' answers still good.
        held.states()
        self.assertEqual(held.started.count("git"), 2)
        self.assertEqual(len(held.started), len(TOOLS) + 1)

    def test_an_asking_that_faults_is_not_out_for_ever(self) -> None:
        def faulty(tool: Tool) -> Found:
            raise OSError("no such shell")

        machine = Machine(faulty, lambda: 0.0, lambda work: self.assertRaises(OSError, work))
        self.assertEqual({one.state for one in machine.read()}, {CHECKING})
        self.assertEqual(machine.out, 0)

    def test_the_board_installing_a_tool_drops_what_was_known_of_it(self) -> None:
        held = Held()
        held.states()
        held.machine.forget("node")
        held.states()
        self.assertEqual(held.started.count("node"), 2)

    def test_real_threads_are_single_flight_too(self) -> None:
        """The same, with the threads a board uses: every tool waits on one event, so the readers below
        are all answered while every asking is out, and the count is of askings started."""
        release, counted = threading.Event(), threading.Lock()
        asked: list[str] = []
        threads: list[threading.Thread] = []

        def blocked(tool: Tool) -> Found:
            release.wait()
            return has(tool)

        def start(work: Callable[[], None]) -> None:
            with counted:
                asked.append("")
            threads.append(threading.Thread(target=work, daemon=True))
            threads[-1].start()

        machine = Machine(blocked, start=start)
        readers = [threading.Thread(target=machine.read) for _ in range(8)]
        for reader in readers:
            reader.start()
        for reader in readers:
            reader.join()
        self.assertEqual(len(asked), len(TOOLS))
        release.set()
        for thread in threads:
            thread.join()
        self.assertEqual({one.state for one in machine.read()}, {"found"})


def missing_node(tool: Tool) -> Found:
    return Found(tool, "missing") if tool.key == "node" else has(tool)


class LineTest(unittest.TestCase):
    """What a start page and the card say of a machine at each point: asked, answered, and not answered."""

    def described(self, held: Held) -> None:
        patched = mock.patch.object(machine_probe, "MACHINE", held.machine)
        patched.start()
        self.addCleanup(patched.stop)

    def test_while_a_tool_is_out_the_line_says_so_names_its_poll_and_offers_a_reload(self) -> None:
        self.described(Held(slow=("git", "make")))
        line = machine_card.lacking_line("/generate", {"language": "go", "profile": "plain"}, inline=True)
        self.assertIn("Checking what this machine has of Git, Make", line)
        self.assertIn('<a href="">Reload</a>', line)  # true with no script at all: the page says where it is
        self.assertIn('data-lacking="/settings/lacking.html?route=%2Fgenerate&amp;language=go&amp;'
                      'profile=plain&amp;inline=1"', line)
        card = machine_card.card()
        self.assertIn("data-machine", card)
        self.assertIn("asking it for its version", card)
        self.assertIn(f"1.2.3 at /described/{TOOLS[2].command}", card)  # the others are not held

    def test_once_every_tool_has_answered_the_words_are_the_ones_they_always_were(self) -> None:
        self.described(Held(missing_node))
        for route, inline in (("/generate", True), ("/adopt", False), ("/generate", False)):
            self.assertEqual(machine_card.lacking_line(route, inline=inline),
                             machine_card.lacking_line(route, look=missing_node, inline=inline))
        self.assertIn("Node (not installed)", machine_card.lacking_line("/generate"))
        self.assertEqual(machine_card.lacking_line("/adopt"), "")
        self.assertNotIn("data-machine", machine_card.card())
        with mock.patch.object(machine_card, "last_row", return_value=""):
            self.assertEqual(machine_card.card(), machine_card.card([missing_node(tool) for tool in TOOLS]))

    def test_a_tool_that_never_answers_is_said_to_be_unanswered_and_is_not_called_missing(self) -> None:
        held = Held(slow=("git",))
        self.described(held)
        machine_card.lacking_line("/adopt")
        held.now = BOUND
        line = machine_card.lacking_line("/adopt")
        self.assertIn("Git did not answer within 15 seconds", line)
        self.assertIn('<a href="">Reload</a>', line)
        self.assertNotIn("needs something first", line)
        self.assertNotIn("data-lacking", line)  # settled: the poll stops, and a reload asks again
        card = machine_card.card()
        self.assertIn("did not answer within 15 seconds", card)
        self.assertNotIn('data-tool="git"', card)  # nothing is offered for a tool nobody has heard from
        self.assertNotIn("data-machine", card)


class ServedTest(unittest.TestCase):
    """Over a board: the start pages are sent while every tool is still out, and fill in once they answer."""

    def setUp(self) -> None:
        self.release = threading.Event()
        self.asked: list[Any] = []
        self.threads: list[threading.Thread] = []
        self.addCleanup(self.release.set)

        def blocked(tool: Tool) -> Found:
            self.release.wait()
            return missing_node(tool)

        def start(work: Callable[[], None]) -> None:
            self.asked.append(work)
            self.threads.append(threading.Thread(target=work, daemon=True))
            self.threads[-1].start()

        patched = mock.patch.object(machine_probe, "MACHINE", Machine(blocked, start=start))
        patched.start()
        self.addCleanup(patched.stop)
        self.port = served(self, Path(tempfile.mkdtemp())).server_address[1]

    def get(self, path: str) -> str:
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=60) as answer:
            return answer.read().decode("utf-8")

    def test_the_pages_answer_before_any_tool_does_and_ask_each_tool_once(self) -> None:
        generate, adopt = self.get("/generate?seat=one"), self.get("/adopt?seat=one")
        for page in (generate, adopt):
            self.assertIn("Checking what this machine has of Git, Make, Python", page)
            self.assertIn("document.querySelector('[data-lacking]')", page)
        self.assertIn('data-lacking="/settings/lacking.html?route=%2Fadopt"', adopt)
        self.assertIn("data-machine", self.get("/settings/machine.html"))
        self.assertIn("Checking", self.get("/settings/lacking.html?route=%2Fgenerate&inline=1"))
        self.assertEqual(len(self.asked), len(TOOLS))  # five requests, one asking of each tool
        self.release.set()
        for thread in self.threads:
            thread.join()
        self.assertEqual(self.get("/settings/lacking.html?route=%2Fadopt"), "")
        self.assertEqual(self.get("/settings/lacking.html?route=%2Fgenerate&inline=1"),
                         machine_card.lacking_line("/generate", look=missing_node, inline=True))
        self.assertIn("Node (not installed)", self.get("/generate?seat=one"))
        self.assertNotIn("data-lacking=", self.get("/adopt?seat=one"))
        self.assertEqual(len(self.asked), len(TOOLS))


class NoMachineTest(unittest.TestCase):
    """No board a suite starts asks this machine for anything, whichever fixture started it."""

    def test_a_board_started_with_no_fixture_at_all_is_answered_by_the_stand_in(self) -> None:
        self.assertIs(machine_probe.MACHINE.look, checkout_packages.equipped,
                      "a suite left its own machine in place of the stand-in: patch it for the test alone")
        server = serve(Path(tempfile.mkdtemp()), "127.0.0.1", 0)
        serving = threading.Thread(target=server.serve_forever, daemon=True)
        serving.start()
        self.addCleanup(server.server_close)
        self.addCleanup(serving.join)
        self.addCleanup(server.shutdown)
        with mock.patch.object(machine_probe, "found", side_effect=AssertionError("the real machine")) as real:
            pages = {}
            for path in ("/generate?seat=one", "/adopt?seat=one", "/settings/machine.html",
                         "/settings/lacking.html?route=%2Fadopt"):
                with urllib.request.urlopen(f"http://127.0.0.1:{server.server_address[1]}{path}",
                                            timeout=60) as answer:
                    pages[path] = answer.read().decode("utf-8")
        real.assert_not_called()
        self.assertIn(f"0.0.0 at {checkout_packages.NO_MACHINE}/git", pages["/settings/machine.html"])
        self.assertNotIn("data-lacking=", pages["/generate?seat=one"] + pages["/adopt?seat=one"])

    def test_every_suite_that_can_start_a_board_imports_the_stand_in(self) -> None:
        """The stand-in is `checkout_packages`' own, put there as that module is imported; a suite that can
        start a board and does not import it would, run on its own, ask this machine."""
        starts = re.compile(r"slipwai\.bridge\b|\bcli_bridge\b|\bcli_start\b|\bbridge\b.*\bserve\b")
        imports = re.compile(r"^(?:import checkout_packages|from (?:board|intake)_fixture import)", re.MULTILINE)
        forgot = [path.name for path in sorted(Path(__file__).parent.glob("*.py"))
                  if starts.search(text := path.read_text(encoding="utf-8")) and not imports.search(text)]
        self.assertEqual(forgot, [], "start each with `import checkout_packages  # noqa: F401`")


if __name__ == "__main__":
    unittest.main()
