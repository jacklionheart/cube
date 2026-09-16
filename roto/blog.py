"""Render out/blog-post.html: the shareable blog-post version.

The lane report (report.py) stays as the internal/background analysis;
this one is structured as an essay for readers. Prose is Jack's —
sections marked TODO are scaffold only.

Usage: python3 blog.py
"""

import html
import pathlib
from urllib.parse import quote

from packages import (card_colors, deck_sets, load, load_scryfall,
                      maindeck_owners, nonland_owners, signature_groups)
from roto_summary import load_decks

HERE = pathlib.Path(__file__).parent

CSS = """
body { font-family: Charter, Georgia, 'Times New Roman', serif;
       font-size: 19px; line-height: 1.65; color: #1a1a1a;
       max-width: 680px; margin: 56px auto 120px; padding: 0 20px; }
h1 { font-size: 28px; line-height: 1.25; margin: 0 0 6px; }
h2 { font-size: 21px; margin: 48px 0 8px; }
h3 { font-size: 17px; margin: 30px 0 4px; }
a { color: inherit; text-decoration: underline;
    text-decoration-color: #b8b8b8; text-underline-offset: 2px; }
a:hover { text-decoration-color: #1a1a1a; }
.meta { font-family: -apple-system, 'Segoe UI', Helvetica, sans-serif;
        font-size: 14px; color: #6b6b6b; margin: 2px 0 14px; }
.mana { width: 13px; height: 13px; vertical-align: -1px; margin-right: 1px; }
.cards { display: flex; flex-wrap: wrap; gap: 8px; margin: 14px 0 18px; }
.cards img { width: 160px; border-radius: 6px; }
.todo { background: #fff8dc; padding: 2px 6px; font-family: -apple-system,
        'Segoe UI', Helvetica, sans-serif; font-size: 13px; }
.vchart { display: flex; align-items: flex-end; gap: 18px;
         height: 190px; margin: 18px 0 6px; font-family: -apple-system,
         'Segoe UI', Helvetica, sans-serif; font-size: 13px; }
.vcol { display: flex; flex-direction: column; align-items: center;
        justify-content: flex-end; height: 100%; }
.vbar { width: 34px; background: #7d93a8; border-radius: 4px 4px 0 0; }
.vnum { color: #444; margin-bottom: 3px; }
.vlab { margin-top: 6px; }
.tabs { margin: 10px 0 4px; }
.tabs button { background: none; border: none; cursor: pointer;
               font: 14px -apple-system, 'Segoe UI', Helvetica, sans-serif;
               color: #6b6b6b; padding: 4px 10px 5px 6px;
               border-bottom: 2px solid transparent; }
.tabs button.on { color: #1a1a1a; border-bottom-color: #1a1a1a; }
.pairs { margin: 8px 0 16px; }
.pair { display: inline-flex; gap: 2px; margin: 3px 10px 3px 0; }
.pair img { width: 128px; border-radius: 5px; }
[hidden] { display: none !important; }
.explorer { display: grid; grid-template-columns: 110px 1fr; gap: 20px;
            margin: 24px 0 8px; }
.sidebar button { display: block; width: 100%; text-align: left;
    background: none; border: none; cursor: pointer; padding: 6px 8px;
    font: 15px -apple-system, 'Segoe UI', Helvetica, sans-serif;
    color: #6b6b6b; border-left: 2px solid transparent; }
.sidebar button.on { color: #1a1a1a; border-left-color: #1a1a1a; }
#hovercard { position: fixed; display: none; z-index: 10;
             pointer-events: none; }
#hovercard img { width: 250px; border-radius: 12px;
                 box-shadow: 0 6px 18px rgba(0,0,0,.28); }
"""

HOVER_JS = """<div id='hovercard'><img alt=''></div>
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
</script>"""


CANON = (["W", "U", "B", "R", "G"]
         + ["WU", "UB", "BR", "RG", "WG", "WB", "UR", "BG", "WR", "UG"]
         + ["WUG", "WUB", "UBR", "BRG", "WRG",
            "WBG", "WUR", "UBG", "WBR", "URG"]
         + ["WUBR", "WUBG", "WURG", "WBRG", "UBRG", "WUBRG", "C"])


