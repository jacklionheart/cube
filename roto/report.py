"""Render out/lane-report.html: the lane-centric analysis report.

Section 1 presents each of the 11 Lanes: theme, core-only colors, the
three owning decks (linked to their sealeddeck pages, with match
records), the core cards as embedded Scryfall images, and the flex
orbit with links to the two decks that kept each flex card. Section 2
shows the two-lanes-per-player structure, split into same-theme pairs
(the theme pooled in one deck where other pods contested it) and
cross-theme module combinations. Section 3 lists the decks owning no
lane and their distinctive cards (maindecked cards in no lane core or
flex). Scaffold text is minimal by design — the prose voice is Jack's.

Usage: python3 report.py
"""

import html
import pathlib

from packages import (card_colors, co_maindeck_counts, deck_sets,
                      flex_packages, load,
                      nonland_owners,
                      load_scryfall, load_themes, maindeck_owners,
                      never_drafted, never_maindecked, signature_groups,
                      theme_str)
from roto_summary import COLOR_FILLS, load_decks

HERE = pathlib.Path(__file__).parent

CSS = """
body { font-family: Charter, Georgia, 'Times New Roman', serif;
       font-size: 19px; line-height: 1.65; color: #1a1a1a;
       max-width: 680px; margin: 56px auto 120px; padding: 0 20px;
       background: #fff; }
h1 { font-size: 26px; line-height: 1.25; margin: 0 0 6px; }
h2 { font-size: 21px; margin: 48px 0 8px; }
h3 { font-size: 17px; margin: 30px 0 4px; }
h4 { font-family: -apple-system, 'Segoe UI', Helvetica, sans-serif;
     font-size: 13px; color: #777; margin: 20px 0 4px; font-weight: 600; }
table { border-collapse: collapse; margin: 12px 0 20px; width: 100%;
        font-family: -apple-system, 'Segoe UI', Helvetica, sans-serif;
        font-size: 14px; }
th { text-align: left; font-weight: 600; padding: 6px 14px 6px 0;
     border-bottom: 1px solid #1a1a1a; }
td { padding: 6px 14px 6px 0; border-bottom: 1px solid #e6e6e6;
     vertical-align: top; }
a { color: inherit; text-decoration: underline;
    text-decoration-color: #b8b8b8; text-underline-offset: 2px; }
a:hover { text-decoration-color: #1a1a1a; }
.meta { font-family: -apple-system, 'Segoe UI', Helvetica, sans-serif;
        font-size: 14px; color: #6b6b6b; margin: 2px 0 14px; }
.lane { border-top: 1px solid #e6e6e6; margin-top: 40px; padding-top: 16px; }
.num { font-family: -apple-system, 'Segoe UI', Helvetica, sans-serif;
       font-size: 13px; color: #9a9a9a; font-weight: 400;
       margin-right: 6px; }
.cards { display: flex; flex-wrap: wrap; gap: 8px; margin: 14px 0 18px; }
.cards img { width: 160px; border-radius: 6px; }
.bangers img { width: 128px; }
.pairs { margin: 8px 0 16px; }
.pair { display: inline-flex; gap: 2px; margin: 3px 10px 3px 0; }
.pair img { width: 104px; border-radius: 5px; }
.mana { width: 13px; height: 13px; vertical-align: -1px;
        margin-right: 1px; }
.flex-list { font-size: 16px; margin: 6px 0 14px; padding-left: 22px; }
.flex-list li { margin: 3px 0; }
.kept { color: #6b6b6b; font-size: .88em; }
summary { cursor: pointer; list-style-position: outside; }
summary h2 { display: inline; }
.tabs { margin: 10px 0 4px; }
.tabs button { background: none; border: none; cursor: pointer;
               font: 14px -apple-system, 'Segoe UI', Helvetica, sans-serif;
               color: #6b6b6b; padding: 4px 10px 5px 6px;
               border-bottom: 2px solid transparent; }
.tabs button.on { color: #1a1a1a; border-bottom-color: #1a1a1a; }
.chart { margin: 6px 0 26px; font-family: -apple-system, 'Segoe UI',
         Helvetica, sans-serif; font-size: 13px; }
.crow { display: grid; grid-template-columns: 72px 1fr 40px;
        align-items: center; margin: 3px 0; }
.clabel { text-align: left; color: #444; }
.cbar2 { background: #40566b; height: 9px;
         border-radius: 0 3px 3px 0; display: block; margin-top: 2px; }
.cbar1 { background: #a8b8c6; height: 9px;
         border-radius: 0 3px 3px 0; display: block; }
.cbar { background: #7d93a8; height: 15px;
        border-radius: 0 4px 4px 0; display: inline-block;
        vertical-align: middle; }
.cval { color: #444; margin-left: 6px; }
"""


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


