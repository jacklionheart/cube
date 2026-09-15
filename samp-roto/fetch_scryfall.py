"""Regenerate scryfall.json for the cube list in sources/draft1.xlsx.

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
UA = "cube-roto-analysis/1.0 (jack@loopflow.studio)"
FIELDS = ("cmc", "type_line", "colors", "color_identity",
          "produced_mana", "oracle_text")


def cube_names():
    ws = openpyxl.load_workbook(HERE / "sources" / "draft1.xlsx",
                                data_only=True)["Cube"]
    names, r = [], 2
    while ws.cell(r, 2).value not in (None, ""):
        names.append(str(ws.cell(r, 2).value).strip())
        r += 1
    return names


def base_name(n):
    """Cube duplicates carry a numeric suffix: 'Hallowed Fountain 2'."""
    return re.sub(r" \d+$", "", n)


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
