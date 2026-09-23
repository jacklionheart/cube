"""Data-driven components for "The Lords of Limited Rotisserie Meta".

build() recomputes every {{slot}} in post.md from the roto analysis
library (three draft grids + 28 sealeddeck maindecks). The asserts pin
numbers that post.md hardcodes in prose, so copy drift gets caught at
build time. Prose is Jack's; this file only makes charts and galleries.
"""

import html
import json
import pathlib
import random
import sys
from collections import Counter
from urllib.parse import quote

POST = pathlib.Path(__file__).resolve().parent
SHARED = POST.parent
ROTO = SHARED.parent / "roto" / "lol"
for p in (str(SHARED), str(ROTO)):
    if p not in sys.path:
        sys.path.insert(0, p)

from render import canon_key, mana, card_gallery  # noqa: E402
from packages import (card_colors, deck_sets, load, load_scryfall,  # noqa: E402
                      maindeck_owners, nonland_owners, signature_groups,
                      unique_ensembles)
from roto_summary import load_decks  # noqa: E402

TITLE = "Rotisserie Drafting the Lords of Limited Cube"
SLUG = "lol-kickoff"
SCRIPTS = ""  # set by build(): the deckImgs data for [data-deck] hovers


def build():
    drafts, cube, decks = load()
    scry = load_scryfall()
    owners = nonland_owners(maindeck_owners(drafts, cube, decks), scry)
    colors = {c: card_colors(c, scry) for c in owners}
    groups = signature_groups(owners, min_size=2)
    _, _, links = load_decks(ROTO / "decks.tsv", cube)
    url_map = {(dr, pl): u for dr, pl, kind, u, used in links
               if used == "Y" and "manual-" not in u}

    def deck_link(k, pl, short=False):
        url = url_map.get((drafts[k].name, pl))
        lab = html.escape(pl if short else f"{drafts[k].name} {pl}")
        dd = f" data-deck='{k}:{html.escape(pl)}'"
        return (f'<a href="{url}"{dd}>{lab}</a>' if url
                else f'<a{dd}>{lab}</a>')
    lanes = [(sig, sorted(cards)) for sig, cards in groups
             if len(cards) >= 3]
    CORE_MARKERS = [("Rally at the Hornburg", "Tokens"),
                    ("Mayhem Devil", "Sac"),
                    ("Fires of Invention", "Ramp"),
                    ("Everything Pizza", "Ramp"),
                    ("Spider Spawning", "Graveyard"),
                    ("Expressive Iteration", "Spells"),
                    ("Shoreline Looter", "Looting")]

    def core_name(cards):
        for marker, nm in CORE_MARKERS:
            if marker in cards:
                return nm
        return "?"
    FAMILY = {"Tokens": "Aggro", "Sac": "Aggro", "Ramp": "Green", "Graveyard": "Green",
              "Spells": "Blue", "Looting": "Blue"}

    def colors_of(cards):
        u = set()
        for c in cards:
            u |= colors.get(c, set())
        return "".join(x for x in "WUBRG" if x in u) or "C"

    def gallery(cards, shuffle=False, small=False):
        if shuffle:
            # deterministic shuffle (seeded by the card set) so deck
            # galleries don't read as alphabetical but builds stay stable
            cards = sorted(cards)
            random.Random(",".join(cards)).shuffle(cards)
        else:
            cards = sorted(cards)
        return card_gallery(cards, {c: scry[c].get("image") for c in cards}, small=small)


    def lane_by_colors(cl, exclude=()):
        for sig, cards in lanes:
            if colors_of(cards) == cl and tuple(cards) not in exclude:
                return sig, cards
        return None

    pair_teams = [(sig, sorted(cards)) for sig, cards in groups
                  if len(cards) == 2]

    def satellites(lane_sig):
        """Standalone pairs kept by at least two of this lane's decks."""
        out = []
        for psig, pcards in pair_teams:
            if sum(a == b for a, b in zip(psig, lane_sig)) >= 2:
                out.append(pcards)
        return out

    def lane_block(entry):
        sig, cards = entry
        h = []
        sats = satellites(sig)
        if sats:
            h.append("<p class='meta'>Satellites — pairs kept by two of "
                     "this core's three decks:</p><div class='pairs'>")
            for pcards in sats:
                imgs = "".join(
                    f"<img src='{scry[c].get('image')}' "
                    f"alt='{html.escape(c)}' title='{html.escape(c)}' "
                    f"loading='lazy'>" for c in pcards)
                h.append(f"<span class='pair'>{imgs}</span>")
            h.append("</div>")
        return "".join(h)

    # Jack's taxonomy of the size-3+ teams (labels are his; mapping of
    # the two blue teams is a guess — swap if backwards)
    def core_by_marker(m):
        return next((sig, cards) for sig, cards in lanes if m in cards)

    tokens = core_by_marker("Rally at the Hornburg")
    sac = core_by_marker("Mayhem Devil")
    temur_ramp = core_by_marker("Fires of Invention")
    golgari_ramp = core_by_marker("Everything Pizza")
    graveyard = core_by_marker("Spider Spawning")
    blue_spells = core_by_marker("Expressive Iteration")
    blue_tempo = core_by_marker("Shoreline Looter")

    parts = {}
    assert len(lanes) == 7, len(lanes)  # post.md says "seven"

    # --- the Lanes viewer: Macro -> Core sidebar + card viewer --------
    fam_order = ["Aggro", "Green", "Blue"]
    cores_by_fam = {f: [] for f in fam_order}
    for lsig, lcards in lanes:
        nm = core_name(lcards)
        cores_by_fam[FAMILY[nm]].append((nm, lsig, lcards))
    vh = ["<div class='explorer'><div class='sidebar'>"]
    idx = 0
    panes = []
    for f in fam_order:
        vh.append(f"<div class='sbh'>{f}</div>")
        for nm, lsig, lcards in cores_by_fam[f]:
            on = " class='on'" if idx == 0 else ""
            vh.append(f"<button{on} data-group='cores' "
                      f"data-show='core-{idx}'>{mana(colors_of(lcards))} "
                      f"{nm}</button>")
            hid = "" if idx == 0 else " hidden"
            panes.append(f"<div data-pane='cores' id='core-{idx}'{hid}>"
                         f"{gallery(lcards)}</div>")
            idx += 1
    vh.append("</div><div class='vpanes'>")
    vh += panes
    vh.append("</div></div>")
    parts["lanes-viewer"] = "\n".join(vh)

    CORE_COLORS = {core_name(lc): colors_of(lc) for _, lc in lanes}
    lane_of_deck = {}
    for lsig, lcards in lanes:
        nm = core_name(lcards)
        for k, pl in enumerate(lsig):
            lane_of_deck.setdefault((k, pl), []).append(nm)

    def classify(psig):
        for lsig, _ in lanes:
            if sum(a == b for a, b in zip(psig, lsig)) >= 2:
                return "satellite"
        per_deck = [set(lane_of_deck.get((k, pl), []))
                    for k, pl in enumerate(psig)]
        touched = set().union(*per_deck)
        n_decks = sum(1 for s in per_deck if s)
        # a true bridge spans lanes via different decks — one deck
        # owning two lanes doesn't count
        return ("bridge" if len(touched) >= 2 and n_decks >= 2
                else "free")

    def pair_span(pcards):
        imgs = "".join(
            f"<img src='{scry[c].get('image')}' alt='{html.escape(c)}' "
            f"title='{html.escape(c)}' loading='lazy'>" for c in pcards)
        return f"<span class='pair'>{imgs}</span>"

    bridges = [(psig, pc) for psig, pc in pair_teams
               if classify(psig) == "bridge"]
    free = [(psig, pc) for psig, pc in pair_teams
            if classify(psig) == "free"]

    def family_bridges(fam):
        h = []
        for psig, pcards in bridges:
            touched = set()
            for k, pl in enumerate(psig):
                touched.update(lane_of_deck.get((k, pl), []))
            if {FAMILY[nm] for nm in touched} == {fam}:
                h.append(f"<div class='pairs'>{pair_span(pcards)}"
                         f"<span class='meta' style='margin-left:10px'>"
                         f"{' ↔ '.join(sorted(touched))}</span></div>")
        if h:
            return ("<p class='meta'>Bridges — pairs whose decks span "
                    "two of this family's cores:</p>" + "".join(h))
        return ""

    parts["core-tokens"] = gallery(tokens[1], small=True)
    parts["core-sac"] = gallery(sac[1], small=True)
    parts["core-ramp-urg"] = gallery(temur_ramp[1], small=True)
    parts["core-ramp-bg"] = gallery(golgari_ramp[1], small=True)
    parts["core-graveyard"] = gallery(graveyard[1], small=True)
    parts["core-spells"] = gallery(blue_spells[1], small=True)
    parts["core-discard"] = gallery(blue_tempo[1], small=True)
    parts["bridges-aggro"] = family_bridges("Aggro")
    parts["bridges-green"] = family_bridges("Green")
    parts["bridges-blue"] = family_bridges("Blue")

    # --- how the cores group ------------------------------------------
    shared = []
    for i in range(len(lanes)):
        for j in range(i + 1, len(lanes)):
            si, ci = lanes[i]
            sj, cj = lanes[j]
            common = [(k, si[k]) for k in range(len(si)) if si[k] == sj[k]]
            if common:
                shared.append((f"{mana(colors_of(ci))} {core_name(ci)}",
                               f"{mana(colors_of(cj))} {core_name(cj)}",
                               common))
    parts["cores-shared"] = "\n".join(
        f"<p class='meta'>{n1} and {n2} share "
        + ", ".join(deck_link(k, pl) for k, pl in common) + "</p>"
        for n1, n2, common in shared)

    # --- the map ------------------------------------------------------
    def svg_pips(cl, x, y):
        return "".join(
            f"<image href='https://svgs.scryfall.io/card-symbols/{s}.svg' "
            f"x='{x + i * 15}' y='{y}' width='13' height='13'/>"
            for i, s in enumerate(cl))

    def node(x, y, cl, name):
        w = 26 + max(len(cl) * 15, len(name) * 8)
        return (f"<rect x='{x - w // 2}' y='{y - 20}' width='{w}' "
                f"height='40' rx='9' fill='#fff' stroke='#999'/>"
                + svg_pips(cl, x - (len(cl) * 15) // 2, y - 14)
                + f"<text x='{x}' y='{y + 13}' text-anchor='middle' "
                f"font-size='13' font-family='-apple-system,sans-serif' "
                f"fill='#1a1a1a'>{name}</text>")

    def region(x, y, w, h, fill, label):
        return (f"<rect x='{x}' y='{y}' width='{w}' height='{h}' rx='14' "
                f"fill='{fill}'/><text x='{x + 12}' y='{y + 20}' "
                f"font-size='11' font-family='-apple-system,sans-serif' "
                f"letter-spacing='.08em' fill='#8a8a8a'>{label}</text>")

    def node_cards(x, y, cl, name, cards):
        cols = 3
        rows = (len(cards) + cols - 1) // cols
        w = 14 + cols * 46
        h = 30 + rows * 66
        s = [f"<rect x='{x}' y='{y}' width='{w}' height='{h}' rx='9' "
             f"fill='#fff' stroke='#999'/>"]
        s.append(svg_pips(cl, x + 10, y + 9))
        s.append(f"<text x='{x + 14 + len(cl) * 15}' y='{y + 20}' "
                 f"font-size='13' font-family='-apple-system,sans-serif' "
                 f"fill='#1a1a1a'>{name}</text>")
        for i, c in enumerate(sorted(cards)):
            img = scry[c].get("image")
            cx = x + 8 + (i % cols) * 46
            cy = y + 28 + (i // cols) * 66
            s.append(f"<image href='{img}' x='{cx}' y='{cy}' "
                     f"width='44' height='62'><title>{html.escape(c)}"
                     f"</title></image>")
        return "".join(s), h

    # three family regions, six sub-archetype nodes (the two ramps
    # merged), and each family's non-rectangle pairs placed inside it
    def pairs_strip(x, y, w, prs):
        rows = len(prs)
        h = 26 + rows * 68
        s = [f"<rect x='{x}' y='{y}' width='{w}' height='{h}' rx='9' "
             f"fill='none' stroke='#aaa' stroke-dasharray='4 3'/>",
             f"<text x='{x + 10}' y='{y + 16}' font-size='11' "
             f"font-family='-apple-system,sans-serif' fill='#8a8a8a'>"
             f"PAIRS</text>"]
        for r, (psig, pcards) in enumerate(prs):
            for j, c in enumerate(sorted(pcards)):
                img = scry[c].get("image")
                s.append(f"<image href='{img}' x='{x + 8 + j * 46}' "
                         f"y='{y + 22 + r * 68}' width='44' height='62'>"
                         f"<title>{html.escape(c)}</title></image>")
        return "".join(s), h

    def pair_family(psig):
        touched = set()
        for k, pl in enumerate(psig):
            touched.update(lane_of_deck.get((k, pl), []))
        fams = {FAMILY[nm] for nm in touched}
        assert len(fams) == 1, (psig, fams)
        return fams.pop()

    by_fam_pairs = {"Aggro": [], "Green": [], "Blue": []}
    for t in sorted(pair_teams, key=lambda t: t[1]):
        if classify(t[0]) != "free":
            by_fam_pairs[pair_family(t[0])].append(t)

    ramp_cards = sorted(temur_ramp[1] + golgari_ramp[1])
    col_defs = [
        ("RED", "#f7ebe8",
         [("WR", "Tokens", tokens[1]), ("BR", "Sac", sac[1])],
         by_fam_pairs["Aggro"]),
        ("GREEN", "#ebf3e8",
         [(colors_of(ramp_cards), "Ramp", ramp_cards),
          ("BG", "Graveyard", graveyard[1])],
         by_fam_pairs["Green"]),
        ("BLUE", "#e8eff6",
         [("UR", "Spells", blue_spells[1]),
          ("U", "Looting", blue_tempo[1])],
         by_fam_pairs["Blue"]),
    ]
    body, col_heights = [], []
    for i, (lab, fill, nodes, prs) in enumerate(col_defs):
        x = 30 + i * 226
        y = 34
        for cl, nm, cards in nodes:
            ns, h = node_cards(x, y, cl, nm, cards)
            body.append(ns)
            y += h + 24
        if prs:
            ps, ph = pairs_strip(x, y, 168, prs)
            body.append(ps)
            y += ph
        col_heights.append(y + 14)
    H = max(col_heights)
    svg = [f"<svg viewBox='0 0 680 {H + 12}' style='max-width:680px;"
           "width:100%;margin:16px 0'>"]
    for i, (lab, fill, _, _) in enumerate(col_defs):
        svg.append(region(6 + i * 226, 6, 216, H, fill, lab))
    svg += body
    svg.append("</svg>")
    parts["map"] = "".join(svg)

    # --- categorizing the pairs ---------------------------------------
    deck_core_lab = {}
    for lsig, lcards in lanes:
        nm = core_name(lcards)
        cl = colors_of(lcards)
        for k, pl in enumerate(lsig):
            deck_core_lab.setdefault((k, pl), []).append(
                f"{mana(cl)}&thinsp;{nm}")

    def short_link(k, pl):
        url = url_map.get((drafts[k].name, pl))
        lab = html.escape(pl)
        dd = f" data-deck='{k}:{html.escape(pl)}'"
        return (f'<a href="{url}"{dd}>{lab}</a>' if url
                else f'<a{dd}>{lab}</a>')

    def card_link(c):
        img = scry[c].get("image") or ""
        url = "https://scryfall.com/search?q=" + quote(f'!"{c}"')
        return (f"<a href='{url}' data-img='{html.escape(img)}'>"
                f"{html.escape(c)}</a>")

    def coreless_label(k, pl):
        """Affiliation of a no-core deck. Every core-less deck that
        holds any team at all is a Rectangles deck (Arason's bonds
        lean Sac, but the deck is non-creature tokens to the bone);
        a deck with no teams (FOOMP) gets nothing."""
        if any(psig[k] == pl for psig, _ in pair_teams):
            return "Rectangles"
        return None

    def owner_cell(k, pl):
        labs = deck_core_lab.get((k, pl))
        if labs:
            return " / ".join(labs)
        nm = coreless_label(k, pl)
        return f"<i>{nm}</i>" if nm else f"<i>{short_link(k, pl)}</i>"

    def sat_core(psig):
        for lsig, lcards in lanes:
            if sum(a == b for a, b in zip(psig, lsig)) >= 2:
                return core_name(lcards)
        return ""

    CAT_RANK = {"satellite": 0, "bridge": 1, "free": 2}
    prows = sorted(pair_teams,
                   key=lambda t: (CAT_RANK[classify(t[0])],
                                  sat_core(t[0]), t[1]))
    pt = ["<table class='pairtab'><tr><th>Pair</th>"
          "<th>Draft 1</th><th>Draft 2</th><th>Draft 3</th></tr>"]
    for psig, pcards in prows:
        pair_cell = "<br>".join(card_link(c) for c in pcards)
        cells = "".join(f"<td>{owner_cell(k, pl)}</td>"
                        for k, pl in enumerate(psig))
        pt.append(f"<tr><td>{pair_cell}</td>{cells}</tr>")
    pt.append("</table>")
    parts["pair-table"] = "\n".join(pt)

    parts["rectangles-gallery"] = ("<div class='pairs'>" + "".join(
        pair_span(pcards) for psig, pcards in free) + "</div>")

    # --- pairs-by-lane-affiliation components for the Pairs section --
    # here core-less decks show their drafter's name (the Rectangles
    # concept isn't introduced yet at this point in the essay)
    def pre_rect_cell(k, pl):
        labs = deck_core_lab.get((k, pl))
        return (" / ".join(labs) if labs
                else f"<i>{short_link(k, pl)}</i>")

    nonfree = [(psig, pc) for psig, pc in pair_teams
               if classify(psig) != "free"]
    full_lane = [(psig, pc) for psig, pc in nonfree
                 if all((k, pl) in lane_of_deck
                        for k, pl in enumerate(psig))]
    partial = [t for t in nonfree if t not in full_lane]
    assert len(full_lane) == 2 and len(partial) == 5, \
        (len(full_lane), len(partial))  # post.md hardcodes 2 and 5

    def pair_rows_gallery(rows):
        h = []
        for psig, pcards in sorted(rows, key=lambda t: t[1]):
            lab = " &middot; ".join(pre_rect_cell(k, pl)
                                    for k, pl in enumerate(psig))
            h.append(f"<div class='pairs'>{pair_span(pcards)}"
                     f"<span class='meta' style='margin-left:10px'>"
                     f"{lab}</span></div>")
        return "".join(h)

    parts["pairs-in-lane"] = pair_rows_gallery(full_lane)
    parts["pairs-contested"] = pair_rows_gallery(partial)

    rt = ["<table class='pairtab'><tr><th>Pair</th><th>Draft 1</th>"
          "<th>Draft 2</th><th>Draft 3</th></tr>"]
    for psig, pcards in sorted(free, key=lambda t: t[1]):
        pair_cell = "<br>".join(card_link(c) for c in pcards)
        cells = "".join(f"<td>{pre_rect_cell(k, pl)}</td>"
                        for k, pl in enumerate(psig))
        rt.append(f"<tr><td>{pair_cell}</td>{cells}</tr>")
    rt.append("</table>")
    parts["pairs-rect-table"] = "\n".join(rt)

    # selector over the stay-home pairs, one pane per macro lane
    # (relies on the delegated click handler the lanes viewer installs)
    FAM_BTN = [("Aggro", "R", "Red Aggro"),
               ("Green", "G", "Green"),
               ("Blue", "U", "Blue")]
    fv = ["<div class='explorer'><div class='sidebar'>"]
    fpanes = []
    for i, (fam, cl, lab) in enumerate(FAM_BTN):
        on = " class='on'" if i == 0 else ""
        fv.append(f"<button{on} data-group='fampairs' "
                  f"data-show='fp-{i}'>{mana(cl)} {lab}</button>")
        hid = "" if i == 0 else " hidden"
        fpanes.append(f"<div data-pane='fampairs' id='fp-{i}'{hid}>"
                      + pair_rows_gallery(by_fam_pairs[fam]) + "</div>")
    fv.append("</div><div>")
    fv += fpanes
    fv.append("</div></div>")
    parts["fam-pairs-viewer"] = "".join(fv)

    # cross-pod shared cards: each rectangles deck vs the macro lanes
    bd_all = deck_sets(owners)
    fam_sets = {}
    for lsig, lc in lanes:
        fm = FAMILY[core_name(lc)]
        for kk, pp in enumerate(lsig):
            fam_sets.setdefault((kk, pp), set()).add(fm)
    SEG = [("Aggro", "#cf7f6b"), ("Green", "#7fa878"),
           ("Blue", "#7f9cc9")]
    hc = []
    for k, d in enumerate(drafts):
        hc.append(f"<div class='sbh'>{d.name}</div>")
        hc.append("<div class='vchart'>")
        for pl in d.players:
            if (k, pl) in lane_of_deck or not coreless_label(k, pl):
                continue
            cnt = Counter()
            # count shared cards with each lane family's decks
            for k2, d2 in enumerate(drafts):
                if k2 == k:
                    continue
                for p2 in d2.players:
                    n = len(bd_all[(k, pl)] & bd_all[(k2, p2)])
                    for fm in fam_sets.get((k2, p2), ()):
                        cnt[fm] += n
            bars = "".join(
                "<div style='display:flex;flex-direction:column;"
                "align-items:center;justify-content:flex-end'>"
                f"<span class='vnum'>{cnt[fm] or ''}</span>"
                f"<div class='vbar' style='height:{cnt[fm] * 8}px;"
                f"background:{col};width:16px' title='{fm}: {cnt[fm]} "
                f"shared cards'></div></div>"
                for fm, col in SEG)
            hc.append(
                "<div class='vcol'>"
                "<div style='display:flex;align-items:flex-end;gap:3px;"
                "height:100%'>" + bars + "</div>"
                f"<span class='vlab'>{html.escape(pl)}</span></div>")
        hc.append("</div>")
    parts["rect-compete-chart"] = "\n".join(hc)

    # --- which lanes do the no-lane decks fit into? -------------------
    def pair_label(psig):
        for lsig, lcards in lanes:
            if sum(a == b for a, b in zip(psig, lsig)) >= 2:
                return core_name(lcards)
        if classify(psig) == "bridge":
            per = set()
            for k, pl in enumerate(psig):
                per.update(lane_of_deck.get((k, pl), []))
            return "/".join(sorted({FAMILY[n] for n in per}))
        return "Rectangles"

    lane_own_x = {(k, pl) for lsig, _ in lanes
                  for k, pl in enumerate(lsig)}
    no_lane_x = [(k, pl) for k, d in enumerate(drafts)
                 for pl in d.players if (k, pl) not in lane_own_x]
    ct = ["<table><tr><th>Deck</th><th>Their pairs say</th></tr>"]
    for k, pl in no_lane_x:
        my = [pair_label(psig) for psig, _ in pair_teams if psig[k] == pl]
        cnt = Counter(my)
        fit = ", ".join(f"{l} ×{n}" if n > 1 else l
                        for l, n in cnt.most_common()) or "—"
        ct.append(f"<tr><td>{drafts[k].name} {html.escape(pl)}</td>"
                  f"<td>{fit}</td></tr>")
    ct.append("</table>")
    parts["coreless-table"] = "\n".join(ct)

    # --- the seat chart -----------------------------------------------
    def seat_lean(k, pl):
        """Strongest non-free affiliation of a core-less deck."""
        labs = Counter()
        for psig, _ in pair_teams:
            if psig[k] != pl:
                continue
            for lsig, lcards in lanes:
                if sum(a == b for a, b in zip(psig, lsig)) >= 2:
                    labs[core_name(lcards)] += 1
                    break
            else:
                if classify(psig) != "free":
                    for kk, ppl in enumerate(psig):
                        for nm in lane_of_deck.get((kk, ppl), []):
                            labs[nm] += 1
        return labs.most_common(1)[0][0] if labs else None

    FAM_ORDER = ["Aggro", "Green", "Blue"]
    sc = ["<div class='seats'>"]
    for k, d in enumerate(drafts):
        col = [f"<div><div class='sbh'>{d.name}</div>"]
        # seats stay in sheet (draft) order; color carries the lane
        for pl in d.players:
            cores_own = lane_of_deck.get((k, pl), [])
            nm = html.escape(pl)
            if cores_own:
                fam = FAMILY[cores_own[0]]
                lab = " + ".join(deck_core_lab[(k, pl)])
                col.append(f"<div class='seat s{fam}'>{nm}"
                           f"<span>{lab}</span></div>")
            elif coreless_label(k, pl):
                lean = seat_lean(k, pl)
                lab = (f"Rectangles &middot; leans "
                       f"{mana(CORE_COLORS[lean])}&thinsp;{lean}"
                       if lean else "Rectangles")
                col.append(f"<div class='seat sRect'>{nm}"
                           f"<span>{lab}</span></div>")
            else:
                col.append(f"<div class='seat sFoomp'>{nm}"
                           f"<span>Gyruda companion — no packages"
                           f"</span></div>")
        col.append("</div>")
        sc.append("".join(col))
    sc.append("</div>")
    parts["seat-chart"] = "\n".join(sc)

    # --- bar graph: cards in teams by color identity + pair gallery ---
    ident = Counter()
    for _, cards in groups:
        cl = colors_of(cards)
        if len(cl) >= 2:
            ident[cl] += len(cards)
    mx = max(ident.values())
    tc = ["<div class='vchart'>"]
    for cl, n in sorted(ident.items(), key=lambda x: -x[1]):
        hpx = round(n / mx * 130)
        tc.append(f"<div class='vcol'><span class='vnum'>{n}</span>"
                  f"<div class='vbar' style='height:{hpx}px'></div>"
                  f"<span class='vlab'>{mana(cl)}</span></div>")
    tc.append("</div>")
    parts["teams-chart"] = "\n".join(tc)

    pair_units = [sorted(cards) for _, cards in groups if len(cards) == 2]
    by_cl = {}
    for pr in pair_units:
        by_cl.setdefault(colors_of(pr), []).append(pr)
    order = sorted(by_cl, key=lambda k: -len(by_cl[k]))
    tabs, panes = [], []
    for cl in order:
        tabs.append(f"<button id='pt-{cl}' onclick=\"showPairs('{cl}')\">"
                    f"{mana(cl)} {len(by_cl[cl])}</button>")
        pane = [f"<div class='pairs' id='pp-{cl}' hidden>"]
        for pr in by_cl[cl]:
            imgs = "".join(
                f"<img src='{scry[c].get('image')}' "
                f"alt='{html.escape(c)}' title='{html.escape(c)}' "
                f"loading='lazy'>" for c in pr)
            pane.append(f"<span class='pair'>{imgs}</span>")
        pane.append("</div>")
        panes.append("".join(pane))
    cls = ",".join(f"'{c}'" for c in order)
    parts["pair-tabs"] = (
        f"<div class='tabs'>{''.join(tabs)}</div>"
        + "\n".join(panes)
        + f"""<script>
const pairGroups = [{cls}];
function showPairs(g) {{
  for (const x of pairGroups) {{
    document.getElementById('pp-' + x).hidden = (x !== g);
    document.getElementById('pt-' + x).classList.toggle('on', x === g);
  }}
}}
showPairs('{order[0]}');
</script>""")

    # --- the most original decks --------------------------------------
    # originality, weak sense: how much of each maindeck was communal
    team_count = {(k, pl): sum(len(cards) for sig, cards in groups
                               if sig[k] == pl)
                  for k, d in enumerate(drafts) for pl in d.players}
    assert [dk for dk, n in team_count.items() if n == 0] \
        == [(2, "FOOMP")]  # post.md: exactly one package-less deck
    tdist = Counter(team_count.values())
    td = ["<div class='vchart'>"]
    mxt = max(tdist.values())
    for s in range(0, max(tdist) + 1):
        n = tdist.get(s, 0)
        hpx = round(n / mxt * 130) if n else 0
        bar = (f"<div class='vbar' style='height:{hpx}px'></div>"
               if n else "<div style='height:0'></div>")
        td.append(f"<div class='vcol'><span class='vnum'>{n or ''}"
                  f"</span>{bar}<span class='vlab'>{s}</span></div>")
    td.append("</div>")
    parts["teams-per-deck"] = "\n".join(td)

    # originality, strong sense: unique ensembles.
    # Yorion-sized maindecks (35+ nonland) get more room for unique
    # pairs than 40-card decks, and not linearly — exclude them from
    # the scoring rather than trying to normalize.
    ue = unique_ensembles(owners)
    by_deck_all = deck_sets(owners)
    yorion = {dk for dk, cards in by_deck_all.items() if len(cards) >= 30}
    lane_own_u = {(k, pl) for lsig, _ in lanes
                  for k, pl in enumerate(lsig)}
    sizes = {dk: len(s) for dk, s in ue.items() if dk not in yorion}
    avg_lane = (sum(v for dk, v in sizes.items() if dk in lane_own_u)
                / sum(1 for dk in sizes if dk in lane_own_u))
    avg_free = (sum(v for dk, v in sizes.items() if dk not in lane_own_u)
                / sum(1 for dk in sizes if dk not in lane_own_u))
    # post.md hardcodes these; assert so copy drift gets caught
    assert (round(avg_lane, 1), round(avg_free, 1)) == (9.9, 12.5), \
        (avg_lane, avg_free)
    hist = Counter(sizes.values())
    oh = ["<div class='vchart'>"]
    mxh = max(hist.values())
    for s in range(min(hist), max(hist) + 1):
        n = hist.get(s, 0)
        hpx = round(n / mxh * 130) if n else 0
        bar = (f"<div class='vbar' style='height:{hpx}px'></div>"
               if n else "<div style='height:0'></div>")
        oh.append(f"<div class='vcol'><span class='vnum'>{n or ''}"
                  f"</span>{bar}<span class='vlab'>{s}</span></div>")
    oh.append("</div>")
    parts["originality-hist"] = "\n".join(oh)
    max_size = max(sizes.values())
    leaders = sorted(dk for dk in sizes if sizes[dk] == max_size)
    assert max_size == 16 and len(leaders) == 2, (max_size, leaders)
    assert leaders == [(0, "Mark"), (1, "tox 🍉")], leaders
    parts["ensemble-mark"] = gallery(ue[(0, "Mark")], shuffle=True)
    parts["ensemble-tox"] = gallery(ue[(1, "tox 🍉")], shuffle=True)
    cbn = (2, "ColdBrewNate")
    assert len(ue[cbn]) == 18 and len(by_deck_all[cbn]) == 37, \
        (len(ue[cbn]), len(by_deck_all[cbn]))  # post.md hardcodes
    parts["ensemble-cbn"] = gallery(ue[cbn], shuffle=True)

    # bangers: all-3-pod cards that joined no package
    in_pkg = {c for _, cards in groups for c in cards}
    bangers = sorted(c for c, sig in owners.items()
                     if None not in sig and c not in in_pkg)
    assert len(bangers) == 48, len(bangers)  # post.md hardcodes
    by_bc = {}
    for c in bangers:
        by_bc.setdefault(colors_of([c]), []).append(c)
    order_bc = sorted(by_bc, key=canon_key)
    bt = ["<div class='tabs'>"]
    bpanes = []
    for i, cl in enumerate(order_bc):
        on = " class='on'" if i == 0 else ""
        bt.append(f"<button{on} data-group='bangers' "
                  f"data-show='bg-{i}'>{mana(cl)} {len(by_bc[cl])}"
                  f"</button>")
        hid = "" if i == 0 else " hidden"
        bpanes.append(f"<div data-pane='bangers' id='bg-{i}'{hid}>"
                      + gallery(by_bc[cl]) + "</div>")
    bt.append("</div>")
    parts["bangers-gallery"] = "".join(bt) + "\n".join(bpanes)
    blade = (0, "BladeTheKing")
    assert len(ue[blade]) == 13 and len(by_deck_all[blade]) == 35, \
        (len(ue[blade]), len(by_deck_all[blade]))  # post.md hardcodes
    parts["originality-blade"] = (
        f"<p>{deck_link(*blade)}: {len(ue[blade])} of its "
        f"{len(by_deck_all[blade])} nonland cards form a group that "
        "exists nowhere else:</p>" + gallery(ue[blade], shuffle=True))

    # --- the FOOMP section --------------------------------------------
    by_deck = deck_sets(owners)
    zero_team = [(k, pl) for k, d in enumerate(drafts)
                 for pl in d.players
                 if not any(sig[k] == pl for sig, _ in groups)]
    assert zero_team == [(2, "FOOMP")], zero_team  # post.md names FOOMP
    k, pl = zero_team[0]
    url = url_map.get((drafts[k].name, pl))
    parts["foomp-link"] = (
        f'<a href="{url}" data-deck="{k}:FOOMP">sealeddeck</a>'
        if url else "")
    parts["foomp-gallery"] = gallery(by_deck[(k, pl)], shuffle=True)

    # inline tokens: {{deck:N:Player}} (full link) and
    # {{drafter:N:Player}} (name-only link), both deck-hoverable
    def deck_token(arg, short=False):
        num, dpl = arg.split(":", 1)
        return deck_link(int(num) - 1, dpl, short=short)
    parts["deck:"] = deck_token
    parts["drafter:"] = lambda arg: deck_token(arg, short=True)

    # the deckImgs data the shared [data-deck] hover layer reads
    all_decks = deck_sets(owners)
    deck_imgs = {f"{dk}:{dpl}": [scry[c].get("image")
                                 for c in sorted(cards)
                                 if scry[c].get("image")]
                 for (dk, dpl), cards in all_decks.items()}
    global SCRIPTS
    SCRIPTS = ("<script>const deckImgs = "
               + json.dumps(deck_imgs, separators=(",", ":"))
               + ";</script>")

    return parts
