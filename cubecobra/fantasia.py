#!/usr/bin/env python3
"""Rebuild Fantasia's maybeboard as the design-phase card pool.

The maybeboard becomes the union (deduped by card name) of:
  - everything currently in Fantasia itself (both boards)
  - everything in the second gathering cube ("jacklionheart's New Cube")
  - the mainboards of three inspiration cubes: GUT, Sacred Geometry,
    and Lords of Limited

Cards are tagged by provenance (tags union when a card has several sources):
  ✨ Picked   — hand-gathered in either of Jack's two gathering cubes
  ⚛️ GUT     — in the GUT cube
  📐 Sacred  — in Sacred Geometry
  👑 LOL     — in Lords of Limited
  🔥 Banger  — 17lands overperformer for its rarity (17lands/out/bangers_all.csv)

Fantasia's mainboard is emptied — during design phase everything lives in
the maybeboard. The gathering cube is left untouched (delete it later via
gaelaria.py-style cleanup once you're confident in the merge).

Dry-run by default. Pass --apply to execute.
"""

import argparse
import csv
import pathlib
from collections import Counter

from cc import CubeCobra, clean_card, name_key, remove_entry, validate_indexes

FANTASIA = "fantasia"
GATHERING_CUBE = "8661cb7a-fa8d-4a4e-bc33-9dab818fd1d7"  # "jacklionheart's New Cube"
PICKED_TAG = "✨ Picked"
INSPIRATION = [
    ("GUT", "⚛️ GUT"),
    ("sacred-geometry", "📐 Sacred"),
    ("0efda005-7243-457e-9d11-875e37d1b768", "👑 LOL"),  # Lords of Limited
]
BANGER_TAG = "🔥 Banger"
BANGERS_CSV = pathlib.Path(__file__).resolve().parent.parent / "17lands" / "out" / "bangers_all.csv"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="actually push the rebuild")
    args = parser.parse_args()

    cc = CubeCobra()

    fantasia = cc.cube_json(FANTASIA)
    gathering = cc.cube_json(GATHERING_CUBE)

    # name -> card template; first writer wins on printing, so own picks
    # keep their chosen printings over inspiration-cube versions.
    pool = {}
    tags = {}  # name -> set of provenance tags

    def absorb(cards, tag):
        for card in cards:
            k = name_key(card)
            if k not in pool:
                template = clean_card(card)
                # provenance tags replace source-cube tags, which mean
                # nothing outside their home cube
                template["tags"] = []
                pool[k] = template
                tags[k] = set()
            tags[k].add(tag)

    for cube in (fantasia, gathering):
        absorb(cube["cards"]["mainboard"] + cube["cards"].get("maybeboard", []), PICKED_TAG)

    for cube_id, tag in INSPIRATION:
        insp = cc.cube_json(cube_id)
        absorb(insp["cards"]["mainboard"], tag)
        print(f"absorbed {insp['name']}: {len(insp['cards']['mainboard'])} cards")

    # --- 17lands bangers -------------------------------------------------
    with open(BANGERS_CSV) as f:
        banger_names = sorted({row["Name"] for row in csv.DictReader(f)})
    already = [n for n in banger_names if n.lower() in pool]
    for n in already:
        tags[n.lower()].add(BANGER_TAG)
    missing = [n for n in banger_names if n.lower() not in pool]
    resolved = cc.resolve_cards(missing)
    unresolved = [n for n in missing if not resolved.get(n.lower())]
    new_cards = [
        {"cardID": d["scryfall_id"], "name": d["name"],
         "status": "Not Owned", "finish": "Non-foil"}
        for n in missing
        if (d := resolved.get(n.lower()))
    ]
    absorb(new_cards, BANGER_TAG)
    print(f"absorbed bangers: {len(banger_names)} total, {len(already)} already in pool, "
          f"{len(new_cards)} new")
    if unresolved:
        print(f"WARNING: {len(unresolved)} banger names not found on Cube Cobra: "
              f"{', '.join(unresolved[:10])}{'…' if len(unresolved) > 10 else ''}")

    for k, template in pool.items():
        template["tags"] = sorted(tags[k])

    desired = list(pool.values())
    combo_counts = Counter(tuple(c["tags"]) for c in desired)
    print(f"\nDesired maybeboard: {len(desired)} unique cards")
    for combo, n in combo_counts.most_common():
        print(f"  {n:4d}  {' + '.join(combo)}")

    current_main = fantasia["cards"]["mainboard"]
    current_maybe = fantasia["cards"].get("maybeboard", [])
    print(f"\nFantasia now: {len(current_main)} mainboard, {len(current_maybe)} maybeboard")
    print(f"After: 0 mainboard, {len(desired)} maybeboard")

    if not args.apply:
        print("\nDry run — nothing changed. Re-run with --apply to execute.")
        return

    cc.login()

    validate_indexes(current_main, "mainboard")
    validate_indexes(current_maybe, "maybeboard")
    changes = {}
    if current_main:
        changes["mainboard"] = {
            "removes": [remove_entry(c) for c in sorted(current_main, key=lambda c: -c["index"])]
        }
    maybe_changes = {}
    current_maybe_names = {name_key(c) for c in current_maybe}
    stale = [
        remove_entry(c)
        for c in sorted(current_maybe, key=lambda c: -c["index"])
        if name_key(c) not in pool
    ]
    if stale:
        maybe_changes["removes"] = stale
    new_cards = [c for k, c in pool.items() if k not in current_maybe_names]
    if new_cards:
        maybe_changes["adds"] = new_cards
    if maybe_changes:
        changes["maybeboard"] = maybe_changes

    if not changes:
        print("Nothing to do — already in desired state.")
        return

    result = cc.commit(fantasia["id"], changes, fantasia.get("version", 0),
                       title="Rebuild maybeboard as design pool")
    print(f"committed, new version {result.get('version')}")


if __name__ == "__main__":
    main()
