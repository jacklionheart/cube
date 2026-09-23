"""Render out/samp-report.html: the samp s4 analysis report.

Centerpiece: the Locks — nonland cards maindecked by EVERY player who
drafted them (literally always, any exposure), as a color-tabbed card
gallery with drafted counts and drafters' win rates, plus opening
charts about that population. Teams (the co-maindeck groups) stay in
the spreadsheet — they're the sheet's Teams tabs. Ends with the bench
(high-profile cards that never start) with the drafted-WR caveat.
Scaffold text is minimal by design — the prose voice is Jack's.

Usage: python3 report.py
"""

import html
import pathlib
from collections import Counter

from lane_compare import CSS as BASE_CSS, guild, is_land, mana
from roto_summary import MAIN_ZONES, load_decks


def scaled_lock_budgets(n_available_drafts):
    """~90%-inclusion budgets for a run over many drafts (the s4 report
    keeps the defaults below: budget=2, oncolor_budget=1)."""
    budget = max(2, round(0.10 * n_available_drafts))
    return budget, max(1, budget // 2)


def compute_locks(cube, availability, scry, drafts, drafted, mained,
                  min_avail=5, budget=2, oncolor_budget=1,
                  decks_tsv=None):
    """Locks: maindecked in all but at most `budget` of the available
    pods, and in all but at most `oncolor_budget` of the decks that
    could actually cast the card (the benching deck's cost-colors cover
    the card's colors). Off-color benches and undrafted pods only eat
    the overall budget. Returns (locks, excuse) where excuse[c]
    describes the forgiven misses. `decks_tsv` defaults to the s4
    decks.tsv; pass decks_all.tsv for an all-drafts run."""
    decks, _, _ = load_decks(
        decks_tsv or pathlib.Path(__file__).parent / "decks.tsv", cube)

    def colors(card):
        base = card[:-2].strip() if card.endswith(" 2") else card
        return set((scry.get(base) or scry.get(card) or {})
                   .get("colors") or [])

    deck_colors = {}
    for key, cards in decks.items():
        u = set()
        for c2, z in cards.items():
            if z in MAIN_ZONES:
                u |= colors(c2)
        deck_colors[key] = u

    locks, excuse = [], {}
    for card in {c for c, _, _ in cube}:
        if is_land(card, scry) or availability.get(card, 0) < min_avail:
            continue
        hard = soft = md = taken = 0
        for d in drafts:
            pk = d.picks.get(card)
            if pk is None:
                continue
            taken += 1
            deck = decks.get((d.name, pk.player))
            if deck is None:
                continue  # unknown deck: no evidence either way
            z = deck.get(card) or (deck.get(card[:-2].strip())
                                   if card.endswith(" 2") else None)
            if z in MAIN_ZONES:
                md += 1
            elif colors(card) <= deck_colors[(d.name, pk.player)]:
                hard += 1
            else:
                soft += 1
        undrafted = availability[card] - taken
        if (hard <= oncolor_budget and hard + soft + undrafted <= budget
                and md >= 1):
            locks.append(card)
            bits = []
            if hard:
                bits.append(f"on-color bench {hard}×")
            if soft:
                bits.append(f"off-color bench {soft}×")
            if undrafted:
                bits.append(f"undrafted {undrafted}×")
            excuse[card] = " · ".join(bits)
    return locks, excuse

# chart/tab/gallery rules from the LoL report, absent from lane_compare's CSS
CSS = BASE_CSS + """
h4 { font-family: -apple-system, 'Segoe UI', Helvetica, sans-serif;
     font-size: 13px; color: #777; margin: 20px 0 4px; font-weight: 600; }
.bangers img { width: 128px; }
.chart { margin: 6px 0 26px; font-family: -apple-system, 'Segoe UI',
         Helvetica, sans-serif; font-size: 13px; }
.crow { display: grid; grid-template-columns: 130px 1fr 52px;
        align-items: center; margin: 3px 0; }
.clabel { text-align: left; color: #444; }
.cbar { background: #7d93a8; height: 15px;
        border-radius: 0 4px 4px 0; display: inline-block;
        vertical-align: middle; }
.cbar1 { background: #a8b8c6; height: 9px;
         border-radius: 0 3px 3px 0; display: block; }
.cbar2 { background: #40566b; height: 9px;
         border-radius: 0 3px 3px 0; display: block; margin-top: 2px; }
.cval { color: #444; margin-left: 6px; }
.tabs { margin: 10px 0 4px; }
.tabs button { background: none; border: none; cursor: pointer;
               font: 14px -apple-system, 'Segoe UI', Helvetica, sans-serif;
               color: #6b6b6b; padding: 4px 10px 5px 6px;
               border-bottom: 2px solid transparent; }
.tabs button.on { color: #1a1a1a; border-bottom-color: #1a1a1a; }
.cards[hidden] { display: none; }
.pair { display: inline-flex; gap: 2px; }
.pair img { width: 104px; border-radius: 5px; }
.paircell { padding: 6px 10px 10px 0; }
summary { cursor: pointer; list-style-position: outside; }
summary h2 { display: inline; }
.kept { color: #6b6b6b; font-size: .88em; }
#hovercard { position: fixed; display: none; z-index: 10;
             pointer-events: none; }
#hovercard img { width: 250px; border-radius: 12px;
                 box-shadow: 0 6px 18px rgba(0,0,0,.28); }
.flex-list { font-size: 14px; margin: 6px 0 14px; padding-left: 22px;
             font-family: -apple-system, 'Segoe UI', Helvetica, sans-serif; }
.flex-list li { margin: 3px 0; }
.hosts { font-family: -apple-system, 'Segoe UI', Helvetica, sans-serif;
         font-size: 12px; color: #6b6b6b; margin-top: 2px; max-width: 230px; }
"""
from theme_report import TAG_RULES, load_all, tags_for

HERE = pathlib.Path(__file__).parent
SHEET_URL = ("https://docs.google.com/spreadsheets/d/"
             "1VcZrPKd_UypiJUpbs3CJ6-ysmBhkGapnq8VJ3duJ3cc/edit")
MIN_DRAFTED = 5  # always maindecked, with enough exposure to mean it


def barchart(title, rows, mx=None, sub=None):
    if mx is None:
        mx = max((r[1] for r in rows), default=1) or 1
    h = [f"<h4>{title}</h4>"]
    if sub:
        h.append(f"<p class='meta' style='margin:0'>{sub}</p>")
    h.append("<div class='chart'>")
    for row in rows:
        label, v = row[0], row[1]
        w = round(v / mx * 100)
        bar = f"<span class='cbar' style='width:{w}%'></span>" if v else ""
        val = (row[2] if len(row) > 2
               else f"{v:.1%}" if isinstance(v, float) else v)
        h.append(f"<div class='crow'><span class='clabel'>{label}</span>"
                 f"<span>{bar}</span><span class='cval'>{val}</span></div>")
    h.append("</div>")
    return "".join(h)


def barchart_pair(title, rows, mx, sub):
    h = [f"<h4>{title}</h4><p class='meta' style='margin:0'>{sub}</p>"
         "<div class='chart'>"]
    for label, v1, v2 in rows:
        w1, w2 = round(v1 / mx * 100), round(v2 / mx * 100)
        h.append(f"<div class='crow'><span class='clabel'>{label}</span>"
                 f"<span><span class='cbar1' style='width:{w1}%'></span>"
                 f"<span class='cbar2' style='width:{w2}%'></span></span>"
                 f"<span class='cval'>{v1}·{v2}</span></div>")
    h.append("</div>")
    return "".join(h)


def main():
    drafts, cube, availability, scry, card_decks, drafted, mained = load_all()
    import json
    images = json.loads((HERE / "images.json").read_text())
    _, _, deck_links = load_decks(HERE / "decks.tsv", cube)
    url_map = {}
    for draft, player, kind, url, used in deck_links:
        if used == "Y" and "manual-" not in url:
            url_map[(draft, player)] = url

    def deck_link(k, player):
        url = url_map.get((drafts[k].name, player))
        label = html.escape(player)
        if url:
            return (f"<a href='{url}' title='{html.escape(drafts[k].name)}'>"
                    f"{label}</a>")
        return f"{label}<span class='kept'>*</span>"

    def card_chip(c):
        from urllib.parse import quote
        base = c.replace(" 2", "", 1) if c.endswith(" 2") else c
        return (f"<a href='https://scryfall.com/search?q=!%22{quote(base)}%22'"
                f" data-img='{images.get(c, '')}'>{html.escape(c)}</a>")

    def colorgrp(c):
        base = c.replace(" 2", "", 1) if c.endswith(" 2") else c
        cs = (scry.get(base) or scry.get(c) or {}).get("colors") or []
        return "Multi" if len(cs) > 1 else (cs[0] if cs else "C")

    def drafters_record(c):
        w = l = 0
        for d in drafts:
            p = d.picks.get(c)
            if p:
                dw, dl = d.records.get(p.player, (0, 0))
                w, l = w + dw, l + dl
        return w, l

    nonland_drafted = [c for c in drafted if not is_land(c, scry)]

    locks, excuse = compute_locks(cube, availability, scry, drafts,
                                  drafted, mained,
                                  min_avail=MIN_DRAFTED)
    locks.sort(key=lambda c: (-drafted.get(c, 0), c))
    lockstats = {}
    for c in locks:
        w, l = drafters_record(c)
        lockstats[c] = (drafted[c], w, l, w / (w + l) if w + l else None)

    out = [f"<meta charset='utf-8'><title>Samp Roto s4 — Report</title>"
           f"<style>{CSS}</style>",
           "<h1>Thirteen Pods, One Cube: the Locks</h1>",
           "<p class='meta'><b>Lock</b>: a nonland card maindecked by "
           "every deck that could cast it (available in ≥5 pods; up to "
           "two misses forgiven when off-color or undrafted). <b>Bench rate</b>: maindecks ÷ drafts "
           "taken. <b>Drafters' WR</b>: the combined match record of the "
           "players who spent a roto pick on the card — sideboard games "
           "count, so it's fair to sideboard cards. Teams (card groups "
           "co-maindecked across pods) live in the "
           f"<a href='{SHEET_URL}'>spreadsheet</a>'s Teams tabs. All 13 "
           "pods, 129 of 129 real maindecks. Method and caveats at the "
           "end.</p>"]

    # -- opening charts -------------------------------------------------
    ggs = list("WUBRG") + ["Multi", "C"]
    md_any = [c for c in nonland_drafted if mained.get(c, 0)]
    d_any = Counter(colorgrp(c) for c in md_any)
    d_lock = Counter(colorgrp(c) for c in locks)
    rate = {g: (d_lock.get(g, 0) / d_any[g] if d_any.get(g) else 0)
            for g in ggs}
    top_rate = max((g for g in ggs if d_any.get(g)), key=lambda g: rate[g])
    out.append(barchart(
        f"{len(locks)} of {len(md_any)} maindecked nonland cards are Locks "
        f"({len(locks) / len(md_any):.0%}) — "
        f"{guild(top_rate) if top_rate != 'Multi' else 'Multicolor'} has "
        "the highest hit rate",
        [("Multi" if g == "Multi" else mana(g), rate[g],
          f"{rate[g]:.0%} ({d_lock.get(g, 0)} of {d_any.get(g, 0)})")
         for g in ggs],
        mx=max(rate.values()) or 1,
        sub="share of each color's maindecked nonland cards that are Locks"))

    n13 = sum(1 for c in locks if drafted[c] == 13)
    byn = Counter(drafted[c] for c in locks)
    out.append(barchart(
        f"{n13} Locks were drafted in all 13 pods — perfect records at "
        "full exposure",
        [(f"{n} drafts", byn[n]) for n in sorted(byn, reverse=True)]))

    out.append(barchart(
        "Locks by color",
        [("Multi" if g == "Multi" else mana(g), d_lock.get(g, 0),
          f"{d_lock.get(g, 0)} (of {d_any.get(g, 0)}, {rate[g]:.0%})")
         for g in ggs]))

    wr_rows = [(html.escape(c.split(",")[0]), lockstats[c][3])
               for c in sorted(locks, key=lambda c: -(lockstats[c][3] or 0))]
    out.append(barchart(
        "Being a Lock doesn't mean winning: drafters' WR across the Locks",
        wr_rows, mx=0.7,
        sub="bar scale capped at 70% · a Lock's drafters can still lose — "
        "Swords to Plowshares starts every deck and its drafters go 42%"))

    tagc = Counter(t for c in locks for t in tags_for(c, scry))
    out.append(barchart(
        "What the Locks do (mechanical tags, a card can carry several)",
        sorted(tagc.items(), key=lambda x: -x[1])))

    out.append("<p class='meta'>Source: 13 Samp Cube Roto s4 pods, "
               "summer 2026 — 129 players' decks (sealeddeck.tech links "
               "+ 5 decks transcribed from posted screenshots; 2 pods' "
               "drafts via read-the-bones).</p>")

    # -- the gallery ----------------------------------------------------
    def gallery(prefix, title, sub, cards, cap_extra=None):
        by_grp = {g: [] for g in ggs}
        for c in cards:
            by_grp[colorgrp(c)].append(c)
        present = [g for g in ggs if by_grp[g]]
        out.append(f"<details open><summary><h2>{title} "
                   f"<span class='kept'>{len(cards)} cards</span></h2>"
                   "</summary>")
        out.append(f"<p class='meta'>{sub}</p>")
        tabs = []
        for g in present:
            glabel = "Multi" if g == "Multi" else mana(g)
            tabs.append(
                f"<button id='bt-{prefix}-{g}' "
                f"onclick=\"showGrp_{prefix}('{g}')\">"
                f"{glabel} {len(by_grp[g])}</button>")
        out.append(f"<div class='tabs'>{''.join(tabs)}</div>")
        for g in present:
            vis = "" if g == present[0] else " hidden"
            out.append(f"<div class='cards bangers' "
                       f"id='bg-{prefix}-{g}'{vis}>")
            for c in sorted(by_grp[g], key=lambda c: -(lockstats[c][3] or 0)):
                n, w, l, wr = lockstats[c]
                img = images.get(c, "")
                cap = f"{n}× · {wr:.0%}" if wr is not None else f"{n}×"
                extra = cap_extra(c) if cap_extra else ""
                if extra:
                    cap += f"<br>{extra}"
                out.append(
                    f"<div><img src='{img}' alt='{html.escape(c)}' "
                    f"title='{html.escape(c)}' loading='lazy'>"
                    f"<div class='kept' style='text-align:center'>{cap}"
                    "</div></div>")
            out.append("</div>")
        grps = ",".join(f"'{g}'" for g in present)
        out.append(f"""<script>
function showGrp_{prefix}(g) {{
  for (const x of [{grps}]) {{
    document.getElementById('bg-{prefix}-' + x).hidden = (x !== g);
    document.getElementById('bt-{prefix}-' + x).classList
        .toggle('on', x === g);
  }}
}}
showGrp_{prefix}('{present[0]}');
</script></details>""")

    gallery("lk", "The Locks",
            "Maindecked by every deck that could cast them: an on-color "
            "bench disqualifies outright; up to two misses are forgiven "
            "when the benching deck's colors couldn't cover the card, or "
            "the card went undrafted. Caption: times drafted × and the "
            "drafters' combined win rate, plus any forgiven misses.",
            locks, cap_extra=lambda c: excuse.get(c) or "")


    # -- the lanes: merged 3+ card teams --------------------------------
    from lane_compare import mine, support as dsupport
    LANE_SUP = 6
    maximal3 = mine(card_decks, LANE_SUP, 3)
    # merge teams that share any card into lanes (union-find)
    parent = list(range(len(maximal3)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(len(maximal3)):
        si = set(maximal3[i][0])
        for j in range(i + 1, len(maximal3)):
            if si & set(maximal3[j][0]):
                parent[find(i)] = find(j)
    fams = {}
    for i in range(len(maximal3)):
        fams.setdefault(find(i), []).append(i)
    lanes = sorted(
        ([maximal3[i] for i in f] for f in fams.values()),
        key=lambda teams: (-len({c for S, _ in teams for c in S}),
                           sorted(teams[0][0])))

    def colors_str_of(cards):
        return "".join(x for x in "WUBRG" if any(
            x in ((scry.get(c.replace(" 2", "", 1)) or {})
                  .get("colors") or []) for c in cards)) or "C"

    out.append("<h2>The lanes</h2>")
    out.append(f"<p class='meta'>A lane is the union of all 3+ card teams "
               f"(whole set in one maindeck in ≥{LANE_SUP} of 13 pods) "
               "that share a card — teams sharing cards merge. Win rate "
               "counts each deck that hosted any of the lane's teams "
               "once. Expand a lane to see the literal teams; deck names "
               "link to sealeddeck.</p>")
    for li, teams in enumerate(lanes):
        union = sorted({c for S, _ in teams for c in S})
        freq = {c: sum(c in S for S, _ in teams) for c in union}
        all_decks = set()
        for _, ds in teams:
            all_decks |= {tuple(x) for x in dict(sorted(ds)).items()}
        w = l = 0
        for k, pl in sorted(all_decks):
            dw, dl = drafts[k].records.get(pl, (0, 0))
            w, l = w + dw, l + dl
        wr = w / (w + l) if w + l else None
        cl = colors_str_of(union)
        out.append(f"<div class='lane'><h3><span class='num'>L{li + 1}"
                   f"</span>{mana(cl)} {guild(cl)} Lane "
                   f"<span class='kept'>{len(union)} cards · "
                   f"{len(teams)} team{'s' if len(teams) != 1 else ''} · "
                   f"{wr:.0%} ({w}–{l})</span></h3>")
        out.append("<div class='cards'>")
        for c in sorted(union, key=lambda c: (-freq[c], c)):
            out.append(f"<img src='{images.get(c, '')}' "
                       f"alt='{html.escape(c)}' title='{html.escape(c)}' "
                       "loading='lazy'>")
        out.append("</div>")
        items = []
        for S, ds in sorted(teams, key=lambda t: (-dsupport(t[1]),
                                                  -len(t[0]))):
            by_draft = dict(sorted(ds))
            tw = tl = 0
            for k, pl in sorted(by_draft.items()):
                dw, dl = drafts[k].records.get(pl, (0, 0))
                tw, tl = tw + dw, tl + dl
            twr = tw / (tw + tl) if tw + tl else 0
            hosts = " · ".join(deck_link(k, pl)
                               for k, pl in sorted(by_draft.items()))
            items.append(
                f"<li>[{dsupport(ds)}/13 · {twr:.0%}] "
                + ", ".join(card_chip(c) for c in sorted(S))
                + f" <span class='kept'>— {hosts}</span></li>")
        out.append(f"<details><summary class='meta'>the "
                   f"{len(teams)} literal team"
                   f"{'s' if len(teams) != 1 else ''}</summary>"
                   f"<ul class='flex-list'>{''.join(items)}</ul></details>")
        out.append("</div>")

    # -- top pairs at three bars ----------------------------------------
    from itertools import combinations
    deck_sets = {}
    for c, ds in card_decks.items():
        for dk in ds:
            deck_sets.setdefault(dk, set()).add(c)
    pair_decks = {}
    for dk, cs in deck_sets.items():
        for a, b in combinations(sorted(cs), 2):
            pair_decks.setdefault((a, b), set()).add(dk)

    def pair_stats(pr):
        ds = pair_decks[pr]
        sup = len({k for k, _ in ds})
        w = l = 0
        for k, p in dict(sorted(ds)).items():
            dw, dl = drafts[k].records.get(p, (0, 0))
            w, l = w + dw, l + dl
        return sup, w, l, (w / (w + l) if w + l else 0)

    stats = {pr: pair_stats(pr) for pr in pair_decks}
    tops = {}
    for bar in (5, 6, 7):
        qual = [(pr, st) for pr, st in stats.items() if st[0] >= bar]
        qual.sort(key=lambda x: (-x[1][3], -x[1][0], x[0]))
        tops[bar] = qual[:10]
    out.append("<h2>The best pairs, at three evidence bars</h2>")
    out.append("<p class='meta'>Every two-card combination that shared a "
               "maindeck in ≥N of the 13 pods, ranked by the hosting "
               "decks' combined win rate. Raising the bar trades ceiling "
               "for certainty: the ≥7 column is what the format proves, "
               "the ≥5 column is what it suggests.</p>")
    out.append("<table><tr><th>≥5 of 13</th><th>≥6 of 13</th>"
               "<th>≥7 of 13</th></tr>")
    for i in range(10):
        cells = []
        for bar in (5, 6, 7):
            if i < len(tops[bar]):
                (a, b), (sup, w, l, wr) = tops[bar][i]
                imgs = "".join(
                    f"<img src='{images.get(c, '')}' "
                    f"alt='{html.escape(c)}' title='{html.escape(c)}' "
                    f"loading='lazy'>" for c in (a, b))
                hosts = " · ".join(
                    deck_link(k, pl)
                    for k, pl in sorted(dict(sorted(pair_decks[(a, b)]))
                                        .items()))
                cells.append(
                    f"<td class='paircell'><span class='pair'>{imgs}</span>"
                    f"<div class='kept'>{wr:.0%} · {sup}/13</div>"
                    f"<div class='hosts'>{hosts}</div></td>")
            else:
                cells.append("<td></td>")
        out.append("<tr>" + "".join(cells) + "</tr>")
    out.append("</table>")

    # -- the bench ------------------------------------------------------
    bench = sorted(
        ((c, mained.get(c, 0), drafted[c], *drafters_record(c))
         for c in nonland_drafted
         if drafted[c] >= 6 and mained.get(c, 0) / drafted[c] <= 0.25),
        key=lambda x: (x[1] / x[2], -x[2]))
    out.append("<h2>The bench</h2>")
    out.append("<p class='meta'>Drafted in ≥6 pods, maindecked in a "
               "quarter of those decks or fewer. Benched is not the same "
               "as bad: we can't see sideboard games, so the drafters' WR "
               "column is the fair test — a benched card whose drafters "
               "win is probably earning its pick from the board.</p>")
    out.append("<table><tr><th>Card</th><th>Maindecked</th>"
               "<th>Drafted</th><th>Drafters' W–L</th><th>Drafters' WR</th>"
               "</tr>")
    for c, m, n, w, l in bench:
        wr = w / (w + l) if w + l else None
        wrs = f"{wr:.1%}" if wr is not None else "—"
        strong = " style='font-weight:600'" if wr and wr >= 0.52 else ""
        out.append(f"<tr{strong}><td>{mana(''.join((scry.get(c) or {}).get('colors') or []) or 'C')} "
                   f"{card_chip(c)}</td><td>{m}</td><td>{n}</td>"
                   f"<td>{w}–{l}</td><td>{wrs}</td></tr>")
    out.append("</table>")

    # -- method ---------------------------------------------------------
    out.append("<h2>How this works</h2>")
    out.append(
        "<p class='meta'>Maindeck status comes from each player's "
        "submitted sealeddeck list (companion-aware — a sideboard Lurrus "
        "or Lutri counts as maindecked only when the deck satisfies its "
        "requirement); five decks were transcribed from posted "
        "screenshots and validated card-for-card against the player's 45 "
        "picks. Lands are excluded from Locks. Drafters' WR attributes a "
        "player's full match record to each card they drafted — it "
        "measures the company a card keeps, not the card alone; at n=13 "
        "pods a single 8–1 drafter moves a 13× card by about two points. "
        "Bold bench rows: benched cards whose drafters still win ≥52%. "
        f"Teams analysis: the <a href='{SHEET_URL}'>sheet</a>'s Teams "
        "tabs (whole-set co-maindeck groups, Maximal filter for "
        "non-subsets). Deck names link to sealeddeck.tech; a * marks "
        "decks transcribed from screenshots (no page to link).</p>")

    out.append("""<div id='hovercard'><img alt=''></div>
<script>
const hc = document.getElementById('hovercard');
const hcImg = hc.querySelector('img');
document.addEventListener('mouseover', e => {
  const a = e.target.closest('a[data-img]');
  if (a && a.dataset.img) { hcImg.src = a.dataset.img;
    hc.style.display = 'block'; }
  else if (!e.target.closest('#hovercard')) hc.style.display = 'none';
});
document.addEventListener('mousemove', e => {
  if (hc.style.display !== 'block') return;
  const w = 250, h = 349;
  let x = e.clientX + 16, y = e.clientY + 12;
  if (x + w > innerWidth - 8) x = e.clientX - w - 16;
  if (y + h > innerHeight - 8) y = innerHeight - h - 8;
  hc.style.left = x + 'px'; hc.style.top = Math.max(8, y) + 'px';
});
</script>""")

    out_path = HERE / "out" / "samp-report.html"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text("\n".join(out))
    print(out_path)


if __name__ == "__main__":
    main()
