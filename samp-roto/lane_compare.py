"""Compare lane definitions for the samp s4 pods as an essay-style HTML
report (styled after roto/report.py's lane-report).

Definitions compared (over REAL maindecks, known for 11 of 13 pods):
  A. Maximal groups: card sets maindecked together (whole set, one deck)
     in >= S of the 13 decked drafts, size >= Z — Jack's definition, at
     7/3, 6/3 (the >50% bar), and 5/3. Overlapping maximal groups roll
     up into families (union shown as card images, variants listed).
  B. Component lanes: connected components of the pairwise co-maindeck
     graph at >= 6 shared drafts (what the published sheet's Lanes tab
     uses).

Usage: python3 lane_compare.py [out.html]
"""

import html
import json
import pathlib
import sys

import refresh
from roto_summary import parse_draft

HERE = pathlib.Path(__file__).parent
WUBRG = "WUBRG"

GUILDS = {
    "W": "White", "U": "Blue", "B": "Black", "R": "Red", "G": "Green",
    "WU": "Azorius", "UB": "Dimir", "BR": "Rakdos", "RG": "Gruul",
    "WG": "Selesnya", "WB": "Orzhov", "UR": "Izzet", "BG": "Golgari",
    "WR": "Boros", "UG": "Simic", "WUB": "Esper", "UBR": "Grixis",
    "BRG": "Jund", "WBG": "Abzan", "WUG": "Bant", "UBG": "Sultai",
    "WBR": "Mardu", "WUR": "Jeskai", "URG": "Temur", "WRG": "Naya",
}


def guild(letters):
    return GUILDS.get(letters, letters)


def is_land(name, scry):
    """Front-face land check (MDFC spell//land faces count as nonland)."""
    info = scry.get(name)
    return bool(info) and "Land" in info["type_line"].split(" // ")[0]


def card_link(name):
    q = html.escape(name.replace(" 2", "", 1) if name.endswith(" 2") else name)
    return (f"<a href='https://scryfall.com/search?q=!%22{q}%22'>"
            f"{html.escape(name)}</a>")

CSS = """
body { font-family: Charter, Georgia, 'Times New Roman', serif;
       font-size: 19px; line-height: 1.65; color: #1a1a1a;
       max-width: 760px; margin: 56px auto 120px; padding: 0 20px;
       background: #fff; }
h1 { font-size: 26px; line-height: 1.25; margin: 0 0 6px; }
h2 { font-size: 21px; margin: 48px 0 8px; }
h3 { font-size: 17px; margin: 30px 0 4px; }
.meta { font-family: -apple-system, 'Segoe UI', Helvetica, sans-serif;
        font-size: 14px; color: #6b6b6b; margin: 2px 0 14px; }
.lane { border-top: 1px solid #e6e6e6; margin-top: 40px; padding-top: 16px; }
.num { font-family: -apple-system, 'Segoe UI', Helvetica, sans-serif;
       font-size: 13px; color: #9a9a9a; font-weight: 400; margin-right: 6px; }
.kept { color: #6b6b6b; font-size: .88em; }
.cards { display: flex; flex-wrap: wrap; gap: 8px; margin: 14px 0 18px; }
.cards img { width: 136px; border-radius: 6px; }
.mana { width: 13px; height: 13px; vertical-align: -1px; margin-right: 1px; }
.variants { font-family: -apple-system, 'Segoe UI', Helvetica, sans-serif;
            font-size: 13.5px; color: #444; margin: 6px 0 14px;
            padding-left: 20px; }
.variants li { margin: 3px 0; }
table { border-collapse: collapse; margin: 12px 0 20px; width: 100%;
        font-family: -apple-system, 'Segoe UI', Helvetica, sans-serif;
        font-size: 14px; }
th { text-align: left; font-weight: 600; padding: 6px 14px 6px 0;
     border-bottom: 1px solid #1a1a1a; }
td { padding: 6px 14px 6px 0; border-bottom: 1px solid #e6e6e6; }
"""


def mana(colors):
    return "".join(
        f"<img class='mana' src='https://svgs.scryfall.io/card-symbols/{c}.svg' alt='{c}'>"
        for c in colors)


