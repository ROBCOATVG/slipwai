"""The drawn figures in `docs/images/`, held to the two things a reader cannot check for themselves.

**The pair is one drawing.** `spec-to-delegate-event-modelling.svg` and `spec-to-delegate-standard.svg`
answer slice 9.6, whose whole claim is that the two profiles are the same figure with *two boxes*
different — so a reader comparing them sees the difference rather than hunting for it. Drawn by hand, that
is a claim that decays on the first edit to one of them: a word fixed in one figure and not the other
leaves a pair that differ in three places and say so nowhere. Here it is arithmetic.

**Every word sits on something filled.** None of these figures declares a background: GitHub renders them
on a white page in the light theme and a near-black one in the dark theme, and dark text on a transparent
background disappears in the second. What the existing figures do about it is put every band, box and bar
down as an opaque light fill and keep the text inside one — so this holds the new pair to that, which is
the one colour rule a figure in this repository has to follow.
"""
from __future__ import annotations

import re
import unittest
import xml.etree.ElementTree as ElementTree
from pathlib import Path

IMAGES = Path(__file__).resolve().parents[1] / "docs/images"
SVG = "{http://www.w3.org/2000/svg}"
PAIR = ("spec-to-delegate-event-modelling.svg", "spec-to-delegate-standard.svg")
#: The two boxes slice 9.6 lets the profiles disagree in: what the feature is typed in, and where the
#: example map's examples come from. Named by their headings, which are the lines a reader compares.
DIFFER = {"Event model", "Chart", "Example map"}
#: 12px of the figures' font stack averages a shade over 6 per character. Generous rather than exact: what
#: is being caught is a line somebody lengthened past its box, not a kerning difference.
PER_CHAR = 6.2


def lines(name: str) -> list[str]:
    return (IMAGES / name).read_text(encoding="utf-8").splitlines()


def rectangles(root: ElementTree.Element) -> list[tuple[float, float, float, float]]:
    return [(float(one.get("x", 0)), float(one.get("y", 0)),
             float(one.get("width", 0)), float(one.get("height", 0)))
            for one in root.iter(f"{SVG}rect")]


class FigureTest(unittest.TestCase):
    def test_every_figure_is_well_formed_and_says_what_it_shows(self) -> None:
        """A figure with no `aria-label` is one a screen reader reads as nothing at all."""
        for path in sorted(IMAGES.glob("*.svg")):
            with self.subTest(figure=path.name):
                root = ElementTree.fromstring(path.read_text(encoding="utf-8"))
                self.assertTrue(root.get("viewBox"), f"{path.name} has no viewBox, so it cannot scale")
                self.assertGreater(len(root.get("aria-label") or ""), 40, "say what the figure shows")

    def test_the_two_profiles_are_one_drawing(self) -> None:
        """Same line for same line, bar the label that names the profile and the two boxes' own words."""
        left, right = (lines(name) for name in PAIR)
        self.assertEqual(len(left), len(right), "the two figures are not the same drawing")
        differing = [index for index, (a, b) in enumerate(zip(left, right, strict=True)) if a != b]
        self.assertIn(0, differing, "the aria-label has to name which profile this is")
        texts = [re.findall(r">([^<]*)<", left[index]) + re.findall(r">([^<]*)<", right[index])
                 for index in differing if index]
        self.assertTrue(texts, "the two profiles differ nowhere, so one of the two boxes was lost")
        for found in texts:
            self.assertTrue([one for one in found if one.strip()],
                            "the figures differ in a shape rather than in a box's words")

    def test_the_two_profiles_differ_in_exactly_two_boxes(self) -> None:
        """Counted by which box each differing word is *inside*, found from the geometry.

        Not by reading down the file: the word that differs has to be in the same shape as the heading
        above it, and an ordering test passes a word changed three boxes further along.
        """
        read = [ElementTree.fromstring((IMAGES / name).read_text(encoding="utf-8")) for name in PAIR]
        shapes = [rectangles(root) for root in read]
        self.assertEqual(shapes[0], shapes[1], "the two figures are not drawn on one geometry")
        texts = [list(root.iter(f"{SVG}text")) for root in read]
        self.assertEqual(len(texts[0]), len(texts[1]), "the two figures do not carry the same words")
        changed = set()
        for left, right in zip(*texts, strict=True):
            if (left.text or "") == (right.text or ""):
                continue
            inside = [index for index, (x, y, w, h) in enumerate(shapes[0])
                      if x <= float(left.get("x", 0)) <= x + w and y <= float(left.get("y", 0)) <= y + h]
            self.assertTrue(inside, f"a word differs outside every box: {left.text!r}")
            # The smallest shape holding it: every box sits inside a band, and the band is not the box.
            changed.add(min(inside, key=lambda index: shapes[0][index][2] * shapes[0][index][3]))
        self.assertEqual(len(changed), 2, "exactly two boxes may differ between the profiles")
        headings = {(one.text or "") for one in texts[0] + texts[1] if (one.text or "") in DIFFER}
        self.assertEqual(headings, DIFFER, "the two boxes that differ are not the two 9.6 names")

    def test_no_word_in_the_new_pair_sits_on_the_page_itself(self) -> None:
        """Dark theme: a word outside every filled shape is dark text on a near-black background."""
        for name in PAIR:
            root = ElementTree.fromstring((IMAGES / name).read_text(encoding="utf-8"))
            filled = rectangles(root)
            for one in root.iter(f"{SVG}text"):
                text = (one.text or "").strip()
                if not text:
                    continue
                size = float(one.get("font-size", "12"))
                width = len(text) * size * 0.52
                anchor = one.get("text-anchor", "start")
                x = float(one.get("x", 0))
                start = x if anchor == "start" else (x - width / 2 if anchor == "middle" else x - width)
                top, bottom = float(one.get("y", 0)) - size * 0.8, float(one.get("y", 0)) + size * 0.25
                with self.subTest(figure=name, text=text[:40]):
                    self.assertTrue(
                        any(rx <= start and start + width <= rx + rw and ry <= top and bottom <= ry + rh
                            for rx, ry, rw, rh in filled),
                        "this line is not inside any filled shape, so it vanishes in the dark theme",
                    )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
