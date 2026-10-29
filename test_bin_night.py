"""Tests for Bin Night Montreal — the date logic is the whole product,
so it gets tested harder than the CLI printing."""

import unittest
from datetime import date

from bin_night import (
    load_sectors,
    next_pickup,
    pickups_on,
    tonight_streams,
)


class TestWeeklyAndBiweekly(unittest.TestCase):
    def test_weekly_next_includes_today(self):
        # 2026-10-29 is a Thursday.
        self.assertEqual(
            next_pickup({"type": "weekly", "weekday": 3}, date(2026, 10, 29)),
            date(2026, 10, 29),
        )

    def test_weekly_next_skips_to_next_week(self):
        self.assertEqual(
            next_pickup({"type": "weekly", "weekday": 3}, date(2026, 10, 30)),
            date(2026, 11, 5),
        )

    def test_biweekly_anchor_week(self):
        # Anchor Monday 2026-01-05; 2026-01-19 is also a pickup Monday.
        rule = {"type": "biweekly", "weekday": 0, "anchor": "2026-01-05"}
        self.assertEqual(next_pickup(rule, date(2026, 1, 19)), date(2026, 1, 19))

    def test_biweekly_off_week_skips(self):
        rule = {"type": "biweekly", "weekday": 0, "anchor": "2026-01-05"}
        self.assertEqual(next_pickup(rule, date(2026, 1, 12)), date(2026, 1, 19))


class TestNthWeekdayAndSeasonal(unittest.TestCase):
    def test_bulky_second_and_fourth_wednesday(self):
        rule = {"type": "nth_weekday", "weekday": 2, "nths": [2, 4]}
        # November 2026: Wednesdays are 4, 11, 18, 25 → 2nd is 11th, 4th is 25th.
        self.assertEqual(next_pickup(rule, date(2026, 11, 1)), date(2026, 11, 11))
        self.assertEqual(next_pickup(rule, date(2026, 11, 12)), date(2026, 11, 25))

    def test_seasonal_in_season(self):
        rule = {"type": "seasonal", "weekday": 2, "start": "04-15", "end": "12-02"}
        self.assertEqual(next_pickup(rule, date(2026, 6, 1)), date(2026, 6, 3))

    def test_seasonal_out_of_season_returns_none(self):
        rule = {"type": "seasonal", "weekday": 2, "start": "04-15", "end": "12-02"}
        self.assertIsNone(next_pickup(rule, date(2026, 12, 10)))

    def test_christmas_trees_january_only(self):
        rule = {"type": "january_wednesdays", "weekday": 2}
        # Jan 10, 2027 is a Sunday; the next Wednesday is Jan 13.
        self.assertEqual(next_pickup(rule, date(2027, 1, 10)), date(2027, 1, 13))
        # After January, it jumps to next January, not to February.
        self.assertEqual(next_pickup(rule, date(2027, 1, 28)), date(2028, 1, 5))


class TestSectorIntegration(unittest.TestCase):
    def setUp(self):
        self.sectors = load_sectors()

    def test_sample_sectors_load(self):
        self.assertIn("plateau-sample", self.sectors)
        self.assertIn("longueuil-sample", self.sectors)

    def test_tonight_is_tomorrows_pickup(self):
        # 2026-10-28 is a Wednesday, so tomorrow (Thursday) is garbage +
        # recycling day in plateau-sample. Tonight you put those out.
        sector = self.sectors["plateau-sample"]
        self.assertEqual(
            sorted(tonight_streams(sector, date(2026, 10, 28))),
            ["garbage", "recycling"],
        )

    def test_pickups_on_bulky_day(self):
        # Wednesday 2026-11-11 is 2nd Wednesday → bulky + green waste.
        sector = self.sectors["plateau-sample"]
        streams = pickups_on(sector, date(2026, 11, 11))
        self.assertIn("bulky items", streams)
        self.assertIn("green waste", streams)


if __name__ == "__main__":
    unittest.main()
