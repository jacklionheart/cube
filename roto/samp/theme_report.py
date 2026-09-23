"""Theme & absence report for the samp s4 pods (essay-style HTML).

Sections:
  1. Auto theme tags (regex over oracle/type lines; themes.tsv overrides
     when it exists) applied to every qualifying team.
  2. Theme league table — which themes win, at the majority (>1/2) and
     "often" (>=1/3-ish) bars. Theme WR counts each hosting deck once.
  3. Color linearity — does a color's play show up as repeated groups?
     (Jack's hypothesis: blue wins without forming groups.)
  4. What is NOT played — never-drafted, drafted-but-never-maindecked,
     drafted-often-rarely-maindecked; themes with cards but no teams.
  5. Threshold sensitivity: maximal team counts at >=5/6/7 of 13.

Usage: python3 theme_report.py [out.html]
"""

import html
import json
import pathlib
import re
import sys

import refresh
from lane_compare import (CSS, GUILDS, WUBRG, card_link, colors_of, families,
                          guild, is_land, mana, mine, support)
from roto_summary import MAIN_ZONES, load_decks, parse_draft
from auto_tags import TAG_RULES, tags_for

HERE = pathlib.Path(__file__).parent


def load_all():
    drafts, cube, seen = [], [], set()
    for n in refresh.SOURCES:
        d, c = parse_draft(HERE / "sources" / f"{refresh.slugify(n)}.xlsx", n)
        drafts.append(d)
        for e in c:
            if e[0] not in seen:
                seen.add(e[0])
                cube.append(e)
    availability = {}
    for n in refresh.SOURCES:
        _, c = parse_draft(HERE / "sources" / f"{refresh.slugify(n)}.xlsx", n)
        for e in c:
            availability[e[0]] = availability.get(e[0], 0) + 1
    real_decks, _, _ = load_decks(HERE / "decks.tsv", cube)
    scry = json.loads((HERE / "scryfall.json").read_text())
    # per-card deck sets (nonland, maindeck) + per-card drafted/md counts
    card_decks, drafted, mained = {}, {}, {}
    for k, d in enumerate(drafts):
        for card, p in d.picks.items():
            drafted[card] = drafted.get(card, 0) + 1
            deck = real_decks.get((d.name, p.player))
            zone = deck.get(card) if deck else None
            if zone is None and card.endswith(" 2") and deck:
                zone = deck.get(card[:-2].strip())
            if zone in MAIN_ZONES:
                mained[card] = mained.get(card, 0) + 1
                if not is_land(card, scry):
                    card_decks.setdefault(card, set()).add((k, p.player))
    return drafts, cube, availability, scry, card_decks, drafted, mained



def group_stats(groups, drafts):
    """[(S, ds, themes, colors, deck-instances)] with per-group host W/L."""
    out = []
    for S, ds in groups:
        by_draft = dict(sorted(ds))
        w = l = 0
        for k, p in sorted(by_draft.items()):
            dw, dl = drafts[k].records.get(p, (0, 0))
            w, l = w + dw, l + dl
        out.append((S, ds, set(by_draft.items()), w, l))
    return out


def theme_table(maximal, drafts, scry):
    """theme -> {groups, cards, decks(set), w, l} — each hosting deck
    counted once per theme."""
    themes = {}
    for S, ds in maximal:
        gtags = {}
        for c in S:
            for t in tags_for(c, scry):
                gtags[t] = gtags.get(t, 0) + 1
        # a group carries a theme when >=2 of its cards do (pairs: both)
        carried = [t for t, n in gtags.items() if n >= min(2, len(S))]
        by_draft = dict(sorted(ds))
        for t in carried:
            e = themes.setdefault(t, {"groups": 0, "cards": set(), "decks": set()})
            e["groups"] += 1
            e["cards"] |= set(S)
            e["decks"] |= set(by_draft.items())
    rows = []
    for t, e in themes.items():
        w = l = 0
        for k, p in sorted(e["decks"]):
            dw, dl = drafts[k].records.get(p, (0, 0))
            w, l = w + dw, l + dl
        rows.append((t, e["groups"], len(e["cards"]), len(e["decks"]),
                     w, l, w / (w + l) if w + l else None))
    rows.sort(key=lambda r: (-(r[6] or 0), -r[1]))
    return rows


