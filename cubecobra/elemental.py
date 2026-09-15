#!/usr/bin/env python3
"""Live-sync shared provenance tags onto Elemental's mainboard.

Board membership is never changed and the maybeboard is ignored. Tags are
derived from current tracked-cube and inspiration-cube membership plus the
generated 17Lands banger list.

Dry-run by default. Pass --apply to execute.
"""

import argparse
import pathlib
from collections import Counter

from cc import CubeCobra, board_tag_edits, name_key, validate_indexes
from tag_library import ELEMENTAL_TAG, load_tag_library

ELEMENTAL = "elemental"
BANGERS_CSV = pathlib.Path(__file__).resolve().parent.parent / "17lands" / "out" / "bangers_all.csv"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="actually push the tag sync")
    parser.add_argument("--bangers-csv", type=pathlib.Path, default=BANGERS_CSV)
    args = parser.parse_args()

    cc = CubeCobra()
    elemental = cc.cube_json(ELEMENTAL)
    mainboard = elemental["cards"]["mainboard"]
    validate_indexes(mainboard, "elemental mainboard")
    tag_library, _, _ = load_tag_library(
        cc,
        args.bangers_csv,
        cubes={ELEMENTAL: elemental},
    )

    desired_counts = Counter(
        tag
        for card in mainboard
        for tag in tag_library.get(name_key(card), set()) - {ELEMENTAL_TAG}
    )
    print(f"Elemental mainboard: {len(mainboard)} cards")
    for tag, count in sorted(desired_counts.items()):
        print(f"  {count:4d}  {tag}")

    edits = board_tag_edits(mainboard, tag_library, excluded_tags={ELEMENTAL_TAG})
    print(f"Tag updates: {len(edits)}")
    if not edits:
        print("Nothing to do — already in desired state.")
        return
    if not args.apply:
        print("Dry run — nothing changed. Re-run with --apply to execute.")
        return

    cc.login()
    result = cc.commit_batched(
        elemental["id"],
        {"mainboard": {"edits": edits}},
        elemental.get("version", 0),
        title="Sync Elemental live provenance tags",
    )
    print(f"committed, new version {result.get('version')}")


if __name__ == "__main__":
    main()
