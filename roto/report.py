"""Render out/merge-report.html: the by-person merge report.

One section per merging deck (both-way blenders first) showing the full
decklist as color-tinted card chips grouped by Team — for each other
draft, the cards this deck shares with each partner deck there — plus
the remainder no team claims. Lane-core cards carry a star badge,
companions a diamond. Self-contained HTML, inline CSS only.

Usage: python3 report.py
"""

import html
import pathlib

from packages import (card_colors, deck_sets, load, load_scryfall,
                      load_themes, maindeck_owners, signature_groups,
                      straddles, team_partners, theme_str)
from roto_summary import COLOR_FILLS

HERE = pathlib.Path(__file__).parent

CSS = """
body { font-family: -apple-system, Segoe UI, Helvetica, Arial, sans-serif;
       margin: 24px auto; max-width: 1080px; color: #222; }
h1 { font-size: 24px; } h2 { font-size: 19px; margin: 28px 0 6px; }
h3 { font-size: 15px; margin: 12px 0 4px; }
table { border-collapse: collapse; margin: 8px 0 16px; }
th, td { border: 1px solid #ccc; padding: 4px 10px; font-size: 13px;
         text-align: left; vertical-align: top; }
th { background: #434343; color: #fff; }
.meta { color: #555; font-size: 13px; margin: 2px 0 10px; }
.cols { display: flex; gap: 18px; align-items: flex-start; }
.col { flex: 1; min-width: 0; }
.team { border: 1px solid #ddd; border-radius: 8px; padding: 8px 10px;
        margin: 8px 0; background: #fafafa; }
.team h4 { margin: 0 0 6px; font-size: 13px; }
.theme { display: inline-block; background: #434343; color: #fff;
         border-radius: 8px; padding: 0 8px; font-size: 11px; }
.chip { display: inline-block; border: 1px solid #bbb; border-radius: 10px;
        padding: 1px 8px; margin: 2px; font-size: 12px; }
.lane-core { border: 2px solid #333; font-weight: 600; }
.deck { border-top: 3px solid #434343; margin-top: 26px; padding-top: 6px; }
.legend { font-size: 12px; color: #555; margin: 6px 0 18px; }
"""


def chip(card, colors, lane_core=False, companion=False):
    cs = colors.get(card, set())
    if len(cs) == 1:
        fill = COLOR_FILLS[next(iter(cs))]
    elif cs:
        fill = COLOR_FILLS["multi"]
    else:
        fill = COLOR_FILLS["C"]
    cls = "chip lane-core" if lane_core else "chip"
    badges = ("★" if lane_core else "") + ("◆" if companion else "")
    label = html.escape(card) + (f" {badges}" if badges else "")
    return f'<span class="{cls}" style="background:#{fill}">{label}</span>'