def mana(letters):
    syms = [s for s in letters if s in "WUBRGC"] or ["C"]
    return "".join(
        f"<img class='mana' src='https://svgs.scryfall.io/card-symbols/"
        f"{s}.svg' alt='{s}'>" for s in syms)


def chip(card, colors):
    from urllib.parse import quote
    return (f'<a href="https://scryfall.com/search?q=!%22{quote(card)}%22">'
            f'{html.escape(card)}</a>')


def main():
    drafts, cube, decks = load()
    scry = load_scryfall()
    owners = nonland_owners(maindeck_owners(drafts, cube, decks), scry)
    groups = signature_groups(owners)
    flex = flex_packages(groups, owners)
    by_deck = deck_sets(owners)
    themes = load_themes()
    colors = {c: card_colors(c, scry) for c, _, _ in cube}

    _, _, links = load_decks(HERE / "decks.tsv", cube)
    url_map = {}
    for draft, player, kind, url, used in links:
        if used == "Y" and "manual-" not in url:
            url_map[(draft, player)] = url

    def colors_of(cards):
        u = set()
        for c in cards:
            u |= colors.get(c, set())
        return "".join(x for x in "WUBRG" if x in u) or "C"

    def deck_link(k, p, label=None):
        label = html.escape(label if label is not None else p)
        url = url_map.get((drafts[k].name, p))
        if url:
            return f'<a href="{url}">{label}</a>'
        return f"{label} <span class='kept'>(OCR)</span>"

    def lane_theme(gi):
        return theme_str(groups[gi][1], themes) or "—"

    lanes_of = {}
    for gi, (sig, cards) in enumerate(groups):
        for k, p in enumerate(sig):
            lanes_of.setdefault((k, p), []).append(gi)

    out = [f"<meta charset='utf-8'><title>LoL Roto — Lane Report</title>"
           f"<style>{CSS}</style>",
           "<h1>Three Rotos, One Cube: the Lanes</h1>",
           "<p class='meta'><b>Lane</b>: a core of 3+ cards maindecked "
           "together in all three drafts, by three different people. "
           "<b>Flex</b>: a lane's orbit — cards that rode with the full "
           "core in two of its three decks. <b>Banger</b>: maindecked in "
           "every pod, in no lane core. Lands are ignored throughout. Deck "
           "links go to sealeddeck.tech; "
           "method and caveats at the end.</p>"]

    # -- Opening charts ------------------------------------------------
    def barchart(title, rows, unit, mx=None):
        if mx is None:
            mx = max(v for _, v in rows) or 1
        h = [f"<h4>{title}</h4><div class='chart'>"]
        for label, v in rows:
            w = round(v / mx * 100)
            bar = (f"<span class='cbar' style='width:{w}%'></span>"
                   if v else "")
            h.append(f"<div class='crow'><span class='clabel'>{label}"
                     f"</span><span>{bar}</span>"
                     f"<span class='cval'>{v}</span></div>")
        h.append(f"</div>")
        return "".join(h)

    def barchart_pair(title, rows, mx):
        h = [f"<h4>{title}</h4><p class='meta' style='margin:0'>"
             "light: maindecked in any pod · dark: in all three</p>"
             "<div class='chart'>"]
        for label, v1, v2 in rows:
            w1, w2 = round(v1 / mx * 100), round(v2 / mx * 100)
            h.append(
                f"<div class='crow'><span class='clabel'>{label}</span>"
                f"<span><span class='cbar1' style='width:{w1}%'></span>"
                f"<span class='cbar2' style='width:{w2}%'></span></span>"
                f"<span class='cval'>{v1}·{v2}</span></div>")
        h.append("</div>")
        return "".join(h)

    lane_sets = [set(colors_of(cards)) - {"C"}
                 for _, cards in groups]
    pairs10 = ["WU", "UB", "BR", "RG", "WG", "WB", "UR", "BG", "WR", "UG"]
    counts0 = [(pr, sum(1 for cs in lane_sets if set(pr) <= cs))
               for pr in pairs10]
    counts0.sort(key=lambda r: -r[1])
    rows0 = [(mana(pr), n) for pr, n in counts0]

    lane_cards = []
    for gi, (_, cards) in enumerate(groups):
        s = set(cards)
        for bucket in flex[gi]["flex"]:
            s |= set(bucket)
        lane_cards.append(s)
    touch = {}
    for dk, cards in by_deck.items():
        touch[dk] = sum(1 for s in lane_cards if s & cards)
    from collections import Counter
    tc = Counter(touch.values())
    rows1 = [(f"{n} lane{'s' if n != 1 else ''}", tc.get(n, 0))
             for n in range(0, max(tc) + 1)]

    all_lane = set().union(*lane_cards)
    laneless = [c for c, sig in owners.items()
                if any(sig) and c not in all_lane]
    def cgroup(c):
        cs = colors.get(c, set())
        return ("Multi" if len(cs) > 1
                else next(iter(cs)) if cs else "C")
    laneless3 = [c for c in laneless if None not in owners[c]]
    all_md = [c for c, sig in owners.items() if any(sig)]
    all_md3 = [c for c, sig in owners.items() if None not in sig]
    ggs = list("WUBRG") + ["Multi", "C"]

    def cdist(cards):
        d = Counter(cgroup(c) for c in cards)
        return {g: d.get(g, 0) for g in ggs}

    d_ll1, d_ll3 = cdist(laneless), cdist(laneless3)
    d_a1, d_a3 = cdist(all_md), cdist(all_md3)
    rows2 = [("Multi" if g == "Multi" else mana(g), d_ll1[g], d_ll3[g])
             for g in ggs]
    rows2a = [("Multi" if g == "Multi" else mana(g), d_a1[g], d_a3[g])
              for g in ggs]
    shared_mx = max(v for _, v, _ in rows2a)

    zeros = [pr for pr in pairs10
             if not any(set(pr) <= cs for cs in lane_sets)]
    zstr = " and ".join(guild(z) for z in zeros)
    out.append(barchart(
        f"{guild(counts0[0][0])} is the most-laned color pair; "
        f"{zstr} never made a lane", rows0, "lanes"))
    import statistics
    med = int(statistics.median(touch.values()))
    out.append(barchart(
        f"Every deck borrows from the lanes — the median deck plays cards "
        f"from {med} of them", rows1, "decks"))
    pct = round(100 * len(laneless) / len(all_md))
    out.append(barchart_pair("All maindecked cards, by color", rows2a,
                             shared_mx))
    out.append(barchart_pair(
        f"{pct}% of maindecked cards sit outside every lane "
        f"(same scale as above)", rows2, shared_mx))
    out.append("<p class='meta'>Source: three LoL cube rotisserie drafts, "
               "Sept 2026 — 28 players, all 28 maindecks "
               "(sealeddeck.tech; one deck transcribed from a screenshot)."
               "</p>")

    # -- Section 1: the lanes, grouped by theme ------------------------
    out.append("<h2>The lanes</h2>")
    theme_order = []
    for gi, (sig, cards) in enumerate(groups):
        th = lane_theme(gi)
        if th not in theme_order:
            theme_order.append(th)
    by_theme = {th: [gi for gi in range(len(groups))
                     if lane_theme(gi) == th] for th in theme_order}
    for th in theme_order:
        out.append(f"<h3 style='margin-top:44px'>{th}</h3>")
        for gi in by_theme[th]:
            sig, cards = groups[gi]
            e = flex[gi]
            cl = colors_of(cards)
            out.append(f"<div class='lane'><h3><span class='num'>"
                       f"P{gi + 1}</span>{mana(cl)} {guild(cl)} Lane "
                       f"<span class='kept'>core {len(cards)}</span></h3>")
            own = []
            for k, p in enumerate(sig):
                own.append(f"{drafts[k].name}: "
                           f"{mana(colors_of(by_deck[(k, p)]))} "
                           f"{deck_link(k, p)}")
            out.append(f"<p class='meta'>{' · '.join(own)}</p>")
            out.append("<div class='cards'>")
            for c in sorted(cards):
                img = scry[c].get("image")
                out.append(f"<img src='{img}' alt='{html.escape(c)}' "
                           f"title='{html.escape(c)}' loading='lazy'>")
            out.append("</div>")
            flex_items = []
            for k, bucket in enumerate(e["flex"]):
                for c in bucket:
                    kept = [deck_link(k2, sig[k2],
                                      f"{drafts[k2].name} {sig[k2]}")
                            for k2 in range(len(drafts)) if k2 != k]
                    flex_items.append(
                        f"<li>{chip(c, colors)} <span class='kept'>kept by "
                        f"{' and '.join(kept)}</span></li>")
            if flex_items:
                out.append(f"<h4>Flex ({len(flex_items)})</h4>"
                           f"<ul class='flex-list'>{''.join(flex_items)}</ul>")
            out.append("</div>")

    # -- Section 2: two lanes per player -------------------------------
    two_lane = {d: gis for d, gis in lanes_of.items() if len(gis) == 2}
    same = {d: g for d, g in two_lane.items()
            if lane_theme(g[0]) == lane_theme(g[1]) != "—"}
    cross = {d: g for d, g in two_lane.items() if d not in same}
    n_owners = len(lanes_of)
    out.append("<h2>Two lanes per player</h2>")
    out.append(f"<p class='meta'>{n_owners} players own a lane; "
               f"{len(two_lane)} of them own exactly two.</p>")
    for title, sub in [("Same theme twice — the theme pooled here, "
                        "contested elsewhere", same),
                       ("Cross-theme — modules combined", cross)]:
        out.append(f"<h3>{title}</h3><table><tr><th>Player</th><th>Draft"
                   "</th><th>Lanes</th></tr>")
        for (k, p), gis in sorted(sub.items(), key=lambda x: (x[0][0],
                                                              x[0][1])):
            lanestr = " + ".join(
                f"P{gi + 1} {lane_theme(gi)} ({colors_of(groups[gi][1])})"
                for gi in gis)
            out.append(f"<tr><td>{deck_link(k, p)}</td>"
                       f"<td>{drafts[k].name}</td><td>{lanestr}</td></tr>")
        out.append("</table>")

    # -- Section 3: maindecked in every pod, but in no lane core -------
    core_cards = {c for _, cards in groups for c in cards}
    flex_of = {}
    for gi, e in enumerate(flex):
        for bucket in e["flex"]:
            for c in bucket:
                flex_of.setdefault(c, gi)
    ubiq = sorted(
        c for c, sig in owners.items()
        if None not in sig and c not in core_cards
        and "Land" not in scry[c]["type_line"].split(" // ")[0])
    group_order = ["W", "U", "B", "R", "G", "Multi", "C"]
    by_grp = {g: [] for g in group_order}
    for c in ubiq:
        cc = colors[c]
        g = ("Multi" if len(cc) > 1 else next(iter(cc)) if cc else "C")
        by_grp[g].append(c)
    present = [g for g in group_order if by_grp[g]]
    out.append("<details open><summary><h2>Bangers "
               f"<span class='kept'>{len(ubiq)} cards</span></h2></summary>")
    out.append(f"<p class='meta'>Nonland cards maindecked in every pod "
               "yet in no lane core — good enough to play everywhere, "
               "tied to nothing. A P# tag means the card is in that "
               "lane's flex orbit; untagged cards float free.</p>")
    tabs = []
    for g in present:
        glabel = "Multi" if g == "Multi" else mana(g)
        tabs.append(f"<button id='bt-{g}' onclick=\"showGrp('{g}')\">"
                    f"{glabel} {len(by_grp[g])}</button>")
    out.append(f"<div class='tabs'>{''.join(tabs)}</div>")
    for g in present:
        vis = "" if g == present[0] else " hidden"
        out.append(f"<div class='cards bangers' id='bg-{g}'{vis}>")
        for c in by_grp[g]:
            img = scry[c].get("image")
            tag = (f"<div class='kept' style='text-align:center'>"
                   f"P{flex_of[c] + 1} flex</div>" if c in flex_of else "")
            out.append(f"<div><img src='{img}' alt='{html.escape(c)}' "
                       f"title='{html.escape(c)}' loading='lazy'>{tag}</div>")
        out.append("</div>")
    grps = ",".join(f"'{g}'" for g in present)
    out.append(f"""<script>
const bangerGroups = [{grps}];
function showGrp(g) {{
  for (const x of bangerGroups) {{
    document.getElementById('bg-' + x).hidden = (x !== g);
    document.getElementById('bt-' + x).classList.toggle('on', x === g);
  }}
}}
showGrp('{present[0]}');
</script></details>""")

    # -- Always-together pairs -----------------------------------------
    pairs3 = sorted(pr for pr, n in co_maindeck_counts(owners).items()
                    if n == 3)
    corder = list("WUBRG") + ["Multi", "C"]

    def combo(pr):
        g1, g2 = sorted((cgroup(pr[0]), cgroup(pr[1])),
                        key=corder.index)
        return (g1, g2)

    from collections import Counter as _C
    combo_counts = _C(combo(pr) for pr in pairs3)
    out.append("<h2>Always together</h2>")
    out.append(f"<p class='meta'>All {len(pairs3)} pairs of nonland cards "
               "that shared a maindeck in every pod — the atomic bonds the "
               "lanes are built from (pairs inside a lane count too). "
               "Counted by the colors of the two cards:</p>")
    out.append("<table><tr><th>Colors</th><th>Pairs</th></tr>")
    for (g1, g2), n in sorted(combo_counts.items(), key=lambda x: -x[1]):
        l1 = "Multi" if g1 == "Multi" else mana(g1)
        l2 = "Multi" if g2 == "Multi" else mana(g2)
        out.append(f"<tr><td>{l1} + {l2}</td><td>{n}</td></tr>")
    out.append("</table>")
    out.append(f"<details><summary class='meta'>Show all {len(pairs3)} "
               "pairs</summary>")
    by_combo = {}
    for pr in pairs3:
        by_combo.setdefault(combo(pr), []).append(pr)
    for key in sorted(by_combo, key=lambda k: -len(by_combo[k])):
        g1, g2 = key
        l1 = "Multi" if g1 == "Multi" else mana(g1)
        l2 = "Multi" if g2 == "Multi" else mana(g2)
        out.append(f"<h4>{l1} + {l2} ({len(by_combo[key])})</h4>"
                   f"<div class='pairs'>")
        for a, b in by_combo[key]:
            imgs = "".join(
                f"<img src='{scry[c].get('image')}' "
                f"alt='{html.escape(c)}' title='{html.escape(c)}' "
                f"loading='lazy'>" for c in (a, b))
            out.append(f"<span class='pair'>{imgs}</span>")
        out.append("</div>")
    out.append("</details>")

    # -- Section 4: decks that carved their own lanes ------------------
    claimed = set()
    for gi, (sig, cards) in enumerate(groups):
        claimed |= set(cards)
        for bucket in flex[gi]["flex"]:
            claimed |= set(bucket)
    no_lane = [(k, p) for k, d in enumerate(drafts) for p in d.players
               if (k, p) not in lanes_of]
    out.append("<h2>The decks that carved their own lanes</h2>")
    out.append("<p class='meta'>No lane runs through these decks — their "
               "distinctive cards below appear in no lane core or flex.</p>")
    for k, p in no_lane:
        cards = by_deck[(k, p)]
        distinct = sorted(cards - claimed)
        out.append(f"<div class='lane'><h3>{drafts[k].name}: "
                   f"{mana(colors_of(cards))} {deck_link(k, p)}</h3>")
        out.append(f"<p class='meta'>{len(distinct)} of {len(cards)} "
                   f"nonland cards sit outside every lane (in no core or "
                   f"flex — though other decks may also run them):</p>")
        out.append("<p>" + ", ".join(chip(c, colors)
                   for c in distinct) + "</p>")
        out.append("</div>")

    # -- Section 4: what's missing? ------------------------------------
    out.append("<h2>What's missing?</h2>")
    out.append("<p class='meta'>Color groups no lane occupies are the "
               "open, uncontested lanes.</p>")
    lane_colors = [(gi, set(colors_of(cards)) - {"C"})
                   for gi, (_, cards) in enumerate(groups)]

    def coverage_row(label, want):
        exact = [gi for gi, cs in lane_colors if cs == want]
        inside = [gi for gi, cs in lane_colors if want < cs]
        if exact:
            status, cls = "lane", ""
            lanes = exact + inside
        elif inside:
            status, cls = "inside a bigger lane", ""
            lanes = inside
        else:
            status, cls = "absent", " class='absent'"
            lanes = []
        lanestr = ", ".join(f"P{gi + 1} {lane_theme(gi)}" for gi in lanes)
        return (f"<tr{cls}><td>{mana(label)}</td><td>{status}</td>"
                f"<td>{lanestr}</td></tr>")

    out.append("<style>.absent td { font-weight: 600; }</style>")
    out.append("<h3>Color coverage of the lanes</h3>"
               "<table><tr><th>Colors</th><th>Status</th><th>Lanes</th></tr>")
    for c in "WUBRG":
        out.append(coverage_row(c, {c}))
    pairs = ["WU", "UB", "BR", "RG", "WG", "WB", "UR", "BG", "WR", "UG"]
    for pr in pairs:
        out.append(coverage_row(pr, set(pr)))
    out.append("</table>")

    # cut lists by color group vs cube baseline
    def group_of(c):
        cs = colors.get(c, set())
        if len(cs) == 1:
            return next(iter(cs))
        return "Multi" if cs else "C"

    all_cards = [c for c, _, _ in cube]
    nd = never_drafted(drafts, cube)
    nm = never_maindecked(drafts, cube, decks)
    nm3 = [c for c in nm if sum(c in d.picks for d in drafts) == 3]
    cols = [("Cube (baseline)", all_cards), ("Never drafted", nd),
            ("Drafted, never maindecked", nm),
            ("Taken in all 3, never maindecked", nm3)]
    groups_order = list("WUBRG") + ["Multi", "C"]

    def dist(cards):
        d = {g: 0 for g in groups_order}
        for c in cards:
            d[group_of(c)] += 1
        return d

    dists = [(label, dist(cs), len(cs)) for label, cs in cols]
    out.append("<h3>Unpicked and unplayed cards, by color</h3>")
    out.append("<p class='meta'>Share per column; compare against the "
               "cube baseline to see where the unloved cards concentrate."
               "</p>")
    out.append("<table><tr><th>Color</th>" + "".join(
        f"<th>{label}</th>" for label, _, _ in dists) + "</tr>")
    for g in groups_order:
        cells = []
        base_share = dists[0][1][g] / dists[0][2]
        for i, (label, d, n) in enumerate(dists):
            share = d[g] / n if n else 0
            hot = i > 0 and share > base_share * 1.3 and d[g] >= 3
            bar = (f"<span style='display:inline-block;background:#bcd;"
                   f"height:8px;width:{int(share * 140)}px'></span>")
            mark = " <b>↑</b>" if hot else ""
            cells.append(f"<td>{d[g]} ({share:.0%}){mark}<br>{bar}</td>")
        glabel = "Multi" if g == "Multi" else mana(g)
        out.append(f"<tr><td>{glabel}</td>{''.join(cells)}</tr>")
    out.append("</table>")

    out.append("<h4>The never-drafted cards, by color</h4>")
    for g in groups_order:
        cs = [c for c in nd if group_of(c) == g]
        if cs:
            glabel = "Multi" if g == "Multi" else mana(g)
            out.append(f"<p class='meta' style='margin:6px 0 0'>{glabel}</p>"
                       + "<p>" + ", ".join(chip(c, colors) for c in cs)
                       + "</p>")

    out.append("<h2>How this works</h2>")
    out.append(
        "<p class='meta'>Data: three rotisserie drafts of the Lords of "
        "Limited cube (Sept 2026), 45 picks x 28 players, no player in "
        "more than one pod — every recurring structure here is a "
        "cross-person replication, not one person's habit. All 28 "
        "maindecks were recovered from sealeddeck.tech links (one from a "
        "posted screenshot).</p>"
        "<p class='meta'>Maindeck rules: pool cards not listed in a deck "
        "count as sideboard (safe: every deck is either a full 40 or "
        "lists all 45 picks). A companion in the sideboard slot counts "
        "as maindecked only if the deck passes its deckbuilding "
        "requirement — e.g. one of the three Lurrus decks fails the "
        "mana-value test and is treated as a true sideboard card. "
        "Lands are excluded from the entire analysis: a lane is 3+ "
        "nonland cards.</p>"
        "<p class='meta'>Are lanes real? A permutation test keeps every "
        "player's picks and re-deals each maindeck as a random same-size "
        "subset, 2,000 times: random deckbuilding averages 3.1 lanes / "
        "10 lane-cards / largest ~4 — it never once produced this "
        "data's 34 lane-cards or a 9-card core (7 lanes: p = .003). "
        "The lane structure is deliberate deckbuilding, not a "
        "pick-pool artifact.</p>"
        "<p class='meta'>Caveats: n = 3 drafts in one community; themes "
        "are hand-labeled; win rates are deliberately absent. Everything "
        "regenerates from the draft sheets via packages.py.</p>")

    dest = HERE / "out" / "lane-report.html"
    dest.parent.mkdir(exist_ok=True)
    dest.write_text("\n".join(out))
    print(dest)


if __name__ == "__main__":
    main()
