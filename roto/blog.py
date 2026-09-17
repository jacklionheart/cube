"""Render out/blog-post.html: the shareable blog-post version.

The lane report (report.py) stays as the internal/background analysis;
this one is structured as an essay for readers. Prose is Jack's —
sections marked TODO are scaffold only.

Usage: python3 blog.py
"""

import html
import pathlib
from collections import Counter
from urllib.parse import quote

from packages import (card_colors, deck_sets, load, load_scryfall,
                      maindeck_owners, nonland_owners, signature_groups,
                      unique_ensembles)
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
table { border-collapse: collapse; margin: 14px 0 18px;
        font: 14px/1.5 -apple-system, 'Segoe UI', Helvetica, sans-serif; }
th { text-align: left; font-weight: 600; color: #6b6b6b; }
th, td { padding: 6px 16px 6px 0; border-bottom: 1px solid #e8e8e8;
         vertical-align: top; }
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
.vpanes { height: 560px; overflow-y: auto; }
.vpanes .cards img { width: 122px; }
.sbh { font: 600 11px -apple-system, 'Segoe UI', Helvetica, sans-serif;
       text-transform: uppercase; letter-spacing: .06em; color: #999;
       margin: 12px 0 2px; }
.seats { display: grid; grid-template-columns: repeat(3, 1fr);
         gap: 16px; margin: 18px 0;
         font: 13px -apple-system, 'Segoe UI', Helvetica, sans-serif; }
.seat { padding: 5px 9px; border-radius: 7px; margin: 4px 0;
        border: 1px solid transparent; }
.seat span { display: block; font-size: 11px; color: #6b6b6b; }
.sAggro { background: #f7ebe8; } .sGreen { background: #ebf3e8; }
.sBlue { background: #e8eff6; }
.sRect { background: #fff; border: 1px dashed #b5b0a8; }
.sLone { background: #f2f2f2; color: #6b6b6b; }
.adj { border: 1px dashed #c9a; }
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
    _, _, links = load_decks(HERE / "decks.tsv", cube)
    url_map = {(dr, pl): u for dr, pl, kind, u, used in links
               if used == "Y" and "manual-" not in u}

    def deck_link(k, pl):
        url = url_map.get((drafts[k].name, pl))
        lab = html.escape(f"{drafts[k].name} {pl}")
        return f'<a href="{url}">{lab}</a>' if url else lab
    lanes = [(sig, sorted(cards)) for sig, cards in groups
             if len(cards) >= 3]
    CORE_MARKERS = [("Rally at the Hornburg", "Tokens"),
                    ("Mayhem Devil", "Sac"),
                    ("Fires of Invention", "Ramp"),
                    ("Everything Pizza", "Ramp"),
                    ("Spider Spawning", "Graveyard"),
                    ("Expressive Iteration", "Spells"),
                    ("Shoreline Looter", "Discard")]

    def core_name(cards):
        for marker, nm in CORE_MARKERS:
            if marker in cards:
                return nm
        return "?"
    FAMILY = {"Tokens": "Aggro", "Sac": "Aggro", "Ramp": "Green", "Graveyard": "Green",
              "Spells": "Blue", "Discard": "Blue"}

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

    out = [f"<meta charset='utf-8'><title>Three Rotos, One Cube</title>"
           f"<style>{CSS}</style>"]
    out.append("<h1>Three Rotos, One Cube</h1>")
    out.append(
        "<p>Twenty-eight drafters. Three rotisserie pods. Five hundred "
        "and forty cards, every pick public, every deck recovered. "
        "When three groups of people who never talked to each other "
        "keep building the same things, that's not taste — that's the "
        "cube talking. <span class='todo'>[draft — make it yours]"
        "</span></p>")
    out.append(
        "<p>The goal of this essay is a 10,000-foot view of the "
        "Lords of Limited Cube — drawn not from card evaluations but "
        "from what three rotisserie pods actually built. The unit of "
        "analysis is the <b>team</b>: a set of nonland cards that were "
        "maindecked together, in the same deck, in all three pods. "
        "Three different drafters, three different decks, the same "
        "cards ending up shoulder to shoulder every time.</p>")
    out.append(
        "<p>Teams come in two sizes: <b>Pairs</b> — exactly two cards — "
        "and <b>Cores</b> — three or more.</p>")

    # --- the Lanes viewer: Macro -> Core sidebar + card viewer --------
    fam_order = ["Aggro", "Green", "Blue"]
    cores_by_fam = {f: [] for f in fam_order}
    for lsig, lcards in lanes:
        nm = core_name(lcards)
        cores_by_fam[FAMILY[nm]].append((nm, lsig, lcards))
    out.append("<div class='explorer'><div class='sidebar'>")
    idx = 0
    panes = []
    for f in fam_order:
        out.append(f"<div class='sbh'>{f}</div>")
        for nm, lsig, lcards in cores_by_fam[f]:
            on = " class='on'" if idx == 0 else ""
            out.append(f"<button{on} data-group='cores' "
                       f"data-show='core-{idx}'>{mana(colors_of(lcards))} "
                       f"{nm}</button>")
            hid = "" if idx == 0 else " hidden"
            panes.append(f"<div data-pane='cores' id='core-{idx}'{hid}>"
                         f"{gallery(lcards)}</div>")
            idx += 1
    out.append("</div><div class='vpanes'>")
    out += panes
    out.append("</div></div>")
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
        "<p>Ask for the Cores and the data hands "
        f"back just {len(lanes)} — and they sort themselves into "
        "three families:</p>")

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

    out.append("<h2>Two Mardu aggro decks</h2>")
    out.append(
        "<p>The aggro seats resolved into two cores that live one pip "
        "apart. Tokens is the largest and most stable structure "
        "in the data — nine cards that three different drafters "
        "assembled almost identically, a deck the cube practically "
        "deals to whoever sits down in it. Sac is its darker "
        "sibling: Deadly Dispute, Marionette Apprentice, and Mayhem "
        "Devil forming the sacrifice engine every pod rebuilt. The "
        "two bridges below are why these read as one Mardu family — "
        "Bastion of Remembrance and Voice of Victory, Magda and "
        "Torch the Tower each lived in a Sac deck in one pod and a "
        "Tokens deck in another. The white and red halves bleed into "
        "each other; the black-red core just decides which half "
        "you're in.</p>")
    out.append(f"<h3>{mana('WR')} Tokens</h3>")
    out.append(lane_block(tokens))
    out.append(f"<h3>{mana('BR')} Sac</h3>")
    out.append(lane_block(sac))
    out.append(family_bridges("Aggro"))

    out.append("<h2>Three green decks</h2>")
    out.append(
        "<p>Green produced three cores and one connected engine room. "
        "The two ramp cores — the five-color Fires-of-Invention pile "
        "and the Pizza build — share two of their three drafters, "
        "which is to say: the people who ramp, ramp both ways. "
        "Graveyard is the third leg — a Spider Spawning value core, "
        "Golgari once you count the flashback cost — sharing a drafter "
        "with Fires Ramp. Where "
        "Aggro splits into two clean decks, Green is one ecosystem "
        "with three stable expressions.</p>")
    out.append(f"<h3>{mana('URG')} Ramp</h3>")
    out.append(lane_block(temur_ramp))
    out.append(f"<h3>{mana('BG')} Ramp</h3>")
    out.append(lane_block(golgari_ramp))
    out.append(f"<h3>{mana('G')} Graveyard</h3>")
    out.append(lane_block(graveyard))
    out.append(family_bridges("Green"))

    out.append("<h2>Two blue decks</h2>")
    out.append(
        "<p>Blue split along the oldest line there is: do you want to "
        "answer things or untap and win. The Spells core is pure "
        "spell velocity — Consider, Think Twice, Expressive Iteration, "
        "Demon Bolt. The Discard core is the Censor-Quench-Shoreline "
        "Looter package that taxes and chips. Hieroglyphic "
        "Illumination and Lórien Revealed ride with both, the "
        "card-flow glue of the family.</p>")
    out.append(f"<h3>{mana('UR')} Spells</h3>")
    out.append(lane_block(blue_spells))
    out.append(f"<h3>{mana('U')} Discard</h3>")
    out.append(lane_block(blue_tempo))
    out.append(family_bridges("Blue"))

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
    out.append("<h2>How the cores group</h2>")
    out.append(
        "<p>The seven cores are not seven islands. Sort them by which "
        "actual decks they ran through and they collapse into the "
        "three families above — and the grouping isn't aesthetic, "
        "it's mechanical:</p>")
    for n1, n2, common in shared:
        cc = ", ".join(deck_link(k, pl) for k, pl in common)
        out.append(f"<p class='meta'>{n1} and {n2} share {cc}</p>")

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

    # family-loyal extras: maindecked 3x, always inside the family's
    # core decks, but in no core themselves — the family glue
    fam_decks = {"Aggro": set(), "Green": set(), "Blue": set()}
    core_cards_all = set()
    for lsig, lcards in lanes:
        fm = FAMILY[core_name(lcards)]
        core_cards_all |= set(lcards)
        for k, pl in enumerate(lsig):
            fam_decks[fm].add((k, pl))

    def fam_glue(fm):
        return sorted(
            c for c, sig in owners.items()
            if None not in sig and c not in core_cards_all
            and all((k, pl) in fam_decks[fm]
                    for k, pl in enumerate(sig)))

    def glue_strip(x, y, w, cards):
        s = [f"<rect x='{x}' y='{y}' width='{w}' height='96' rx='9' "
             f"fill='none' stroke='#aaa' stroke-dasharray='4 3'/>",
             f"<text x='{x + 10}' y='{y + 16}' font-size='11' "
             f"font-family='-apple-system,sans-serif' fill='#8a8a8a'>"
             f"FAMILY-WIDE</text>"]
        for i, c in enumerate(cards):
            img = scry[c].get("image")
            s.append(f"<image href='{img}' x='{x + 8 + i * 48}' "
                     f"y='{y + 24}' width='44' height='62'>"
                     f"<title>{html.escape(c)}</title></image>")
        return "".join(s)

    svg = ["<svg viewBox='0 0 680 830' style='max-width:680px;"
           "width:100%;margin:16px 0'>"]
    svg.append(region(6, 6, 216, 688, "#f7ebe8", "MARDU"))
    svg.append(region(232, 6, 216, 688, "#ebf3e8", "GREEN"))
    svg.append(region(458, 6, 216, 688, "#e8eff6", "BLUE"))
    n_tok, h_tok = node_cards(30, 34, "WR", "Tokens", tokens[1])
    n_sac, h_sac = node_cards(30, 34 + h_tok + 24, "BR", "Sac", sac[1])
    svg += [n_tok, n_sac]
    svg.append(glue_strip(30, 34 + h_tok + 24 + h_sac + 24, 168,
                          fam_glue("Aggro")))
    n1, h1 = node_cards(256, 34, "URG", "Ramp", temur_ramp[1])
    n2, h2 = node_cards(256, 34 + h1 + 24, "BG", "Ramp", golgari_ramp[1])
    n3, h3 = node_cards(256, 34 + h1 + 24 + h2 + 24, "BG", "Graveyard",
                        graveyard[1])
    svg += [n1, n2, n3]
    svg.append(glue_strip(256, 34 + h1 + h2 + h3 + 72, 168,
                          fam_glue("Green")))
    n4, h4 = node_cards(482, 34, "UR", "Spells", blue_spells[1])
    n5, h5 = node_cards(482, 34 + h4 + 24, "U", "Discard", blue_tempo[1])
    svg += [n4, n5]
    svg.append(glue_strip(482, 34 + h4 + 24 + h5 + 24, 168,
                          fam_glue("Blue")))
    # the ghost region: the family of free pairs that never found a core
    ry = 706
    svg.append(f"<rect x='6' y='{ry}' width='668' height='118' rx='14' "
               f"fill='none' stroke='#b5b0a8' stroke-dasharray='6 4'/>")
    svg.append(f"<text x='18' y='{ry + 20}' font-size='11' "
               f"font-family='-apple-system,sans-serif' "
               f"letter-spacing='.08em' fill='#8a8a8a'>RECTANGLES — "
               f"THE CORE THAT NEVER ASSEMBLED</text>")
    px = 16
    for psig, pcards in free:
        for j, c in enumerate(sorted(pcards)):
            img = scry[c].get("image")
            svg.append(f"<image href='{img}' x='{px + j * 44}' "
                       f"y='{ry + 30}' width='42' height='59'>"
                       f"<title>{html.escape(c)}</title></image>")
        px += 94
    svg.append("</svg>")
    out.append("".join(svg))

    # --- categorizing the pairs ---------------------------------------
    out.append("<h2>Categorizing the pairs</h2>")
    out.append(
        "<p>Every pair, with the identity of its three owners. Where "
        "a deck owns a core, that core is its label; every core-less "
        "deck is a Rectangles deck (a deck with no teams at all "
        "keeps its drafter's name). Read down the table and the law "
        "shows itself: when a pair sits with a core twice, the third "
        "owner is a sibling from the same family, or Rectangles — "
        "never a core from another family.</p>")
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
        return f'<a href="{url}">{lab}</a>' if url else lab

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
    out.append("<table class='pairtab'><tr><th>Pair</th>"
               "<th>Draft 1</th><th>Draft 2</th><th>Draft 3</th></tr>")
    for psig, pcards in prows:
        pair_cell = "<br>".join(card_link(c) for c in pcards)
        cells = "".join(f"<td>{owner_cell(k, pl)}</td>"
                        for k, pl in enumerate(psig))
        out.append(f"<tr><td>{pair_cell}</td>{cells}</tr>")
    out.append("</table>")

    out.append("<h2>The Rectangles</h2>")
    out.append(
        "<p>Seven pairs live entirely outside the core system — no "
        "core claims two of their decks, no two cores share them. "
        "Look at them together and they stop looking like leftovers: "
        "white-black drain enchantments, white auras and adventures, "
        "blue rooms and cases. We call the family Rectangles. It is "
        "the eighth core that never quite assembled — the bonds kept "
        "forming, in every pod, and never found their third card."
        "</p><div class='pairs'>")
    for psig, pcards in free:
        out.append(pair_span(pcards))
    out.append("</div>")

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
    from collections import Counter as _Cn
    out.append("<h2>Where the core-less decks fit</h2>")
    out.append(
        "<p>Ten decks own no core. Label every pair with its family "
        "and ask what those ten decks were actually doing, and the "
        "answer is one word: Rectangles. Arason is the instructive "
        "case — both of that deck's teams point at Sac, because its "
        "rectangle-makers (Magda, Piggy Bank) got claimed by aggro "
        "decks in the other pods. But the deck itself is rectangles "
        "to the bone: Blood, Treasure, Junk, equipment tokens. Bonds "
        "measure who else wanted your cards, not what your deck "
        "does. roc and ColdBrewNate lean Blue the same way. One "
        "deck fits nothing at all; it gets its own section.</p>")
    out.append("<table><tr><th>Deck</th><th>Their pairs say</th></tr>")
    for k, pl in no_lane_x:
        my = [pair_label(psig) for psig, _ in pair_teams if psig[k] == pl]
        cnt = _Cn(my)
        fit = ", ".join(f"{l} ×{n}" if n > 1 else l
                        for l, n in cnt.most_common()) or "—"
        out.append(f"<tr><td>{drafts[k].name} {html.escape(pl)}</td>"
                   f"<td>{fit}</td></tr>")
    out.append("</table>")

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
    out.append("<h2>The seat chart</h2>")
    out.append(
        "<p>Put it all together and every pod resolves to the same "
        "shape: six drafters own the seven cores (one always doubles "
        "up, always in green), and everyone else is a Rectangles "
        "drafter — except one wildcard. FOOMP's companion was "
        "Gyruda: every nonland card in that deck has even mana "
        "value, a constraint that pulled it out of everyone else's "
        "card pool entirely. That's why it bonded with nothing.</p>")
    out.append("<div class='seats'>")
    for k, d in enumerate(drafts):
        col = [f"<div><div class='sbh'>{d.name}</div>"]
        rows = []
        for pl in d.players:
            cores_own = lane_of_deck.get((k, pl), [])
            nm = html.escape(pl)
            if cores_own:
                fam = FAMILY[cores_own[0]]
                lab = " + ".join(deck_core_lab[(k, pl)])
                rows.append((0, FAM_ORDER.index(fam),
                             f"<div class='seat s{fam}'>{nm}"
                             f"<span>{lab}</span></div>"))
            else:
                main = coreless_label(k, pl)
                if main:
                    lean = seat_lean(k, pl)
                    lab = (f"Rectangles &middot; leans {lean}"
                           if lean else "Rectangles")
                    rows.append((2, 0, f"<div class='seat sRect'>{nm}"
                                 f"<span>{lab}</span></div>"))
                else:
                    rows.append((3, 0, f"<div class='seat sLone'>{nm}"
                                 f"<span>wildcard — Gyruda, all even, "
                                 f"no teams</span></div>"))
        col += [h for _, __, h in sorted(rows, key=lambda r: r[:2])]
        col.append("</div>")
        out.append("".join(col))
    out.append("</div>")
    out.append("<p class='meta'>Every deck in every pod, by its place "
               "in the team system. Tinted = owns a core (its family's "
               "color). Dashed white = Rectangles deck, with the "
               "family its bonds lean toward. Gray = the wildcard.</p>")

    # --- bar graph: cards in teams by color identity + pair gallery ---
    ident = Counter()
    for _, cards in groups:
        cl = colors_of(cards)
        if len(cl) >= 2:
            ident[cl] += len(cards)
    out.append("<h2>Where the teams live</h2>")
    out.append(
        "<p>Add the pairs to the cores and count where the teams "
        "actually live:</p>")
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

    # --- the most original decks --------------------------------------
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
    out.append("<h2>The most original decks</h2>")
    out.append(
        "<p>Flip the question over. Instead of asking what recurred, "
        "ask what <i>never</i> did: for each deck, the largest group of "
        "cards no other deck ever ran any two of — its unique ensemble, "
        "the part of the deck that was genuinely invented at that "
        "table. (The three Yorion decks sit this one out: a 60-card "
        "maindeck gets extra room for unique pairs just by being big.) "
        "Core ownership turns out to be the opposite of originality: "
        f"core decks average {avg_lane:.1f} unique cards, "
        f"decks outside the core system {avg_free:.1f}.</p>")
    from collections import Counter as _Ch
    hist = _Ch(sizes.values())
    out.append("<div class='vchart'>")
    mxh = max(hist.values())
    for s in range(min(hist), max(hist) + 1):
        n = hist.get(s, 0)
        hpx = round(n / mxh * 130) if n else 0
        bar = (f"<div class='vbar' style='height:{hpx}px'></div>"
               if n else "<div style='height:0'></div>")
        out.append(f"<div class='vcol'><span class='vnum'>{n or ''}"
                   f"</span>{bar}<span class='vlab'>{s}</span></div>")
    out.append("</div>")
    out.append("<p class='meta'>Decks by size of their largest unique "
               "ensemble (nonland cards, no pair shared with any other "
               "deck). Yorion decks excluded.</p>")
    max_size = max(sizes.values())
    leaders = sorted(dk for dk in sizes if sizes[dk] == max_size)
    out.append(
        f"<p>The record is {max_size}"
        + ("." if len(leaders) == 1 else ", and it's a tie.")
        + "</p>")
    for lk, lpl in leaders:
        out.append(
            f"<p>{deck_link(lk, lpl)}: {sizes[(lk, lpl)]} of its "
            f"{len(by_deck_all[(lk, lpl)])} nonland cards form a group "
            "that exists nowhere else in ninety decks' worth of "
            "building:</p>")
        out.append(gallery(ue[(lk, lpl)]))

    # --- the FOOMP section --------------------------------------------
    by_deck = deck_sets(owners)
    zero_team = []
    for k, d in enumerate(drafts):
        for pl in d.players:
            if not any(sig[k] == pl for sig, _ in groups):
                zero_team.append((k, pl))
    for k, pl in zero_team:
        dcards = by_deck[(k, pl)]
        url = url_map.get((drafts[k].name, pl))
        link = (f'<a href="{url}">sealeddeck</a>' if url else "")
        out.append(f"<h2>The {html.escape(pl)} deck</h2>")
        out.append(
            "<p>Raise a glass. Twenty-seven drafters built decks made "
            "of teams — combinations the other pods discovered too. "
            "One did not. <span class='todo'>[draft — make it yours]"
            "</span></p>")
        out.append(
            f"<p>Every other drafter — all 27 of them — built a deck "
            f"containing at least one team: some two-card combination "
            f"that also showed up, together, in both other pods. "
            f"{html.escape(pl)} is the exception. Not one pair of "
            f"nonland cards in this deck was ever maindecked together "
            f"in both other pods. There's a mechanical reason: the "
            f"companion is Gyruda, and every single nonland card here "
            f"has even mana value — a constraint that pulled this "
            f"deck out of the card pool everyone else was drafting "
            f"from. Twenty-eight decks, one true original. {link}</p>")
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
