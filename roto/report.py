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
body { font-family: -apple-system, Segoe UI, Helvetica, Arial, sans-serif;
       margin: 24px auto; max-width: 1080px; color: #222; }
h1 { font-size: 24px; } h2 { font-size: 20px; margin: 30px 0 8px; }
h3 { font-size: 16px; margin: 18px 0 4px; }
h4 { font-size: 13px; margin: 10px 0 4px; }
table { border-collapse: collapse; margin: 8px 0 16px; }
th, td { border: 1px solid #ccc; padding: 4px 10px; font-size: 13px;
         text-align: left; vertical-align: top; }
th { background: #434343; color: #fff; }
a { color: #1a56a0; text-decoration: none; }
a:hover { text-decoration: underline; }
.meta { color: #555; font-size: 13px; margin: 2px 0 10px; }
.lane { border-top: 3px solid #434343; margin-top: 26px; padding-top: 6px; }
.theme { display: inline-block; background: #434343; color: #fff;
         border-radius: 8px; padding: 0 8px; font-size: 12px; }
.cards { display: flex; flex-wrap: wrap; gap: 6px; margin: 8px 0; }
.cards img { width: 160px; border-radius: 7px; }
.flex-list { font-size: 13px; margin: 4px 0 12px; }
.flex-list li { margin: 2px 0; }
.chip { display: inline-block; border: 1px solid #bbb; border-radius: 10px;
        padding: 1px 8px; margin: 2px; font-size: 12px; }
.kept { color: #555; }
"""


def chip(card, colors):
    cs = colors.get(card, set())
    if len(cs) == 1:
        fill = COLOR_FILLS[next(iter(cs))]
    elif cs:
        fill = COLOR_FILLS["multi"]
    else:
        fill = COLOR_FILLS["C"]
    return (f'<span class="chip" style="background:#{fill}">'
            f'{html.escape(card)}</span>')


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
    out.append("<h2>1. The Lanes</h2>")
    for gi, (sig, cards) in enumerate(groups):
        e = flex[gi]
        out.append(f"<div class='lane'><h3>P{gi + 1} "
                   f"<span class='theme'>{lane_theme(gi)}</span> "
                   f"<span class='kept'>{colors_of(cards)} · "
                   f"core {len(cards)}</span></h3>")
        own = []
        for k, p in enumerate(sig):
            w, l = drafts[k].records.get(p, (0, 0))
            own.append(f"{drafts[k].name}: {deck_link(k, p)} ({w}–{l})")
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
    out.append("<h2>2. Two lanes per player</h2>")
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
    out.append("<h2>3. Everywhere, but in no core</h2>")
    out.append(f"<p class='meta'>{len(ubiq)} nonland cards were maindecked "
               "in every pod yet belong to no lane core — the universal "
               "role-players. A P# tag means the card is in that lane's "
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
        items = []
        for c in by_grp[g]:
            tag = (f" <span class='kept'>P{flex_of[c] + 1}</span>"
                   if c in flex_of else "")
            items.append(f"{chip(c, colors)}{tag}")
        out.append(f"<p class='meta'><b>{g}</b> ({len(by_grp[g])})</p>"
                   f"<p>{' '.join(items)}</p>")

    # -- Section 4: decks that carved their own lanes ------------------
    claimed = set()
    for gi, (sig, cards) in enumerate(groups):
        claimed |= set(cards)
        for bucket in flex[gi]["flex"]:
            claimed |= set(bucket)
    no_lane = [(k, p) for k, d in enumerate(drafts) for p in d.players
               if (k, p) not in lanes_of]
    out.append("<h2>4. The decks that carved their own lanes</h2>")
    out.append("<p class='meta'>No lane runs through these decks — their "
               "distinctive cards below appear in no lane core or flex.</p>")
    for k, p in no_lane:
        cards = by_deck[(k, p)]
        distinct = sorted(cards - claimed)
        w, l = drafts[k].records.get(p, (0, 0))
        out.append(f"<div class='lane'><h3>{drafts[k].name}: "
                   f"{deck_link(k, p)} <span class='kept'>"
                   f"{colors_of(cards)} · {w}–{l}</span></h3>")
        out.append(f"<p class='meta'>{len(distinct)} of {len(cards)} "
                   f"nonbasic cards sit outside every lane (in no core or "
                   f"flex — though other decks may also run them):</p>")
        out += [chip(c, colors) for c in distinct]
        out.append("</div>")

    # -- Section 4: what's missing? ------------------------------------
    out.append("<h2>5. What's missing?</h2>")
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