def main():
    drafts, cube, decks = load()
    owners = maindeck_owners(drafts, cube, decks)
    groups = signature_groups(owners)
    by_deck = deck_sets(owners)
    partners = team_partners(owners)
    merged = straddles(owners, drafts)
    themes = load_themes()
    scry = load_scryfall()
    colors = {c: card_colors(c, scry) for c, _, _ in cube}

    def colors_of(cards):
        u = set()
        for c in cards:
            u |= colors.get(c, set())
        return "".join(x for x in "WUBRG" if x in u) or "C"

    lanes_of = {}
    for gi, (sig, cards) in enumerate(groups):
        for k, p in enumerate(sig):
            lanes_of.setdefault((k, p), []).append(gi)

    def lane_label(gi):
        theme = theme_str(groups[gi][1], themes) or "—"
        return f"P{gi + 1} {theme}"

    blenders = sorted(d for d, bd in merged.items() if len(bd) == 2)
    single = sorted(d for d, bd in merged.items() if len(bd) == 1)
    all_decks = [(k, p) for k, d in enumerate(drafts) for p in d.players]
    nonmergers = [d for d in all_decks if d not in merged]
    drivers = sorted(d for d in nonmergers if d in lanes_of)
    free = sorted(d for d in nonmergers if d not in lanes_of)

    def name(deck):
        k, p = deck
        return f"{drafts[k].name}: {html.escape(p)}"

    out = [f"<meta charset='utf-8'><title>LoL Roto — Merge Report</title>"
           f"<style>{CSS}</style>",
           "<h1>Three Rotos, One Cube: the Merge Report</h1>",
           "<p class='meta'>A <b>Lane</b> is a card core maindecked by three "
           "different people, one per draft (plus its flex orbit). A "
           "<b>Team</b> is the block of cards two decks from different "
           "drafts agreed on (5+). A deck <b>merges</b> when it holds teams "
           "with two different decks of the same other draft.</p>",
           "<div class='legend'>★ lane-core card &nbsp; ◆ companion &nbsp; "
           "chip tint = card color (gold = multicolor, tan = colorless)"
           "</div>"]

    out.append("<h2>Player taxonomy</h2><table><tr><th>Category</th>"
               "<th>#</th><th>Decks</th></tr>")
    for label, ds in [("Both-way blenders", blenders),
                      ("Single-side mergers", single),
                      ("Pure lane-drivers", drivers),
                      ("Free agents", free)]:
        out.append(f"<tr><td>{label}</td><td>{len(ds)}</td>"
                   f"<td>{', '.join(name(d) for d in ds)}</td></tr>")
    out.append("</table>")

    out.append("<h2>Lanes</h2><table><tr><th>Lane</th><th>Theme</th>"
               "<th>Colors</th><th>Core #</th><th>Owners</th></tr>")
    for gi, (sig, cards) in enumerate(groups):
        ownstr = " / ".join(html.escape(p) for p in sig)
        out.append(f"<tr><td>P{gi + 1}</td>"
                   f"<td>{theme_str(cards, themes) or '—'}</td>"
                   f"<td>{colors_of(cards)}</td><td>{len(cards)}</td>"
                   f"<td>{ownstr}</td></tr>")
    out.append("</table>")

    n_cases = sum(len(bd) for bd in merged.values())
    out.append(f"<p class='meta'>{n_cases} merge cases across "
               f"{len(merged)} decks; {len(blenders)} blend in both other "
               f"drafts.</p>")

    for deck in blenders + single:
        k, p = deck
        cards = by_deck[deck]
        lane_cores = set()
        for gi in lanes_of.get(deck, []):
            lane_cores |= set(groups[gi][1])
        comps = {c for c, z in decks[(drafts[k].name, p)].items()
                 if z == "companion"}
        w, l = drafts[k].records.get(p, (0, 0))
        lanes_txt = (", ".join(lane_label(gi) for gi in lanes_of.get(deck, []))
                     or "none")
        out.append(f"<div class='deck'><h2>{name(deck)}</h2>"
                   f"<p class='meta'>{len(cards)} nonbasic maindeck cards · "
                   f"colors {colors_of(cards)} · record {w}–{l} · "
                   f"lanes: {lanes_txt}</p>")
        covered = set()
        out.append("<div class='cols'>")
        for k2 in sorted(set(range(len(drafts))) - {k}):
            out.append(f"<div class='col'><h3>Teams vs "
                       f"{drafts[k2].name}</h3>")
            plist = sorted(partners[deck].get(k2, []),
                           key=lambda x: -len(x[1]))
            if not plist:
                out.append("<p class='meta'>no teams</p>")
            for pb, core in plist:
                covered |= core
                t = theme_str(core, themes)
                badge = f" <span class='theme'>{t}</span>" if t else ""
                out.append(f"<div class='team'><h4>with "
                           f"{html.escape(pb)} [{len(core)}]{badge}</h4>")
                out += [chip(c, colors, c in lane_cores, c in comps)
                        for c in sorted(core)]
                out.append("</div>")
            out.append("</div>")
        out.append("</div>")
        rest = cards - covered
        if rest:
            out.append(f"<div class='team'><h4>Unclaimed by any team "
                       f"[{len(rest)}]</h4>")
            out += [chip(c, colors, c in lane_cores, c in comps)
                    for c in sorted(rest)]
            out.append("</div>")
        out.append("</div>")

    dest = HERE / "out" / "merge-report.html"
    dest.parent.mkdir(exist_ok=True)
    dest.write_text("\n".join(out))
    print(dest)


if __name__ == "__main__":
    main()
