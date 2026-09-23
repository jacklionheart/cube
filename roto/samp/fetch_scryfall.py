"""Regenerate scryfall.json for the union of all sources/*.xlsx cube lists.

Keyed by cube card names (as typed in the Cube tab). Batched
/cards/collection lookups via curl (urllib SSL is broken on this
python), User-Agent header, 0.3s sleeps, front-half fallback for
split/room cards. Fields: cmc, type_line, colors, color_identity,
produced_mana, oracle_text.
"""

import json
import pathlib
import re
import subprocess
import time

import openpyxl

HERE = pathlib.Path(__file__).parent
BATCH = 75
UA = "cubeds/1.0 (roto analysis; jack@loopflow.studio)"
FIELDS = ("cmc", "type_line", "colors", "color_identity",
          "produced_mana", "oracle_text")


def cube_names():
    names, seen = [], set()
    for path in sorted((HERE / "sources").glob("*.xlsx")):
        ws = openpyxl.load_workbook(path, data_only=True)["Cube"]
        r = 2
        while ws.cell(r, 2).value not in (None, ""):
            n = str(ws.cell(r, 2).value).strip()
            if n not in seen:
                seen.add(n)
                names.append(n)
            r += 1
    return names


# cube lists sometimes use a card's alternate (in-universe) name
NAME_ALIASES = {"Outsmart the Amateur": "School Daze"}


def base_name(n):
    """Cube duplicates carry a numeric suffix: 'Hallowed Fountain 2'."""
    base = re.sub(r" \d+$", "", n)
    return NAME_ALIASES.get(base, base)


def fetch_batch(names):
    body = json.dumps({"identifiers": [{"name": n} for n in names]})
    out = subprocess.run(
        ["curl", "-s", "--fail", "https://api.scryfall.com/cards/collection",
         "-H", "Content-Type: application/json", "-H", f"User-Agent: {UA}",
         "-d", body],
        check=True, capture_output=True).stdout
    return json.loads(out)


def main():
    names = cube_names()
    print(f"{len(names)} cube cards")
    result = {}
    def record(n, card):
        result[n] = {f: card[f] for f in FIELDS if f in card}
        # split/room cards keep faces' combined oracle; faces carry
        # colors when the top level omits them
        if "colors" not in result[n] and card.get("card_faces"):
            cols = sorted({c for f_ in card["card_faces"]
                           for c in f_.get("colors", [])})
            result[n]["colors"] = cols

    for i in range(0, len(names), BATCH):
        chunk = names[i:i + BATCH]
        # collection matches full "A // B" names; fall back to front halves
        resp = fetch_batch([base_name(n) for n in chunk])
        found = {c["name"]: c for c in resp["data"]}
        for n in chunk:
            card = found.get(base_name(n))
            if card is None:  # front-half fallback for split/room cards
                front = base_name(n).split("//")[0].strip()
                card = next((c for c in found.values()
                             if c["name"].split("//")[0].strip() == front),
                            None)
            if card is not None:
                record(n, card)
        print(f"batch {i // BATCH + 1}: {len(result)} total")
        time.sleep(0.3)

    # retry any stragglers one at a time (front half for split cards)
    for n in [n for n in names if n not in result]:
        time.sleep(0.3)
        q = base_name(n).split("//")[0].strip()
        sub = fetch_batch([q])
        if sub["data"]:
            record(n, sub["data"][0])
        else:
            print(f"NOT FOUND: {n}")
    (HERE / "scryfall.json").write_text(
        json.dumps(result, indent=1, sort_keys=True))
    missing = [n for n in names if n not in result]
    print(f"wrote {len(result)}/{len(names)}; missing: {missing}")


if __name__ == "__main__":
    main()