def load_data():
    from roto_summary import MAIN_ZONES, load_decks

    drafts, cube, seen = [], [], set()
    for n in refresh.SOURCES:
        d, c = parse_draft(HERE / "sources" / f"{refresh.slugify(n)}.xlsx", n)
        drafts.append(d)
        for e in c:
            if e[0] not in seen:
                seen.add(e[0])
                cube.append(e)
    real_decks, _, _ = load_decks(HERE / "decks.tsv", cube)
    name2idx = {d.name: k for k, d in enumerate(drafts)}
    decks, card_decks = {}, {}
    for k, d in enumerate(drafts):
        for card, p in d.picks.items():
            deck = real_decks.get((d.name, p.player))
            if deck is None:
                continue  # no decklist known: contributes nothing
            zone = deck.get(card)
            if zone is None and card.endswith(" 2"):
                zone = deck.get(card[:-2].strip())
            if zone in MAIN_ZONES:
                decks.setdefault((k, p.player), set()).add(card)
    for dk, cards in decks.items():
        for c in cards:
            card_decks.setdefault(c, set()).add(dk)
    scry = json.loads((HERE / "scryfall.json").read_text())
    images = json.loads((HERE / "images.json").read_text())
    # lanes are about spells: drop lands from the co-maindeck universe
    # (mirrors roto/packages.nonland_owners)
    card_decks = {c: ds for c, ds in card_decks.items()
                  if not is_land(c, scry)}
    return drafts, decks, card_decks, scry, images


def support(deckset):
    return len({dk[0] for dk in deckset})


def mine(card_decks, min_sup, min_size):
    """Maximal card sets fully co-maindecked in >= min_sup drafts."""
    cards = sorted(c for c, ds in card_decks.items() if support(ds) >= min_sup)
    idx = {c: i for i, c in enumerate(cards)}
    frequent = {}

    def dfs(stack, ds):
        for c in cards:
            if idx[c] <= idx[stack[-1]]:
                continue
            nds = ds & card_decks[c]
            if support(nds) >= min_sup:
                frequent[tuple(stack + [c])] = nds
                dfs(stack + [c], nds)

    for c in cards:
        dfs([c], card_decks[c])
    maximal = []
    for S, ds in frequent.items():
        if len(S) < min_size:
            continue
        ss = set(S)
        if not any(support(ds & card_decks[c2]) >= min_sup
                   for c2 in cards if c2 not in ss):
            maximal.append((S, ds))
    return maximal


