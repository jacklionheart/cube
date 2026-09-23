"""Build decks_all.tsv: decks.tsv (s4, unchanged) + old-pod decks.

Old-pod scrapes (discord-scrape/<slug>.json, keys u/t/l/i) are assigned
to draft-grid players by CONTENT: each sealeddeck pool's non-basic cards
are matched against every player's picks and the deck goes to the player
with the highest overlap. This sidesteps two problems name-matching
can't solve: RTB-sourced drafts label players "Seat N", and Discord
message grouping hides the author of some link posts. Name matching is
still computed as a cross-check and disagreements are printed.

Image-only decks (no sealeddeck link) are left out — noted, not OCR'd.

Run: python3 build_decks_all.py   (writes decks_all.tsv)
"""

import json
import pathlib
import re
import subprocess
import sys
import time

import refresh_all
from build_decks_tsv import match as name_match
from roto_summary import parse_draft, norm, BASICS

HERE = pathlib.Path(__file__).parent
CACHE = HERE / "deckcache"

OLD_SCRAPE2DRAFT = {
    "bolt-10-25": "Lightning Bolt (s1)",
    "birds-10-25": "Birds of Paradise (s1)",
    "zen-12-25": "Zendikar (s2)",
    "tar-12-25": "Tarkir (s2)",
    "rav-12-25": "Ravnica (s2)",
    "lor-12-25": "Lorwyn (s2)",
    "inn-12-25": "Innistrad (s2)",
    "pyro-12-25": "Pyrogoyf (s2)",
    "dka-12-25": "Dark Ascension (s2)",
    "frf-01-26": "Fate Reforged (s2)",
    "bob-03-07": "Dark Confidant (s3)",
    "bbe-03-07": "Bloodbraid Elf (s3)",
    "goyf-03-07": "Tarmogoyf (s3)",
    "seize-03-07": "Thoughtseize (s3)",
    "blight-03-07": "Blightning (s3)",
    "term-03-19": "Terminate (s3)",
    "maels-03-19": "Maelstrom Pulse (s3)",
    "ravine-04-04": "Raging Ravine (s3)",
    "lili-04-04": "Liliana (s3)",
    "ooze-04-04": "Scavenging Ooze (s3)",
    "cabal-04-04": "Cabal (s3)",
    "rabbit-06-26": "Rabbit Battery (s3)",
    "kappa-06-26": "Kappa Cannoneer (s3)",
    # no decks channel found for Inquisition (s3); yotia-01-26 is not a
    # roto draft in RTB/sheets (see discord-scrape/notes.txt)
}


def fetch_pool(pool_id):
    path = CACHE / f"{pool_id}.json"
    if not path.exists():
        subprocess.run(["curl", "-sf", "-o", str(path),
                        f"https://sealeddeck.tech/api/pools/{pool_id}"],
                       check=True)
        time.sleep(0.3)
    return json.loads(path.read_text())


def strip_copy(name):
    return re.sub(r" \d+$", "", name)


def pool_cards(pool):
    """Non-basic cards in deck+sideboard. Some posts link a whole-pool
    dump (500+ cards, everything in 'hidden' or a huge sideboard) —
    those can't be content-matched, so the caller treats >100 cards as
    a dump and falls back to the author's name."""
    cards = set()
    for zone in ("deck", "sideboard"):
        for e in pool.get(zone) or []:
            n = norm(e["name"])
            if n not in BASICS:
                cards.add(n)
    if not cards:
        for e in pool.get("hidden") or []:
            n = norm(e["name"])
            if n not in BASICS:
                cards.add(n)
    return cards


def main():
    CACHE.mkdir(exist_ok=True)
    rows = []
    for slug, draft_name in OLD_SCRAPE2DRAFT.items():
        path = HERE / "discord-scrape" / f"{slug}.json"
        if not path.exists():
            print(f"no scrape for {draft_name}", file=sys.stderr)
            continue
        src = HERE / "sources" / f"{refresh_all.slugify(draft_name)}.xlsx"
        dpa = refresh_all.SOURCES_ALL[draft_name][1]
        d, _ = parse_draft(src, draft_name, dpa)
        picks_by_player = {p: set() for p in d.players}
        for card, pick in d.picks.items():
            picks_by_player[pick.player].add(norm(strip_copy(card)))

        entries = json.load(open(path))
        author = None
        counts = {}
        for e in entries:
            author = e.get("u") or author
            for pool_id in e["l"]:
                pool = fetch_pool(pool_id)
                cards = pool_cards(pool)
                if not cards:
                    print(f"  empty pool {pool_id} ({draft_name})",
                          file=sys.stderr)
                    continue
                nm = name_match(draft_name, author, d.players) if author else None
                if len(cards) > 100:
                    if nm is None:
                        print(f"  DUMP with no author match: {draft_name} "
                              f"{pool_id} ({len(cards)} cards, {author!r})",
                              file=sys.stderr)
                        continue
                    print(f"  pool dump -> author: {draft_name} {pool_id} "
                          f"-> {nm}", file=sys.stderr)
                    counts[nm] = counts.get(nm, 0) + 1
                    rows.append((draft_name, nm,
                                 "initial" if counts[nm] == 1 else "rebuild",
                                 f"https://sealeddeck.tech/{pool_id}"))
                    continue
                scores = sorted(((len(cards & pk), p)
                                 for p, pk in picks_by_player.items()),
                                reverse=True)
                (s1, p1), (s2, _) = scores[0], scores[1]
                cover = s1 / len(cards)
                if cover < 0.5 or s1 - s2 < 3:
                    # a pool matching NO seat is usually the redacted
                    # seat's deck (its picks are blank in the grid)
                    blank = [p for p, pk in picks_by_player.items() if not pk]
                    if nm is not None:
                        p1 = nm
                    elif cover < 0.35 and len(blank) == 1:
                        p1 = blank[0]
                        print(f"  redacted-seat by elimination: {draft_name} "
                              f"{pool_id} -> {p1} (author {author!r})",
                              file=sys.stderr)
                    else:
                        print(f"  AMBIGUOUS {draft_name} {pool_id}: best {p1} "
                              f"{s1}/{len(cards)} vs next {s2} (author "
                              f"{author!r} -> {nm})", file=sys.stderr)
                        continue
                elif nm is not None and nm != p1:
                    print(f"  content beats name: {draft_name} {pool_id}: "
                          f"{p1} ({s1}/{len(cards)}) vs author {author!r} -> "
                          f"{nm}", file=sys.stderr)
                counts[p1] = counts.get(p1, 0) + 1
                kind = "initial" if counts[p1] == 1 else "rebuild"
                rows.append((draft_name, p1, kind,
                             f"https://sealeddeck.tech/{pool_id}"))
        no_deck = [p for p in d.players if p not in counts]
        if no_deck:
            print(f"{draft_name}: no deck for {', '.join(no_deck)}",
                  file=sys.stderr)

    out = (HERE / "decks.tsv").read_text().rstrip("\n").splitlines()
    out += ["\t".join(r) for r in rows]
    (HERE / "decks_all.tsv").write_text("\n".join(out) + "\n")
    print(f"decks_all.tsv: {len(out) - 1} links "
          f"({len(rows)} old-pod, rest s4)")


if __name__ == "__main__":
    main()
