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

from packages import (card_colors, deck_sets, flex_packages, load,
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
h1 { font-size: 34px; line-height: 1.2; margin: 0 0 8px; }
h2 { font-size: 25px; margin: 64px 0 10px; }
h3 { font-size: 20px; margin: 40px 0 6px; }
h4 { margin-top: 30px; font-family: -apple-system, 'Segoe UI', Helvetica, sans-serif;
     font-size: 12px; letter-spacing: .08em; text-transform: uppercase;
     color: #6b6b6b; margin: 26px 0 6px; font-weight: 600; }
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
.lane { border-top: 1px solid #e6e6e6; margin-top: 60px; padding-top: 26px; }
.num { font-family: -apple-system, 'Segoe UI', Helvetica, sans-serif;
       font-size: 13px; color: #9a9a9a; font-weight: 400;
       margin-right: 6px; }
.cards { display: flex; flex-wrap: wrap; gap: 10px; margin: 22px 0 26px;
         justify-content: center;
         width: min(960px, calc(100vw - 40px));
         margin-left: 50%; transform: translateX(-50%); }
.cards img { width: 176px; border-radius: 8px; }
.bangers img { width: 148px; }
.flex-list { font-size: 16px; margin: 6px 0 14px; padding-left: 22px; }
.flex-list li { margin: 3px 0; }
.kept { color: #6b6b6b; font-size: .88em; }
"""


def chip(card, colors):
    return html.escape(card)


def main():
    drafts, cube, decks = load()
    owners = maindeck_owners(drafts, cube, decks)
    groups = signature_groups(owners)
    flex = flex_packages(groups, owners)
    by_deck = deck_sets(owners)
    themes = load_themes()
    scry = load_scryfall()
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
           "<p class='meta'>A <b>Lane</b> is a core of 3+ cards maindecked "
           "together in all three drafts — by three different people — plus "
           "its flex orbit (cards that rode with the full core in two of "
           "the three decks). Deck links go to sealeddeck.tech.</p>"]

    # -- Section 1: the lanes ------------------------------------------
    out.append("<h2>The lanes</h2>")
    for gi, (sig, cards) in enumerate(groups):
        e = flex[gi]
        out.append(f"<div class='lane'><h3><span class='num'>P{gi + 1}</span>{lane_theme(gi)} "
                   f"<span class='kept'>{colors_of(cards)} · "
                   f"core {len(cards)}</span></h3>")
        own = []
        for k, p in enumerate(sig):
            own.append(f"{drafts[k].name}: {deck_link(k, p)}")
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
                kept = [deck_link(k2, sig[k2], f"{drafts[k2].name} {sig[k2]}")
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
    out.append("<h2>Bangers</h2>")
    out.append(f"<p class='meta'>{len(ubiq)} nonland cards were maindecked "
               "in every pod yet belong to no lane core — good enough to "
               "play everywhere, tied to nothing. A P# tag means the card "
               "is in that lane's "
               "flex orbit; untagged cards float free.</p>")
    group_order = ["W", "U", "B", "R", "G", "Multi", "C"]
    by_grp = {g: [] for g in group_order}
    for c in ubiq:
        cc = colors[c]
        g = ("Multi" if len(cc) > 1 else next(iter(cc)) if cc else "C")
        by_grp[g].append(c)
    for g in group_order:
        if not by_grp[g]:
            continue
        out.append(f"<h4>{g} ({len(by_grp[g])})</h4>"
                   f"<div class='cards bangers'>")
        for c in by_grp[g]:
            img = scry[c].get("image")
            tag = (f"<div class='kept' style='text-align:center'>"
                   f"P{flex_of[c] + 1} flex</div>" if c in flex_of else "")
            out.append(f"<div><img src='{img}' alt='{html.escape(c)}' "
                       f"title='{html.escape(c)}' loading='lazy'>{tag}</div>")
        out.append("</div>")

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
                   f"{deck_link(k, p)} <span class='kept'>"
                   f"{colors_of(cards)}</span></h3>")
        out.append(f"<p class='meta'>{len(distinct)} of {len(cards)} "
                   f"nonbasic cards sit outside every lane (in no core or "
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
        return (f"<tr{cls}><td>{label}</td><td>{status}</td>"
                f"<td>{lanestr}</td></tr>")

    out.append("<style>.absent td { background: #fbdcdc; }</style>")
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
        out.append(f"<tr><td>{g}</td>{''.join(cells)}</tr>")
    out.append("</table>")

    out.append("<h4>The never-drafted cards, by color</h4>")
    for g in groups_order:
        cs = [c for c in nd if group_of(c) == g]
        if cs:
            out.append(f"<p class='meta' style='margin:6px 0 0'>{g}:</p>"
                       + "".join(chip(c, colors) for c in cs))

    dest = HERE / "out" / "lane-report.html"
    dest.parent.mkdir(exist_ok=True)
    dest.write_text("\n".join(out))
    print(dest)


if __name__ == "__main__":
    main()
