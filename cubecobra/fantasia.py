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

Fantasia's mainboard is emptied — during design phase everything lives in
the maybeboard. The gathering cube is left untouched (delete it later via
gaelaria.py-style cleanup once you're confident in the merge).

Dry-run by default. Pass --apply to execute.
"""

import argparse
from collections import Counter

from cc import CubeCobra, clean_card, name_key

FANTASIA = "fantasia"
GATHERING_CUBE = "8661cb7a-fa8d-4a4e-bc33-9dab818fd1d7"  # "jacklionheart's New Cube"
PICKED_TAG = "✨ Picked"
INSPIRATION = [
    ("GUT", "⚛️ GUT"),
    ("sacred-geometry", "📐 Sacred"),
    ("0efda005-7243-457e-9d11-875e37d1b768", "👑 LOL"),  # Lords of Limited
]


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

    changes = {}
    if current_main:
        changes["mainboard"] = {
            "removes": [
                {"index": i, "oldCard": clean_card(c)}
                for i, c in reversed(list(enumerate(current_main)))
            ]
        }
    maybe_changes = {}
    current_maybe_names = {name_key(c) for c in current_maybe}
    stale = [
        {"index": i, "oldCard": clean_card(c)}
        for i, c in reversed(list(enumerate(current_maybe)))
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