def families(maximal):
    """Union-find over maximal groups sharing >= 2 cards."""
    parent = list(range(len(maximal)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(len(maximal)):
        si = set(maximal[i][0])
        for j in range(i + 1, len(maximal)):
            if len(si & set(maximal[j][0])) >= 2:
                parent[find(i)] = find(j)
    fams = {}
    for i in range(len(maximal)):
        fams.setdefault(find(i), []).append(i)
    return sorted(fams.values(),
                  key=lambda f: -len({c for i in f for c in maximal[i][0]}))


def colors_of(cards, scry):
    u = set()
    for c in cards:
        u |= set((scry.get(c) or {}).get("colors") or [])
    return [c for c in WUBRG if c in u] or ["C"]


def card_grid(cards, images, order=None):
    ordered = order or sorted(cards)
    imgs = "\n".join(
        f"<img src='{images[c]}' alt=\"{html.escape(c)}\" "
        f"title=\"{html.escape(c)}\" loading='lazy'>"
        for c in ordered if c in images)
    return f"<div class='cards'>\n{imgs}\n</div>"


def host_line(group_decks, drafts):
    by_draft = {}
    for k, player in sorted(group_decks):
        by_draft.setdefault(k, player)
    return " · ".join(f"{drafts[k].name}: <b>{html.escape(p)}</b>"
                      for k, p in sorted(by_draft.items()))


def render_setting(out, tag, min_sup, min_size, card_decks, drafts, scry, images):
    maximal = mine(card_decks, min_sup, min_size)
    fams = families(maximal)
    out.append(f"<h2>{tag}: together in ≥{min_sup} of the 13 decked "
               f"drafts, size ≥{min_size}</h2>")
    out.append(f"<p class='meta'>{len(maximal)} maximal groups → "
               f"{len(fams)} families. A group only counts when every card "
               f"in it sat in one maindeck in ≥{min_sup} drafts; overlapping "
               f"groups (≥2 shared cards) roll up into a family.</p>")
    for fi, f in enumerate(fams):
        groups = sorted((maximal[i] for i in f),
                        key=lambda g: (-support(g[1]), -len(g[0])))
        union = {c for i in f for c in maximal[i][0]}
        # order union by how many of the family's groups contain each card
        freq = {c: sum(c in maximal[i][0] for i in f) for c in union}
        order = sorted(union, key=lambda c: (-freq[c], c))
        best, best_ds = groups[0]
        cl = "".join(colors_of(union, scry))
        out.append("<div class='lane'>")
        out.append(f"<h3><span class='num'>F{fi + 1}</span>"
                   f"{mana(cl)} {guild(cl)} family "
                   f"<span class='kept'>{len(union)} cards · {len(f)} "
                   f"groups · best {support(best_ds)}/13</span></h3>")
        out.append(f"<p class='meta'>Best group's decks — "
                   f"{host_line(best_ds, drafts)}</p>")
        out.append(card_grid(union, images, order))
        items = []
        for S, ds in groups[:8]:
            items.append(f"<li>[{support(ds)}/13, {len(S)}c] "
                         + ", ".join(card_link(c) for c in S) + "</li>")
        if len(groups) > 8:
            items.append(f"<li>… +{len(groups) - 8} more variants</li>")
        out.append(f"<ul class='variants'>{''.join(items)}</ul>")
        out.append("</div>")


def render_component_lanes(out, card_decks, drafts, scry, images, K=7):
    from collections import defaultdict
    co = defaultdict(set)
    for dk, _ in {dk: None for ds in card_decks.values() for dk in ds}.items():
        pass
    pair_count = defaultdict(int)
    by_deck = defaultdict(set)
    for c, ds in card_decks.items():
        for dk in ds:
            by_deck[dk].add(c)
    from itertools import combinations
    counted = defaultdict(set)
    for dk, cards in by_deck.items():
        for a, b in combinations(sorted(cards), 2):
            counted[(a, b)].add(dk[0])
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for (a, b), ds in counted.items():
        if len(ds) >= K:
            parent[find(a)] = find(b)
    comps = {}
    for c in list(parent):
        comps.setdefault(find(c), set()).add(c)
    lanes = sorted((s for s in comps.values() if len(s) >= 3),
                   key=lambda s: (-len(s), min(s)))
    out.append(f"<h2>For comparison: component lanes "
               f"(pairwise ≥{K} shared drafts)</h2>")
    out.append(f"<p class='meta'>{len(lanes)} lanes. Cards are chained: "
               f"an edge is a PAIR co-maindecked in ≥{K} drafts, a lane is a "
               "connected component — so a lane never certifies that the "
               "whole set appeared together. This is what the published "
               "sheet's Lanes tab shows.</p>")
    for i, cards in enumerate(lanes):
        out.append("<div class='lane'>")
        out.append(f"<h3><span class='num'>L{i + 1}</span>"
                   f"{mana(''.join(colors_of(cards, scry)))} "
                   f"{guild(''.join(colors_of(cards, scry)))} — "
                   f"{len(cards)} cards</h3>")
        out.append(card_grid(cards, images))
        out.append("</div>")


def main():
    out_path = pathlib.Path(sys.argv[1] if len(sys.argv) > 1
                            else HERE / "out" / "lane-compare.html")
    drafts, decks, card_decks, scry, images = load_data()
    out = [f"<meta charset='utf-8'><title>Samp Roto s4 — Lane Definitions"
           f"</title><style>{CSS}</style>"]
    out.append("<h1>Samp Roto s4 — Lane Definitions Compared</h1>")
    out.append("<p class='meta'>13 pods · maindeck = all 45 picks (v1) · "
               "generated from the same data as the published sheet</p>")
    out.append(
        "<h2>How this works</h2>"
        "<p>The candidate definition: <i>a lane is a set of cards that were "
        "all maindecked together — the whole set, in one deck — in more "
        "than half of the drafts.</i> Mining finds every <b>maximal</b> such "
        "group (no card can be added without dropping below the threshold); "
        "overlapping groups (≥2 shared cards) roll up into a "
        "<b>family</b>, shown as one card grid ordered core-first. "
        "<b>Lands are excluded</b> — otherwise every family is half "
        "fetchlands. Below: the definition at the chosen setting "
        "(≥7 of the 13 decked drafts — the >50% rule), one stricter and "
        "one looser setting, then the pairwise component lanes the "
        "published sheet currently uses.</p>"
        "<p class='meta'>Caveats: maindeck status comes from the real "
        "submitted sealeddeck lists (companion-aware), so these are "
        "built-together lanes. Decklists are known for 126 of 129 decks "
        "(all 13 pods) — Dom's and aidybaby's decks are transcribed from "
        "their posted images; Rocketman's and Rob's Baleful Strix decks "
        "and Kishla's tenderdrafter remain unknown. "
        "The cube also drifted ~30 cards "
        "across the season, so late-add cards can support at most the "
        "drafts they were available in. Source: the 13 s4 pod "
        "spreadsheets + read-the-bones + Rough Drafts #decks channels.</p>")
    render_setting(out, "Strict", 8, 3, card_decks, drafts, scry, images)
    render_setting(out, "Chosen — the >50% rule", 7, 3,
                   card_decks, drafts, scry, images)
    render_setting(out, "Looser", 6, 3, card_decks, drafts, scry, images)
    render_component_lanes(out, card_decks, drafts, scry, images, K=7)
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text("\n".join(out))
    print(out_path)


if __name__ == "__main__":
    main()
