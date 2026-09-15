#!/usr/bin/env python3
"""Gaelaria housekeeping: delete stale sealed-play clones and sync the
Gaea/Tolaria module cubes from the master list.

The master cube (shortId `sealed`) tags every card either 🌳 Gaea or
🧙 Tolaria; the /gaea and /tolaria cubes must be exactly the cards
carrying their tag.

Dry-run by default — prints what it would do. Pass --apply to execute.
"""

import argparse
import os
import pathlib
import subprocess
import sys

from cc import CubeCobra, board_delta, describe_delta, missing_slot_removals

MASTER = "sealed"
MODULES = {
    "gaea": "🌳 Gaea",
    "tolaria": "🧙 Tolaria",
}
CLONE_PREFIX = "Clone of Gaelaria"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="actually delete clones and push syncs")
    args = parser.parse_args()

    cc = CubeCobra()
    have_creds = os.environ.get("CUBECOBRA_USERNAME") and os.environ.get("CUBECOBRA_PASSWORD")
    if have_creds or sys.stdin.isatty():
        my_cubes = cc.login()
    elif args.apply:
        sys.exit("--apply needs credentials: set CUBECOBRA_USERNAME/CUBECOBRA_PASSWORD or run interactively")
    else:
        print("(no credentials — clone check skipped in this dry run)")
        my_cubes = []

    # --- 1. stale clones -------------------------------------------------
    master_json = cc.cube_json(MASTER)
    protected = {master_json["id"]}
    clones = [c for c in my_cubes if c["name"].startswith(CLONE_PREFIX) and c["id"] not in protected]
    print(f"Clones to delete ({len(clones)}):")
    for c in clones:
        print(f"  x {c['name']} ({c['id']})")

    # --- 2. module sync --------------------------------------------------
    master_cards = master_json["cards"]["mainboard"]
    by_tag = {tag: [] for tag in MODULES.values()}
    odd = []
    for card in master_cards:
        hits = [t for t in card.get("tags", []) if t in by_tag]
        if len(hits) != 1:
            odd.append(card["name"])
            continue
        by_tag[hits[0]].append(card)
    if odd:
        print(f"WARNING: {len(odd)} master cards without exactly one module tag "
              f"(skipped): {', '.join(odd[:10])}{'…' if len(odd) > 10 else ''}")

    deltas = {}
    for short_id, tag in MODULES.items():
        module = cc.cube_json(short_id)
        mainboard = module["cards"]["mainboard"]
        adds, removes = board_delta(mainboard, by_tag[tag])
        stored_count = module.get("cardCount", len(mainboard))
        slot_removes = missing_slot_removals(mainboard, stored_count, f"{short_id} mainboard")
        removes.extend(slot_removes)
        deltas[short_id] = (module, adds, removes)
        print(f"\n{module['name']} ({short_id}) — should hold {len(by_tag[tag])} {tag} cards, "
              f"currently {len(mainboard)} visible / {stored_count} stored:")
        if adds or removes:
            describe_delta("sync", adds, removes)
        else:
            print("  in sync ✓")

    if not args.apply:
        print("\nDry run — nothing changed. Re-run with --apply to execute.")
        return

    # --- 3. execute ------------------------------------------------------
    print("\nApplying:")
    for c in clones:
        print(f"deleting {c['name']}…")
        cc.remove_cube(c["id"])
    for short_id, (module, adds, removes) in deltas.items():
        if not (adds or removes):
            continue
        print(f"syncing {short_id}…")
        changes = {"mainboard": {}}
        if adds:
            changes["mainboard"]["adds"] = adds
        if removes:
            changes["mainboard"]["removes"] = removes
        result = cc.commit_batched(
            module["id"], changes, module.get("version", 0),
            title="Automated sync from Gaelaria",
        )
        print(f"  committed, new version {result.get('version')}")

    print("refreshing local CSVs…")
    subprocess.run(["bash", "fetch.sh"], check=False,
                   cwd=pathlib.Path(__file__).resolve().parent)
    print("done.")


if __name__ == "__main__":
    main()
