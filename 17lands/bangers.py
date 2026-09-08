#!/usr/bin/env python3
"""List 17Lands bangers for one or more sets.

A banger overperforms for its rarity (grades per the 17Lands normal-curve
method, GIH WR) for BOTH the full population and top players:
common >= B, uncommon >= B+, rare >= A, mythic >= A+.

Usage: python3 bangers.py FIN TLA ... [--csv out.csv]
"""

import argparse
import csv
import sys

from lib17.bangers import bangers


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sets", nargs="+", help="set codes, e.g. FIN TLA SOS")
    parser.add_argument("--min-games-all", type=int, default=500)
    parser.add_argument("--min-games-top", type=int, default=100)
    parser.add_argument("--csv", help="also write results to this CSV path")
    args = parser.parse_args()

    rows = []
    for code in args.sets:
        found = bangers(code,
                        min_games_all=args.min_games_all,
                        min_games_top=args.min_games_top)
        rows.extend(found)
        print(f"\n=== {code}: {len(found)} bangers ===")
        for r in found:
            top_grade = r["grade_top"] or "—"
            top_wr = f"{r['gih_wr_top']:.1%}" if r["gih_wr_top"] is not None else "—"
            print(f"  {r['rarity']:8s} {top_grade:2s} (top) / {r['grade_all']:2s} (all)  "
                  f"{top_wr} / {r['gih_wr_all']:.1%}  {r['name']}")

    if args.csv and rows:
        with open(args.csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print(f"\nwrote {len(rows)} rows to {args.csv}", file=sys.stderr)


if __name__ == "__main__":
    main()