def canon_key(cl):
    return CANON.index(cl) if cl in CANON else len(CANON)


def mana(letters):
    syms = [s for s in letters if s in "WUBRGC"] or ["C"]
    return "".join(
        f"<img class='mana' src='https://svgs.scryfall.io/card-symbols/"
        f"{s}.svg' alt='{s}'>" for s in syms)


def main():
    drafts, cube, decks = load()
    scry = load_scryfall()
    owners = nonland_owners(maindeck_owners(drafts, cube, decks), scry)
    colors = {c: card_colors(c, scry) for c in owners}
    groups = signature_groups(owners, min_size=2)
    lanes = [(sig, sorted(cards)) for sig, cards in groups
             if len(cards) >= 3]

    def colors_of(cards):
        u = set()
        for c in cards:
            u |= colors.get(c, set())
        return "".join(x for x in "WUBRG" if x in u) or "C"

    def gallery(cards):
        h = ["<div class='cards'>"]
        for c in sorted(cards):
            h.append(f"<img src='{scry[c].get('image')}' "
                     f"alt='{html.escape(c)}' title='{html.escape(c)}' "
                     f"loading='lazy'>")
        h.append("</div>")
        return "".join(h)

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
        h = [gallery(cards)]
        sats = satellites(sig)
        if sats:
            h.append("<p class='meta'>Satellites — pairs kept by two of "
                     "this lane's three decks:</p><div class='pairs'>")
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
    tokens = lane_by_colors("WR")
    sac = lane_by_colors("BR")
    temur_ramp = lane_by_colors("URG")
    golgari_ramp = lane_by_colors("BG")
    graveyard = lane_by_colors("G")
    blue_spells = lane_by_colors("UR")
    blue_tempo = lane_by_colors("U")

    out = [f"<meta charset='utf-8'><title>Three Rotos, One Cube</title>"
           f"<style>{CSS}</style>"]
    out.append("<h1>Three Rotos, One Cube</h1>")
    out.append("<p class='meta'><span class='todo'>TODO: byline / intro "
               "hook in Jack's voice</span></p>")

    out.append(
        "<p>Call two nonland cards a <b>team</b> if they were maindecked "
        "together — in the same deck — in all three pods. Three "
        "different drafters, three different decks, same two cards "
        "ending up shoulder to shoulder every time.</p>")

    # --- explorer module: Pairs / Bangers / Lanes ---------------------
    from collections import Counter as _Ct
    pair_units_x = [sorted(cards) for _, cards in groups
                    if len(cards) == 2]
    team_cards_x = {c for _, cards in groups for c in cards}
    bangers_x = sorted(c for c, sig in owners.items()
                       if None not in sig and c not in team_cards_x)

    def tabbed(gid, items, label_fn, pane_fn):
        h = ["<div class='tabs'>"]
        for i, it in enumerate(items):
            on = " class='on'" if i == 0 else ""
            h.append(f"<button{on} data-group='{gid}' "
                     f"data-show='{gid}-p{i}'>{label_fn(it)}</button>")
        h.append("</div>")
        for i, it in enumerate(items):
            hid = "" if i == 0 else " hidden"
            h.append(f"<div data-pane='{gid}' id='{gid}-p{i}'{hid}>"
                     f"{pane_fn(it)}</div>")
        return "".join(h)

    def pair_pane(prs):
        s = ["<div class='pairs'>"]
        for pr in prs:
            imgs = "".join(
                f"<img src='{scry[c].get('image')}' "
                f"alt='{html.escape(c)}' title='{html.escape(c)}' "
                f"loading='lazy'>" for c in pr)
            s.append(f"<span class='pair'>{imgs}</span>")
        s.append("</div>")
        return "".join(s)

    pair_by_cl = {}
    for pr in pair_units_x:
        pair_by_cl.setdefault(colors_of(pr), []).append(pr)
    pair_tabs = sorted(pair_by_cl, key=canon_key)

    bang_by_cl = {}
    for c in bangers_x:
        bang_by_cl.setdefault(colors_of([c]), []).append(c)
    bang_tabs = sorted(bang_by_cl, key=canon_key)

    lanes_sorted = sorted(lanes, key=lambda x: (canon_key(colors_of(x[1])), -len(x[1])))

    sets = [
        ("pairs", f"Pairs ({len(pair_units_x)})",
         tabbed("tp", pair_tabs,
                lambda cl: f"{mana(cl)} {len(pair_by_cl[cl])}",
                lambda cl: pair_pane(pair_by_cl[cl]))),
        ("bangers", f"Bangers ({len(bangers_x)})",
         tabbed("tb", bang_tabs,
                lambda cl: f"{mana(cl)} {len(bang_by_cl[cl])}",
                lambda cl: gallery(bang_by_cl[cl]))),
        ("lanes", f"Lanes ({len(lanes)})",
         tabbed("tl", lanes_sorted,
                lambda ln: f"{mana(colors_of(ln[1]))} {len(ln[1])}",
                lambda ln: gallery(ln[1]))),
    ]
    out.append("<div class='explorer'><div class='sidebar'>")
    for i, (sid, label, _) in enumerate(sets):
        on = " class='on'" if i == 0 else ""
        out.append(f"<button{on} data-group='sets' "
                   f"data-show='set-{sid}'>{label}</button>")
    out.append("</div><div>")
    for i, (sid, _, body) in enumerate(sets):
        hid = "" if i == 0 else " hidden"
        out.append(f"<div data-pane='sets' id='set-{sid}'{hid}>"
                   f"{body}</div>")
    out.append("</div></div>")
    out.append("<p class='meta'>Pairs: exactly-two-card teams. Bangers: "
               "nonland cards maindecked in all three pods that belong "
               "to no team. Lanes: the teams of three or more.</p>")
    out.append("""<script>
document.addEventListener('click', e => {
  const b = e.target.closest('button[data-show]');
  if (!b) return;
  const g = b.dataset.group;
  document.querySelectorAll(`[data-pane='${g}']`).forEach(
    el => el.hidden = (el.id !== b.dataset.show));
  document.querySelectorAll(`button[data-group='${g}']`).forEach(
    x => x.classList.toggle('on', x === b));
});
</script>""")

    out.append(
        "<p>If you ask for teams of three or more cards, the data hands "
        f"back {len(lanes)} of them — and they sort themselves into "
        "three families:</p>")

    LANE_NAME = {"WR": "Tokens", "BR": "Sac", "URG": "Temur Ramp",
                 "BG": "Golgari Ramp", "G": "Graveyard",
                 "UR": "Control", "U": "Tempo"}
    FAMILY = {"Tokens": "Aggro", "Sac": "Aggro", "Temur Ramp": "Green",
              "Golgari Ramp": "Green", "Graveyard": "Green",
              "Control": "Blue", "Tempo": "Blue"}
    lane_of_deck = {}
    for lsig, lcards in lanes:
        nm = LANE_NAME[colors_of(lcards)]
        for k, pl in enumerate(lsig):
            lane_of_deck.setdefault((k, pl), []).append(nm)

    def classify(psig):
        for lsig, _ in lanes:
            if sum(a == b for a, b in zip(psig, lsig)) >= 2:
                return "satellite"
        touched = set()
        for k, pl in enumerate(psig):
            touched.update(lane_of_deck.get((k, pl), []))
        return "bridge" if len(touched) >= 2 else "free"

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
                    "two of this family's lanes:</p>" + "".join(h))
        return ""

    out.append("<h2>Two Mardu aggro decks</h2>")
    out.append(f"<h3>{mana('WR')} Boros Tokens</h3>")
    out.append(lane_block(tokens))
    out.append(f"<h3>{mana('BR')} Rakdos Sac</h3>")
    out.append(lane_block(sac))
    out.append(family_bridges("Aggro"))

    out.append("<h2>Three green decks</h2>")
    out.append(f"<h3>{mana('URG')} Five-color Temur Ramp</h3>")
    out.append(lane_block(temur_ramp))
    out.append(f"<h3>{mana('BG')} Five-color Golgari Ramp</h3>")
    out.append(lane_block(golgari_ramp))
    out.append(f"<h3>{mana('G')} Golgari Graveyard</h3>")
    out.append(lane_block(graveyard))
    out.append(family_bridges("Green"))

    out.append("<h2>Two blue decks</h2>")
    out.append(f"<h3>{mana('UR')} Control</h3>")
    out.append(lane_block(blue_spells))
    out.append(f"<h3>{mana('U')} Tempo</h3>")
    out.append(lane_block(blue_tempo))
    out.append(family_bridges("Blue"))

    out.append("<h2>The free pairs</h2>")
    out.append("<p class='meta'><span class='todo'>TODO: framing — "
               "pairs living outside the lane system; the proto-lanes."
               "</span></p><div class='pairs'>")
    for psig, pcards in free:
        out.append(pair_span(pcards))
    out.append("</div>")

    # --- bar graph: cards in teams by color identity + pair gallery ---
    from collections import Counter
    ident = Counter()
    for _, cards in groups:
        cl = colors_of(cards)
        if len(cl) >= 2:
            ident[cl] += len(cards)
    out.append("<h2>Where the teams live</h2>")
    out.append("<p class='meta'><span class='todo'>TODO: framing "
               "sentence</span></p>")
    mx = max(ident.values())
    out.append("<div class='vchart'>")
    for cl, n in sorted(ident.items(), key=lambda x: -x[1]):
        hpx = round(n / mx * 130)
        out.append(f"<div class='vcol'><span class='vnum'>{n}</span>"
                   f"<div class='vbar' style='height:{hpx}px'></div>"
                   f"<span class='vlab'>{mana(cl)}</span></div>")
    out.append("</div>")
    out.append("<p class='meta'>Cards in teams of each color identity "
               "(teams of two or more colors).</p>")

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
    out.append("<p class='meta'>The two-card teams, by color:</p>")
    out.append(f"<div class='tabs'>{''.join(tabs)}</div>")
    out += panes
    cls = ",".join(f"'{c}'" for c in order)
    out.append(f"""<script>
const pairGroups = [{cls}];
function showPairs(g) {{
  for (const x of pairGroups) {{
    document.getElementById('pp-' + x).hidden = (x !== g);
    document.getElementById('pt-' + x).classList.toggle('on', x === g);
  }}
}}
showPairs('{order[0]}');
</script>""")

    # --- the FOOMP section --------------------------------------------
    by_deck = deck_sets(owners)
    zero_team = []
    for k, d in enumerate(drafts):
        for pl in d.players:
            if not any(sig[k] == pl for sig, _ in groups):
                zero_team.append((k, pl))
    _, _, links = load_decks(HERE / "decks.tsv", cube)
    url_map = {(dr, pl): u for dr, pl, kind, u, used in links
               if used == "Y" and "manual-" not in u}
    for k, pl in zero_team:
        dcards = by_deck[(k, pl)]
        url = url_map.get((drafts[k].name, pl))
        link = (f'<a href="{url}">sealeddeck</a>' if url else "")
        out.append(f"<h2>The {html.escape(pl)} deck</h2>")
        out.append("<p class='meta'><span class='todo'>TODO: "
                   "celebration prose</span></p>")
        out.append(
            f"<p>Every other drafter — all 27 of them — built a deck "
            f"containing at least one team: some two-card combination "
            f"that also showed up, together, in both other pods. "
            f"{html.escape(pl)} is the exception. Not one pair of "
            f"nonland cards in this deck was ever maindecked together "
            f"in both other pods. Twenty-eight decks, one true "
            f"original. {link}</p>")
        out.append(gallery(dcards))

    out.append("<p class='meta'><span class='todo'>TODO: continue — "
               "next sections from Jack's outline</span></p>")
    out.append(HOVER_JS)

    dest = HERE / "out" / "blog-post.html"
    dest.parent.mkdir(exist_ok=True)
    dest.write_text("\n".join(out))
    print(dest)


if __name__ == "__main__":
    main()