def main():
    out_path = pathlib.Path(sys.argv[1] if len(sys.argv) > 1
                            else HERE / "out" / "theme-report.html")
    drafts, cube, availability, scry, card_decks, drafted, mained = load_all()
    n_known = len(drafts)

    mx = {sup: [(S, ds) for S, ds in mine(card_decks, sup, 2)]
          for sup in (5, 6, 7)}

    out = [f"<meta charset='utf-8'><title>Samp Roto s4 — Themes & Absences"
           f"</title><style>{CSS}</style>"]
    out.append("<h1>Samp Roto s4 — Themes, Win Rates, and What Nobody Plays</h1>")
    out.append("<p class='meta'>129/129 real maindecks · nonland teams · "
               "theme tags are mechanical regex over oracle text "
               "(hand labels in themes.tsv override when present) · "
               "sources: 13 pod sheets + read-the-bones + sealeddeck</p>")

    # 1. thresholds
    out.append("<h2>Loosening the bar: majority vs often</h2>")
    out.append("<table><tr><th>Bar</th><th>Maximal teams</th>"
               "<th>Families</th><th>Biggest team</th></tr>")
    for sup in (7, 6, 5):
        m = mx[sup]
        f = families(m)
        big = max((len(S) for S, _ in m), default=0)
        label = {7: ">1/2 (majority)", 6: "6/13", 5: "≥5/13 (~often)"}[sup]
        out.append(f"<tr><td>≥{sup} of 13 — {label}</td><td>{len(m)}</td>"
                   f"<td>{len(f)}</td><td>{big} cards</td></tr>")
    out.append("</table>")

    # 2. theme league tables at 7 and 5
    for sup, label in ((7, "majority (≥7/13)"), (5, "often (≥5/13)")):
        rows = theme_table(mx[sup], drafts, scry)
        out.append(f"<h2>Theme league at the {label} bar</h2>")
        out.append("<p class='meta'>Theme WR counts each hosting deck once "
                   "(a deck hosting three tagged groups isn't triple-counted). "
                   "A team carries a theme when ≥2 of its cards do.</p>")
        out.append("<table><tr><th>Theme</th><th>Teams</th><th>Cards</th>"
                   "<th>Host decks</th><th>W–L</th><th>Win rate</th></tr>")
        for t, g, c, dks, w, l, wr in rows:
            wrs = f"{wr:.1%}" if wr is not None else "—"
            out.append(f"<tr><td>{t}</td><td>{g}</td><td>{c}</td>"
                       f"<td>{dks}</td><td>{w}–{l}</td><td>{wrs}</td></tr>")
        out.append("</table>")

    # 3. color linearity
    out.append("<h2>Color linearity: does winning show up as teams?</h2>")
    out.append("<p class='meta'>Grouped share = of a color's maindecked "
               "nonland cards, how many appear in at least one maximal team. "
               "Low share + high WR = wins without repeated packages.</p>")
    in_group7 = {c for S, _ in mx[7] for c in S}
    in_group5 = {c for S, _ in mx[5] for c in S}
    out.append("<table><tr><th>Color</th><th>Maindecked cards</th>"
               "<th>In a team (≥7/13)</th><th>In a team (≥5/13)</th>"
               "<th>Deck-weighted WR</th></tr>")
    for col in WUBRG:
        cs = [c for c in card_decks
              if col in (scry.get(c.replace(" 2", "", 1)) or scry.get(c) or {})
              .get("colors", [])]
        if not cs:
            continue
        w = l = 0
        for c in cs:
            for k, p in card_decks[c]:
                dw, dl = drafts[k].records.get(p, (0, 0))
                w, l = w + dw, l + dl
        g7 = sum(1 for c in cs if c in in_group7)
        g5 = sum(1 for c in cs if c in in_group5)
        out.append(f"<tr><td>{mana(col)} {guild(col)}</td><td>{len(cs)}</td>"
                   f"<td>{g7} ({g7 / len(cs):.0%})</td>"
                   f"<td>{g5} ({g5 / len(cs):.0%})</td>"
                   f"<td>{w / (w + l):.1%}</td></tr>")
    out.append("</table>")

    # 4. what is not played
    out.append("<h2>What nobody plays</h2>")
    never_drafted = sorted(
        (c for c, _, _ in cube if c not in drafted
         and not c.endswith(" 2") and not is_land(c, scry)),
        key=lambda c: -availability.get(c, 0))
    out.append(f"<h3>Never drafted ({len(never_drafted)})</h3>")
    out.append("<p class='meta'>Available in N pods, taken in zero.</p>")
    out.append("<p>" + " · ".join(
        f"{card_link(c)} ({availability.get(c, 0)})"
        for c in never_drafted) + "</p>")

    never_mained = sorted(
        ((c, drafted[c]) for c in drafted
         if c not in mained and not is_land(c, scry)),
        key=lambda x: -x[1])
    out.append(f"<h3>Drafted but never maindecked "
               f"({len(never_mained)} nonland cards)</h3>")
    out.append("<p class='meta'>Someone spent a roto pick; no known deck "
               "ever ran it. Sorted by times drafted.</p>")
    out.append("<p>" + " · ".join(
        f"{card_link(c)} (drafted {n}×)" for c, n in never_mained[:60])
        + ("</p>" if len(never_mained) <= 60
           else f" · … +{len(never_mained) - 60} more</p>"))

    low_rate = sorted(
        ((c, mained.get(c, 0), drafted[c]) for c in drafted
         if drafted[c] >= 6 and not is_land(c, scry)
         and mained.get(c, 0) / drafted[c] <= 0.5),
        key=lambda x: x[1] / x[2])
    out.append(f"<h3>Drafted often, benched half the time "
               f"({len(low_rate)})</h3>")
    out.append("<p class='meta'>Taken in ≥6 pods, maindecked in ≤half of "
               "those decks — the format's most overrated picks?</p>")
    out.append("<p>" + " · ".join(
        f"{card_link(c)} ({m}/{n})" for c, m, n in low_rate) + "</p>")

    # themes with cards but no teams
    all_tagged = {}
    for c in card_decks:
        for t in tags_for(c, scry):
            all_tagged.setdefault(t, set()).add(c)
    themed7 = {t for t, *_ in theme_table(mx[7], drafts, scry)}
    themed5 = {t for t, *_ in theme_table(mx[5], drafts, scry)}
    missing = [(t, len(cs)) for t, cs in sorted(all_tagged.items())
               if t not in themed5]
    weak = [(t, len(cs)) for t, cs in sorted(all_tagged.items())
            if t in themed5 and t not in themed7]
    out.append("<h3>Themes that never form teams</h3>")
    out.append("<p class='meta'>Tag exists on maindecked cards, but no "
               "qualifying team carries it even at the ≥5/13 bar"
               + ("." if missing else " — none; every tag teams up somewhere.")
               + "</p>")
    if missing:
        out.append("<p>" + " · ".join(f"{t} ({n} cards)" for t, n in missing)
                   + "</p>")
    if weak:
        out.append("<p class='meta'>Only at the loose bar (≥5/13, not ≥7): "
                   + ", ".join(f"{t} ({n})" for t, n in weak) + "</p>")

    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text("\n".join(out))
    print(out_path)


if __name__ == "__main__":
    main()
