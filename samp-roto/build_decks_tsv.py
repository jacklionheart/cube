"""Build decks.tsv from discord-scrape/*.json.

Maps Discord authors to draft-grid player names (normalization + hand
aliases for by-elimination cases), orders each player's links
chronologically (first = initial, later = rebuild), and reports roster
players with no deck link. Run whenever a scrape file changes.
"""

import json
import pathlib
import re
import sys

import refresh
from roto_summary import parse_draft

HERE = pathlib.Path(__file__).parent

SCRAPE2DRAFT = {
    "ledger-shredder": "Ledger Shredder", "slickshot": "Slickshot",
    "kishla": "Kishla Skimmer", "raven-eagle": "Raven Eagle",
    "hard-academic": "Hardened Academic", "baleful-strix": "Baleful Strix",
    "goose-mother": "Goose Mother", "yorion": "Yorion",
    "mockingbird": "Mockingbird", "aven": "Aven Interrupter",
    "skycoach": "Skycoach Conductor",
}

# (draft, author) -> roster name, for cases normalization can't derive
ALIASES = {
    ("Slickshot", "[Tom] Rasta#42946"): "mwc (Tom)",
    ("Slickshot", "Most Decrepit Old Rob"): "Rob",
    ("Raven Eagle", "dillon - digthedill#46954"): "DILL 🛶",
    ("Raven Eagle", "clong"): "Dunkin on Tom.dek",
    ("Baleful Strix", "Melissing Out - wings#28708"): "Melissa",
    ("Baleful Strix", "lordtupperware"): "Ethan",
    ("Goose Mother", "Jack (Arpanet#12152)"): "Jack L",
    ("Goose Mother", "Adhavoc"): "Justin",
    ("Goose Mother", "dillon - digthedill#46954"): "Dillon",
    ("Goose Mother", "philjackson // philjack#50425"): "Phil",
    ("Yorion", "Neo (Marc)"): "Marc",
    ("Yorion", "f-of-X (Paul)"): "Paul",
    ("Yorion", "nlaframwashed"): "nlaframboise",
    ("Mockingbird", "samp"): "Sam",
    ("Mockingbird", "tang (jonnietang#11502)"): "jonnietang",
}


def norm(s):
    s = re.sub(r"#\d+", "", s)
    s = re.sub(r"[^\w]", "", s, flags=re.UNICODE)
    return s.casefold()


def author_variants(a):
    """Name fragments an author string might match a roster name by."""
    v = [a]
    for sep in ("->", "//", ":"):
        if sep in a:
            v.append(a.split(sep)[0])
    m = re.match(r"([^(]+)\(([^)]+)\)", a)
    if m:
        v += [m.group(1), m.group(2)]
    return [x.strip() for x in v if x.strip()]


def match(draft, author, roster):
    if (draft, author) in ALIASES:
        return ALIASES[(draft, author)]
    for var in author_variants(author):
        nv = norm(var)
        for p in roster:
            np = norm(p)
            if nv == np or nv.startswith(np) or np.startswith(nv):
                return p
    return None


def main():
    rosters = {}
    for n in refresh.SOURCES:
        d, _ = parse_draft(HERE / "sources" / f"{refresh.slugify(n)}.xlsx", n)
        rosters[n] = d.players

    rows, missing = [], []
    for slug, draft in SCRAPE2DRAFT.items():
        entries = json.load(open(HERE / "discord-scrape" / f"{slug}.json"))
        seen_players = set()
        counts = {}
        for e in entries:
            player = match(draft, e["a"], rosters[draft])
            if player is None:
                print(f"UNMATCHED: {draft}: {e['a']!r}", file=sys.stderr)
                continue
            for pool_id in e["l"]:
                counts[player] = counts.get(player, 0) + 1
                kind = "initial" if counts[player] == 1 else "rebuild"
                rows.append((draft, player,
                             kind, f"https://sealeddeck.tech/{pool_id}"))
            seen_players.add(player)
        for p in rosters[draft]:
            if p not in seen_players:
                missing.append((draft, p))

    out = ["draft\tplayer\tkind\turl"]
    out += ["\t".join(r) for r in rows]
    (HERE / "decks.tsv").write_text("\n".join(out) + "\n")
    print(f"decks.tsv: {len(rows)} links, "
          f"{len({(r[0], r[1]) for r in rows})} decks")
    for draft, p in missing:
        print(f"  no deck link: {draft}: {p}")


if __name__ == "__main__":
    main()
