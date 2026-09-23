"""Load submitted pools and adjudicate companion zones for any cube."""
import json
import pathlib
import sys
import unicodedata
import urllib.request

BASICS = {"plains", "island", "swamp", "mountain", "forest", "wastes"}

# A companion lives in the sideboard slot of exported pools but is
# functionally part of the deck — IF the maindeck actually satisfies its
# deckbuilding requirement (it might just be a sided-out card otherwise).
COMPANIONS = {
    "Gyruda, Doom of Depths", "Jegantha, the Wellspring",
    "Kaheera, the Orphanguard", "Keruga, the Macrosage",
    "Lurrus of the Dream-Den", "Lutri, the Spellchaser",
    "Obosh, the Preypiercer", "Umori, the Collector",
    "Yorion, Sky Nomad", "Zirda, the Dawnwaker",
}
MAIN_ZONES = ("main", "companion")
PERMANENT_TYPES = ("Creature", "Artifact", "Enchantment", "Planeswalker",
                   "Battle", "Land")


def companion_ok(companion, main_cards, main_size, has_basics, scry):
    """Does the maindeck satisfy this companion's deckbuilding requirement?
    main_cards: nonbasic maindeck names (basics are MV-0 lands and satisfy
    every implemented requirement automatically). Returns None if the check
    for this companion isn't implemented."""
    def cmc(c):
        return scry[c]["cmc"]

    def is_land(c):
        return "Land" in scry[c]["type_line"].split(" — ")[0]

    def is_permanent(c):
        return any(t in scry[c]["type_line"] for t in PERMANENT_TYPES)

    nonlands = [c for c in main_cards if not is_land(c)]
    if companion == "Lurrus of the Dream-Den":
        return all(cmc(c) <= 2 for c in main_cards if is_permanent(c))
    if companion == "Obosh, the Preypiercer":
        return all(cmc(c) % 2 == 1 for c in nonlands)
    if companion == "Gyruda, Doom of Depths":
        return all(cmc(c) % 2 == 0 for c in nonlands)
    if companion == "Keruga, the Macrosage":
        return all(cmc(c) >= 3 for c in nonlands)
    if companion == "Yorion, Sky Nomad":
        # some pools omit basics entirely; >40 listed cards still proves a
        # deliberately oversized (60-card) deck
        return main_size >= 60 or (not has_basics and main_size > 40)
    if companion == "Lutri, the Spellchaser":
        return True  # singleton cube decks always qualify
    return None  # Kaheera/Jegantha/Umori/Zirda: adjudicate by hand if seen


def norm(name):
    """Casefold and strip accents: sealeddeck uses 'lorien revealed' etc."""
    return "".join(
        c for c in unicodedata.normalize("NFD", name.strip().casefold())
        if not unicodedata.combining(c)
    )


# pool exports sometimes use a card's alternate (in-universe) name
def load_decks(tsv_path, cube, *, aliases=None):
    """Read decks.tsv (draft/player/kind/url), fetch+cache each sealeddeck
    pool, and return {(draft, player): {canonical card: 'main'|'side'|'hidden'}}.
    A rebuild deck replaces an initial one for the same draft+player."""
    tsv_path = pathlib.Path(tsv_path)
    cache = tsv_path.parent / "deckcache"
    cache.mkdir(exist_ok=True)
    canonical = {norm(c): c for c, _, _ in cube}
    canonical.update({norm(c.split(" // ")[0]): c for c, _, _ in cube if " // " in c})
    canonical.update({norm(a): c for a, c in (aliases or {}).items()})

    entries, links = {}, []
    for line in tsv_path.read_text().splitlines()[1:]:
        if not line.strip():
            continue
        draft, player, kind, url = (f.strip() for f in line.split("\t"))
        pool_id = url.rstrip("/").split("/")[-1]
        key = (draft, player)
        links.append([draft, player, kind, url])
        if key in entries and entries[key][0] == "rebuild" and kind != "rebuild":
            continue
        entries[key] = (kind, pool_id)
    for link in links:
        chosen = entries[(link[0], link[1])]
        link.append("Y" if chosen == (link[2], link[3].rstrip("/").split("/")[-1]) else "")

    scry_path = tsv_path.parent / "scryfall.json"
    scry = json.loads(scry_path.read_text()) if scry_path.exists() else None
    decks, main_sizes = {}, {}
    for key, (_, pool_id) in entries.items():
        path = cache / f"{pool_id}.json"
        if not path.exists():
            with urllib.request.urlopen(f"https://sealeddeck.tech/api/pools/{pool_id}") as r:
                path.write_bytes(r.read())
        pool = json.loads(path.read_text())
        main_sizes[key] = sum(c["count"] for c in pool.get("deck") or [])
        has_basics = any(norm(c["name"]) in BASICS for c in pool.get("deck") or [])
        cards = {}
        for zone, label in [("deck", "main"), ("sideboard", "side"), ("hidden", "hidden")]:
            for entry in pool.get(zone) or []:
                name = norm(entry["name"])
                if name in BASICS:
                    continue
                if name not in canonical:
                    print(f"warning: {key}: unmatched deck card {entry['name']!r} ({label})",
                          file=sys.stderr)
                    continue
                cards.setdefault(canonical[name], label)
        for card, zone in cards.items():
            if card not in COMPANIONS or zone != "side":
                continue
            if scry is None:
                print(f"warning: {key}: {card} in sideboard but scryfall.json "
                      "missing — cannot check companion requirement", file=sys.stderr)
                continue
            main_cards = [c for c, z in cards.items() if z == "main"]
            ok = companion_ok(card, main_cards, main_sizes[key], has_basics, scry)
            if ok:
                cards[card] = "companion"
            elif ok is None:
                print(f"warning: {key}: {card} in sideboard; no requirement "
                      "check implemented — left as sideboard", file=sys.stderr)
        decks[key] = cards
    return decks, main_sizes, links


def check_deck_coverage(decks, main_sizes, drafts):
    """Unlisted picks count as sideboard ('N'); that's only safe when the
    submitted maindeck is a full 40 cards. Warn when it isn't."""
    by_name = {d.name: d for d in drafts}
    for (dname, player), cards in decks.items():
        draft = by_name.get(dname)
        if draft is None:
            print(f"warning: decks.tsv references unknown draft {dname!r}", file=sys.stderr)
            continue
        picks = [c for c, p in draft.picks.items() if p.player == player]
        if not picks:
            print(f"warning: {dname}: no picks found for player {player!r}", file=sys.stderr)
            continue
        unlisted = [c for c in picks if c not in cards]
        if unlisted and main_sizes.get((dname, player)) != 40:
            print(
                f"warning: {dname} {player}: {len(unlisted)} picks unlisted in pool "
                f"and maindeck is {main_sizes.get((dname, player))} cards (not 40) — "
                "their 'N' status is unreliable", file=sys.stderr,
            )
