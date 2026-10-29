#!/usr/bin/env python3
"""
Bin Night Montreal — "quel bac ce soir?"

A tiny, offline CLI that answers the most Montreal question of all:
what bin goes out tonight?

How it works
------------
You pick a sector from ``data/sectors.json`` (or add your own — see README).
Each sector lists its streams with a simple rule:

  - weekly:      {"type": "weekly", "weekday": 3}          # Thursday
  - biweekly:    {"type": "biweekly", "weekday": 0, "anchor": "2026-01-05"}
                 # every other Monday, starting from the anchor Monday
  - nth_weekday: {"type": "nth_weekday", "weekday": 2, "nths": [2, 4]}
                 # 2nd and 4th Wednesday — the classic bulky-items rule
  - seasonal:    {"type": "seasonal", "weekday": 2,
                  "start": "04-15", "end": "12-02"}
                 # Wednesdays, April 15 to December 2 — green waste
  - january_wednesdays: Christmas trees, Wednesdays in January

"Tonight" means: bins for a pickup *tomorrow* go out this evening.
Montreal's rule of thumb is bins out between 7 p.m. the evening before
and 7 a.m. on collection day; Longueuil's brown-bin guidance is similar
(8 p.m. to 7 a.m.). The sector config carries its own ``put_out`` window,
so the tool never pretends one city's rule covers the other.

Honest limits
-------------
This is NOT the city's address lookup. Montreal and Longueuil schedules
vary by sector, and they change (holidays, November biweekly garbage in
some areas, July/August green-waste exceptions). The sample sectors in
``data/sectors.json`` are *examples in the shape of real rules*, not your
official schedule — check montreal.ca / longueuil.quebec for your address,
then copy your real days into a sector of your own. The value here is
the date logic and its tests, not a scraped official calendar.

Usage
-----
    python bin_night.py tonight --sector plateau-sample
    python bin_night.py tonight --sector plateau-sample --date 2026-10-29
    python bin_night.py next --sector longueuil-sample
    python bin_night.py calendar --sector plateau-sample --days 14
    python -m unittest test_bin_night -v
"""

from __future__ import annotations

import argparse
import calendar as calmod
import json
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).parent
SECTORS_PATH = ROOT / "data" / "sectors.json"

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def load_sectors(path: Path = SECTORS_PATH) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["sectors"]


def _parse_date(s: str) -> date:
    y, m, d = (int(x) for x in s.split("-"))
    return date(y, m, d)


def _next_weekday(from_day: date, weekday: int, include_today: bool = False) -> date:
    """Next date with this weekday. ``include_today`` counts today if it matches."""
    delta = (weekday - from_day.weekday()) % 7
    if delta == 0 and not include_today:
        delta = 7
    return from_day + timedelta(days=delta)


def _nth_weekday_of_month(year: int, month: int, weekday: int, n: int) -> date | None:
    """The nth weekday of a month, or None if the month has no such day."""
    month_cal = calmod.monthcalendar(year, month)
    # monthcalendar weeks start Monday; weekday is Monday=0.
    count = 0
    for week in month_cal:
        day = week[weekday]
        if day:
            count += 1
            if count == n:
                return date(year, month, day)
    return None


