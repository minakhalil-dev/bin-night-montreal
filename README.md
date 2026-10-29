# Bin Night Montreal — quel bac ce soir?

A tiny, offline CLI that answers Montreal's most recurring question:
what bin goes out tonight?

```bash
python bin_night.py tonight --sector plateau-sample
# Put out tonight: garbage, recycling.
```

No API key, no scraping, no account. Python standard library only.

## Disclaimer

This project is for information and learning only. It is not an
official collection schedule and it is not affiliated with or
endorsed by the City of Montreal, the City of Longueuil, or any
collection service. The sample sectors are examples, not official
schedules for any real address — verify your address on montreal.ca
or longueuil.quebec / 311 before relying on it, and use the project
at your own risk. The full text is in [DISCLAIMER.md](DISCLAIMER.md),
and the software is provided "AS IS" under the MIT LICENSE.

## Quickstart (3 commands)

```bash
python bin_night.py tonight --sector plateau-sample
python bin_night.py next --sector plateau-sample
python bin_night.py calendar --sector plateau-sample --days 14
```

Add `--date 2026-10-28` to any command to check a different day.

## How it works

You pick a sector from `data/sectors.json` and the tool computes pickups
from simple rules:

- `weekly` — every Thursday, say
- `biweekly` — every other week from an anchor date (garbage in some areas)
- `nth_weekday` — 2nd and 4th Wednesday (the classic bulky-items rule)
- `seasonal` — Wednesdays, April 15 to December 2 (green waste)
- `january_wednesdays` — Christmas trees, Wednesdays in January only

"Tonight" means bins for tomorrow's pickup. Montreal's rule of thumb is
bins out between 7 p.m. the evening before and 7 a.m. on collection day;
each sector in the config carries its own put-out window, because
Longueuil's brown-bin guidance is 8 p.m. to 7 a.m. and the tool should
not pretend one city's rule covers the other.

## Honest limits — read this before trusting it

The sample sectors are **examples in the shape of real rules, not your
official schedule**. Montreal and Longueuil schedules vary by sector and
change for holidays, November biweekly garbage in some areas, and
July/August green-waste exceptions.

To use it for real:
1. Look up your address on montreal.ca (Montreal) or longueuil.quebec / 311 (Longueuil).
2. Copy your real days into a new sector in `data/sectors.json`.
3. Run it. The value here is the date logic and its tests, not a scraped
   official calendar — and the README says so, so nobody mistakes a sample
   for a city service.

## Results (measured, 2026-10-29)

```bash
python -m unittest test_bin_night -v
# Ran 11 tests — OK
```

Sample, plateau-sample, from 2026-10-28 (Wednesday):

```
Tonight (2026-10-28, for pickups 2026-10-29):
Put out tonight: garbage, recycling.
```

The test suite covers the tricky cases on purpose: biweekly anchor
weeks vs. off weeks, 2nd/4th Wednesday bulky pickup, seasonal
green waste returning "not in season" after December 2 instead of
inventing a date, and Christmas trees jumping to next January rather
than February.

## Project structure

```
DISCLAIMER.md         # full disclaimer — read before using
bin_night.py          # date logic + CLI (stdlib only)
data/sectors.json     # sample sectors — replace with your real sector
test_bin_night.py     # 11 tests for the date logic
```

## Add your own sector

Copy `plateau-sample` in `data/sectors.json`, rename the key, and set
your streams. Weekdays are Monday=0 through Sunday=6. Then:

```bash
python bin_night.py tonight --sector my-street --date 2026-11-10
```
