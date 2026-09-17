import unittest

from worker import doubled


class DoubledTest(unittest.TestCase):
    def test_doubles(self) -> None:
        self.assertEqual(doubled(2), 4)