def next_pickup(rule: dict, from_day: date) -> date | None:
    """Next pickup on or after ``from_day`` for one rule, or None if none soon.

    For seasonal rules, "soon" means within the current season; if the
    season is over, the caller gets None and can say "not in season"
    instead of inventing a date a year away. Christmas trees return the
    next January Wednesday, which may be in the next calendar year.
    """
    kind = rule["type"]
    weekday = rule["weekday"]

    if kind == "weekly":
        return _next_weekday(from_day, weekday, include_today=True)

    if kind == "biweekly":
        anchor = _parse_date(rule["anchor"])
        # Walk forward from the anchor in 14-day steps until >= from_day.
        candidate = anchor
        while candidate < from_day:
            candidate += timedelta(days=14)
        return candidate

    if kind == "nth_weekday":
        for year, month in [(from_day.year, from_day.month),
                            (from_day.year + (from_day.month // 12), from_day.month % 12 + 1)]:
            for n in sorted(rule["nths"]):
                candidate = _nth_weekday_of_month(year, month, weekday, n)
                if candidate and candidate >= from_day:
                    return candidate
        return None

    if kind == "seasonal":
        start_month, start_day = (int(x) for x in rule["start"].split("-"))
        end_month, end_day = (int(x) for x in rule["end"].split("-"))
        season_start = date(from_day.year, start_month, start_day)
        season_end = date(from_day.year, end_month, end_day)
        if from_day > season_end:
            return None
        candidate = _next_weekday(max(from_day, season_start), weekday, include_today=True)
        return candidate if candidate <= season_end else None

    if kind == "january_wednesdays":
        # Next Wednesday on/after from_day, if it is still in January;
        # otherwise the first Wednesday of next January.
        candidate = _next_weekday(from_day, weekday, include_today=True)
        if candidate.month == 1 and candidate.year == from_day.year:
            return candidate
        return _next_weekday(date(from_day.year + 1, 1, 1), weekday, include_today=True)

    raise ValueError(f"Unknown rule type: {kind!r}")


def pickups_on(sector: dict, day: date) -> list[str]:
    """Streams collected on exactly ``day``."""
    out = []
    for stream, rule in sector["streams"].items():
        nxt = next_pickup(rule, day)
        if nxt == day:
            out.append(stream)
    return out


def tonight_streams(sector: dict, today: date) -> list[str]:
    """Streams to put out tonight = pickups tomorrow."""
    return pickups_on(sector, today + timedelta(days=1))


def next_pickups(sector: dict, today: date) -> dict[str, date | None]:
    return {stream: next_pickup(rule, today) for stream, rule in sector["streams"].items()}


def format_stream_list(streams: list[str]) -> str:
    if not streams:
        return "Nothing goes out tonight. Enjoy the evening."
    return "Put out tonight: " + ", ".join(streams) + "."


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bin Night Montreal — quel bac ce soir?")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("tonight", "next", "calendar"):
        p = sub.add_parser(name)
        p.add_argument("--sector", required=True, help="Sector key from data/sectors.json")
        p.add_argument("--date", default=None, help="YYYY-MM-DD (default: today)")
    sub.choices["calendar"].add_argument("--days", type=int, default=14)
    args = parser.parse_args(argv)

    sectors = load_sectors()
    if args.sector not in sectors:
        print(f"Unknown sector: {args.sector!r}. Available: {', '.join(sorted(sectors))}")
        return 2
    sector = sectors[args.sector]
    today = _parse_date(args.date) if args.date else date.today()
    put_out = sector.get("put_out", "7 p.m. the evening before to 7 a.m. on collection day")

    if args.command == "tonight":
        streams = tonight_streams(sector, today)
        print(f"Sector: {args.sector} — {sector.get('city', '')} ({sector.get('note', '')})")
        print(f"Tonight ({today.isoformat()}, for pickups { (today + timedelta(days=1)).isoformat() }):")
        print(format_stream_list(streams))
        print(f"Put bins out between {put_out}.")
        return 0

    if args.command == "next":
        print(f"Sector: {args.sector}")
        for stream, nxt in next_pickups(sector, today).items():
            print(f"  {stream}: {nxt.isoformat() if nxt else 'not in season'} "
                  f"({WEEKDAYS[nxt.weekday()] if nxt else ''})")
        return 0

    # calendar
    print(f"Sector: {args.sector} — next {args.days} days from {today.isoformat()}")
    for i in range(args.days):
        day = today + timedelta(days=i)
        streams = pickups_on(sector, day)
        if streams:
            print(f"  {day.isoformat()} ({WEEKDAYS[day.weekday()]}): {', '.join(streams)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
