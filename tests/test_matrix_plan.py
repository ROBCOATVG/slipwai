"""What the matrix reads back from its probe's plan: at most one production image per backend, and none is a plan.

`matrix/plan.py` plans no image where no managed target is installed — there is nothing to deploy one to — and
the reader refused that plan as malformed, so every package CI that installs no target ended its tag run on
`backend go has no image, or more than one` before a row was generated.
"""
from __future__ import annotations

import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.matrix.run import validated

ROW = {"name": "verify-go", "profile": "standard", "backend": "go", "frontend": "none", "answers": []}
IMAGE = {"row": ROW, "tool": "ko", "ready": "/ready"}


def plan(images: list) -> dict:
    return {"backends": ["go"], "rows": [ROW], "images": images}


class PlanReadTest(unittest.TestCase):
    def test_no_managed_target_is_no_image_and_still_a_plan(self) -> None:
        self.assertEqual(validated("go", Path("."), plan([])).images, ())

    def test_one_image_is_read(self) -> None:
        self.assertEqual(len(validated("go", Path("."), plan([IMAGE])).images), 1)

    def test_two_images_for_one_backend_are_refused(self) -> None:
        with self.assertRaises(RuntimeError) as raised:
            validated("go", Path("."), plan([IMAGE, IMAGE]))
        self.assertIn("more than one image", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
