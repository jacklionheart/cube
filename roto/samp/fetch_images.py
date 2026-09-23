"""Fetch Scryfall image URIs for every card in scryfall.json -> images.json."""

import json
import pathlib
import re
import subprocess
import time

HERE = pathlib.Path(__file__).parent
UA = "cube-roto-analysis/1.0 (jack@loopflow.studio)"


NAME_ALIASES = {"Outsmart the Amateur": "School Daze"}


def base_name(n):
    base = re.sub(r" \d+$", "", n)
    return NAME_ALIASES.get(base, base)


def fetch(names):
    body = json.dumps({"identifiers": [{"name": n} for n in names]})
    out = subprocess.run(
        ["curl", "-s", "--fail", "https://api.scryfall.com/cards/collection",
         "-H", "Content-Type: application/json", "-H", f"User-Agent: {UA}",
         "-d", body], check=True, capture_output=True).stdout
    return json.loads(out)["data"]


def image_uri(card):
    if card.get("image_uris"):
        return card["image_uris"]["normal"]
    faces = card.get("card_faces") or []
    for f in faces:
        if f.get("image_uris"):
            return f["image_uris"]["normal"]
    return None


def main():
    names = list(json.loads((HERE / "scryfall.json").read_text()))
    out_path = HERE / "images.json"
    out = json.loads(out_path.read_text()) if out_path.exists() else {}
    todo = [n for n in names if n not in out]
    for i in range(0, len(todo), 75):
        chunk = todo[i:i + 75]
        found = {c["name"]: c for c in fetch([base_name(n) for n in chunk])}
        for n in chunk:
            card = found.get(base_name(n)) or next(
                (c for c in found.values()
                 if c["name"].split("//")[0].strip()
                 == base_name(n).split("//")[0].strip()), None)
            if card and image_uri(card):
                out[n] = image_uri(card)
        time.sleep(0.3)
    out_path.write_text(json.dumps(out, indent=0, sort_keys=True))
    print(f"{len(out)}/{len(names)} images")


if __name__ == "__main__":
    main()
