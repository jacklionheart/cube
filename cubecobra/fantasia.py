#!/usr/bin/env python3
"""Sync Fantasia tags without backfilling its maybeboard.

Normal runs never change board membership. The --import-cube option performs
an explicit one-time mainboard import, so a later manual removal stays removed.
The --undo-additions option reverses additions found between saved snapshots.

Maybeboard cards receive live provenance tags. Mainboard cards keep only the
manual Allies and Enemies tags. The old Picked tag is removed everywhere, and
Fantasia never tags itself.

Dry-run by default. Pass --apply to execute.
"""

import argparse
import json
import pathlib
from collections import Counter

from cc import (
    CubeCobra,
    board_tag_edits,
    clean_card,
    name_key,
    remove_entry,
    tag_edit,
    validate_indexes,
)
from tag_library import FANTASIA_TAG, load_tag_library

FANTASIA = "fantasia"
MAINBOARD_TAGS = frozenset({"🤝 Allies", "⚔️ Enemies"})
BANGERS_CSV = pathlib.Path(__file__).resolve().parent.parent / "17lands" / "out" / "bangers_all.csv"


def mainboard_tag_edits(cards):
    """Keep only the two manually managed role tags on mainboard cards."""
    return [
        edit
        for card in cards
        if (edit := tag_edit(card, MAINBOARD_TAGS.intersection(card.get("tags", []))))
    ]


def maybeboard_tag_edits(cards, tags_by_name):
    """Match derived provenance without redundantly tagging Fantasia itself."""
    return board_tag_edits(cards, tags_by_name, excluded_tags={FANTASIA_TAG})


def added_names_between(before, after):
    """Names present on the later maybeboard but absent from the earlier one."""
    before_names = {
        name_key(card) for card in before["cards"].get("maybeboard", [])
    }
    return {
        name_key(card) for card in after["cards"].get("maybeboard", [])
    } - before_names


def one_time_imports(occupied_names, source_boards, tags_by_name):
    """Build deduped adds from explicitly requested source mainboards."""
    occupied_names = set(occupied_names)
    imports = []
    for cards in source_boards:
        for card in cards:
            key = name_key(card)
            if key in occupied_names:
                continue
            template = clean_card(card)
            template["tags"] = sorted(tags_by_name.get(key, set()) - {FANTASIA_TAG})
            imports.append(template)
            occupied_names.add(key)
    return imports


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="actually push the sync")
    parser.add_argument("--bangers-csv", type=pathlib.Path, default=BANGERS_CSV)
    parser.add_argument(
        "--import-cube",
        action="append",
        default=[],
        metavar="CUBE_ID",
        help="one-time import of a cube's mainboard (repeatable)",
    )
    parser.add_argument(
        "--undo-additions",
        nargs=2,
        type=pathlib.Path,
        metavar=("BEFORE_JSON", "AFTER_JSON"),
        help="remove maybeboard names added between two saved snapshots",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    cc = CubeCobra()
    fantasia = cc.cube_json(FANTASIA)

    cubes = {FANTASIA: fantasia}
    import_cubes = []
    for cube_id in args.import_cube:
        cube = cc.cube_json(cube_id)
        cubes[cube_id] = cube
        import_cubes.append(cube)
    tag_library, _, _ = load_tag_library(cc, args.bangers_csv, cubes=cubes)

    current_main = fantasia["cards"]["mainboard"]
    current_maybe = fantasia["cards"].get("maybeboard", [])

    removal_names = set()
    if args.undo_additions:
        before_path, after_path = args.undo_additions
        before = json.loads(before_path.read_text())
        after = json.loads(after_path.read_text())
        removal_names = added_names_between(before, after)
        print(f"undo manifest: {len(removal_names)} names added between snapshots")

    kept_maybe = [card for card in current_maybe if name_key(card) not in removal_names]
    occupied_names = {name_key(card) for card in current_main + kept_maybe}
    new_cards = one_time_imports(
        occupied_names,
        [cube["cards"].get("mainboard", []) for cube in import_cubes],
        tag_library,
    )
    for cube in import_cubes:
        size = len(cube["cards"].get("mainboard", []))
        print(f"one-time import source: {cube.get('name')} ({size} cards)")

    desired = []
    for card in kept_maybe + new_cards:
        template = clean_card(card)
        template["tags"] = sorted(
            tag_library.get(name_key(card), set()) - {FANTASIA_TAG}
        )
        desired.append(template)

    combo_counts = Counter(tuple(card["tags"]) for card in desired)
    print(f"\nDesired maybeboard: {len(desired)} unique cards")
    for combo, count in combo_counts.most_common():
        print(f"  {count:4d}  {' + '.join(combo)}")

    print(f"\nFantasia now: {len(current_main)} mainboard, {len(current_maybe)} maybeboard")
    print(f"After: {len(current_main)} mainboard, {len(desired)} maybeboard")

    validate_indexes(current_main, "mainboard")
    validate_indexes(current_maybe, "maybeboard")
    changes = {}
    main_edits = mainboard_tag_edits(current_main)
    if main_edits:
        changes["mainboard"] = {"edits": main_edits}
    print(f"  mainboard tag updates: {len(main_edits)}")

    maybe_changes = {}
    stale = [
        remove_entry(card)
        for card in sorted(current_maybe, key=lambda card: -card["index"])
        if name_key(card) in removal_names
    ]
    if stale:
        maybe_changes["removes"] = stale
    if new_cards:
        maybe_changes["adds"] = new_cards
    maybe_edits = maybeboard_tag_edits(kept_maybe, tag_library)
    if maybe_edits:
        maybe_changes["edits"] = maybe_edits
    if maybe_changes:
        changes["maybeboard"] = maybe_changes

    print(
        f"  maybeboard: +{len(new_cards)} / -{len(stale)} / "
        f"{len(maybe_edits)} tag updates"
    )

    if not changes:
        print("Nothing to do — already in desired state.")
        return
    if not args.apply:
        print("\nDry run — nothing changed. Re-run with --apply to execute.")
        return

    cc.login()
    result = cc.commit_batched(
        fantasia["id"],
        changes,
        fantasia.get("version", 0),
        title="Sync Fantasia boards and live tags",
    )
    print(f"committed, new version {result.get('version')}")


if __name__ == "__main__":
    main()
