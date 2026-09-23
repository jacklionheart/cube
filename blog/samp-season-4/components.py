"""Generated cards, tables, and metrics for post.md. Prose belongs in Markdown."""

import html
import json
import pathlib
import sys
from urllib.parse import quote

HERE = pathlib.Path(__file__).resolve().parents[2] / "roto" / "samp"
sys.path.insert(0, str(HERE))

import packages as pk
import team_search as ts
from roto.packages import jaccard_components, backbone_depth
from render import card_gallery, tabbed_panels

TITLE = "Samp Roto s4 — the components"
SLUG = "samp-season-4"
_imgpath = HERE / "images.json"
IMAGES = json.loads(_imgpath.read_text()) if _imgpath.exists() else {}

AGGRO_SEED = {
    "Mother of Runes", "Luminarch Aspirant", "Practiced Offense", "Glimmer Lens",
    "Stoneforge Mystic", "Staff of the Storyteller", "Adeline, Resplendent Cathar",
    "Intrepid Adversary", "Warden of the Inner Sky", "Giver of Runes",
    "Voice of Victory", "Phelia, Exuberant Shepherd", "Witch Enchanter",
    "Novice Inspector", "Thraben Inspector", "Sanguine Evangelist",
}
CATS = ["Removal", "Aggro", "Tokens", "Draws"]


# ---- data helpers (self-contained; no dependency on report.py) --------
def pct(w, l):
    return w / (w + l) if (w + l) else None


def wr_of(decklist, rec):
    w = l = 0
    for kp in decklist:
        a, b = rec[kp]
        w, l = w + a, l + b
    return w, l


def load():
    drafts, cube, decks, scry, owners = ts.load_owners()
    deck_sets = {}
    for c, sig in owners.items():
        for k, p in enumerate(sig):
            if p:
                deck_sets.setdefault((k, p), set()).add(c)
    rec = {kp: drafts[kp[0]].records.get(kp[1], (0, 0)) for kp in deck_sets}
    md = {c: sum(p is not None for p in sig) for c, sig in owners.items()}
    return drafts, cube, decks, scry, owners, deck_sets, rec, md






def img_url(card):
    base = card[:-2].strip() if card.endswith(" 2") else card
    return IMAGES.get(base) or (
        "https://api.scryfall.com/cards/named?exact="
        + quote(base) + "&format=image&version=normal")


def wr_str(w, l, cls=True):
    r = pct(w, l)
    if r is None:
        return "<span class='big'>—</span>"
    c = "" if not cls else (" hi" if r >= 0.52 else " lo" if r < 0.48 else "")
    return f"<span class='wr{c}'>{r:.0%}</span> <span class='big'>({w}–{l})</span>"


def card_cap(card, deck_sets, rec, extra=""):
    withc = [kp for kp in deck_sets if card in deck_sets[kp]]
    w, l = wr_of(withc, rec)
    r = pct(w, l)
    rs = f"{r:.0%}" if r is not None else "—"
    return f"{extra}{rs} · {w}–{l}"


def gallery(cards, deck_sets, rec, caps=None):
    captions = {
        c: html.escape(c.split(',')[0]) + "<br>" +
        (caps[c] if caps and c in caps else card_cap(c, deck_sets, rec))
        for c in cards
    }
    return card_gallery(cards, {c: img_url(c) for c in cards}, captions=captions)


# ---------------------------------------------------------------- sections
def package_block(name, pool, owners, deck_sets, rec, md, scry):
    pool = set(pool)
    T = 3
    ncore = {kp: len(cs & pool) for kp, cs in deck_sets.items()}
    tagged = [kp for kp in deck_sets if ncore[kp] >= T]
    depth = backbone_depth(owners, pool)
    w, l = wr_of(tagged, rec)
    ranked = sorted(pool, key=lambda c: (
        -depth[c], -sum(1 for kp in tagged if c in deck_sets[kp]), c))
    caps = {}
    for c in ranked:
        withc = [kp for kp in tagged if c in deck_sets[kp]]
        ww, ll = wr_of(withc, rec)
        r = pct(ww, ll)
        incl = len(withc) / len(tagged) if tagged else 0
        caps[c] = (f"d{depth[c]} · {incl:.0%} in"
                   f"<br>{r:.0%} · {ww}–{ll}" if r is not None else "—")
    parts = {
        "colors": pk.combo_color(pool, scry),
        "size": str(len(pool)),
        "deck-count": str(len(tagged)),
        "threshold": str(T),
        "record": wr_str(w, l),
        "cards": gallery(ranked, deck_sets, rec, caps),
    }
    out = []

    # WR by package density (how many core cards a deck runs), high/med/low
    n = len(pool)
    bins = [("High", f"≥{round(0.7*n)}", lambda k: ncore[k] >= 0.7 * n),
            ("Med", f"{max(T, round(0.4*n))}–{round(0.7*n)-1}",
             lambda k: 0.4 * n <= ncore[k] < 0.7 * n),
            ("Low", f"{T}–{max(T, round(0.4*n))-1}",
             lambda k: T <= ncore[k] < 0.4 * n)]
    out.append("<table class='dat'><tr><th>Commitment</th><th>core cards</th>"
               "<th class='n'>Decks</th><th class='n'>WR</th></tr>")
    for lab, rng, test in bins:
        b = [k for k in tagged if test(k)]
        out.append(f"<tr><td>{lab}</td><td>{rng}</td>"
                   f"<td class='n'>{len(b)}</td>"
                   f"<td class='n'>{wr_str(*wr_of(b, rec))}</td></tr>")
    out.append("</table>")

    parts["density"] = "\n".join(out)
    out = []

    # Non-core cards these decks also play (>=30% inclusion).
    pen = []
    allc = set().union(*[deck_sets[k] for k in tagged]) if tagged else set()
    for c in allc:
        if c in pool:
            continue
        withc = [k for k in tagged if c in deck_sets[k]]
        incl = len(withc) / len(tagged)
        if incl < 0.30:
            continue
        ww, ll = wr_of(withc, rec)
        pen.append((c, incl, pct(ww, ll), ww, ll))
    pen.sort(key=lambda t: (-t[1], t[0]))
    if pen:
        out.append("<table class='dat'><tr><th>Card</th><th class='n'>Incl</th>"
                   "<th class='n'>WR</th><th class='n'>W–L</th></tr>")
        for c, incl, r, ww, ll in pen:
            rs = f"{r:.0%}" if r is not None else "—"
            out.append(f"<tr><td>{html.escape(c.split(',')[0])}</td>"
                       f"<td class='n'>{incl:.0%}</td><td class='n'>{rs}</td>"
                       f"<td class='n'>{ww}–{ll}</td></tr>")
        out.append("</table>")
    parts["also-played"] = "\n".join(out)
    return parts


def green_block(owners, deck_sets, rec, scry):
    def ent(c):
        return scry.get(c.replace(" 2", "", 1)) or scry.get(c) or {}

    def text(c):
        return (ent(c).get("oracle_text") or "").lower()

    def is_green(c):
        return "G" in ent(c).get("colors", []) and not pk.is_land(c, scry)

    md = lambda c: sum(p is not None for p in owners[c])
    green = [c for c in owners if is_green(c)]
    GY = {c for c in green if any(k in text(c) for k in
          ["graveyard", "escape", "delve", "descend", "mill",
           "from your graveyard"])}
    LF = {c for c in green if any(k in text(c) for k in
          ["landfall", "land enters", "lands you control",
           "play an additional land"])}
    gdecks = [kp for kp in deck_sets if "G" in pk.combo_color(
        [c for c in deck_sets[kp] if not pk.is_land(c, scry)], scry)]

    # method A: label the DECKS by which they lean on, pool their records
    leanA = {"Landfall": [], "Graveyard": [], "Balanced": []}
    for kp in gdecks:
        g, f = len(deck_sets[kp] & GY), len(deck_sets[kp] & LF)
        leanA["Landfall" if f > g else "Graveyard" if g > f
              else "Balanced"].append(kp)

    # method B: label the CARDS, average each card's deck-WR
    def card_wr(c):
        withc = [kp for kp in deck_sets if c in deck_sets[kp]]
        return pct(*wr_of(withc, rec))

    def avg_card_wr(cards):
        vals = [card_wr(c) for c in cards if md(c) >= 4]
        vals = [v for v in vals if v is not None]
        return sum(vals) / len(vals) if vals else None, len(vals)

    parts = {}
    out = []
    out.append("<table class='dat'><tr><th>Green deck leans</th><th class='n'>"
               "Decks</th><th class='n'>WR</th></tr>")
    for k in ("Landfall", "Graveyard", "Balanced"):
        w, l = wr_of(leanA[k], rec)
        out.append(f"<tr><td>{k}</td><td class='n'>{len(leanA[k])}</td>"
                   f"<td class='n'>{wr_str(w, l)}</td></tr>")
    out.append("</table>")
    parts["decks"] = "\n".join(out)
    out = []
    out.append("<table class='dat'><tr><th>Payoff type</th><th class='n'>Cards"
               "</th><th class='n'>Avg card WR</th></tr>")
    for k, S in (("Landfall", LF), ("Graveyard", GY)):
        a, n = avg_card_wr(S)
        rs = f"<span class='wr'>{a:.0%}</span>" if a is not None else "—"
        out.append(f"<tr><td>{k}</td><td class='n'>{n}</td>"
                   f"<td class='n'>{rs}</td></tr>")
    out.append("</table>")
    parts["card-rates"] = "\n".join(out)
    lf_show = sorted([c for c in LF if md(c) >= 5], key=lambda c: (-md(c), c))
    gy_show = sorted([c for c in GY if md(c) >= 6], key=lambda c: (-md(c), c))
    parts["landfall"] = gallery(lf_show, deck_sets, rec)
    parts["graveyard"] = gallery(gy_show, deck_sets, rec)
    return parts


def blue_block(owners, deck_sets, rec, scry, staple_md=6):
    def ent(c):
        return scry.get(c.replace(" 2", "", 1)) or scry.get(c) or {}

    def is_blue(c):
        return "U" in ent(c).get("colors", []) and not pk.is_land(c, scry)

    md = lambda c: sum(p is not None for p in owners[c])
    deck_colors = {kp: pk.combo_color(
        [c for c in cs if not pk.is_land(c, scry)], scry)
        for kp, cs in deck_sets.items()}
    groups = {"W": [], "R": [], "B": [], "G": []}
    for c in owners:
        if not is_blue(c) or md(c) < staple_md:
            continue
        dks = [kp for kp in deck_sets if c in deck_sets[kp]]
        share = {col: sum(1 for kp in dks if col in deck_colors[kp]) / len(dks)
                 for col in "WBRG"}
        dom = max("WRBG", key=lambda k: share[k])
        groups[dom].append((c, pct(*wr_of(dks, rec))))
    label = {"W": ("UW", "control"), "R": ("UR", "prowess"),
             "B": ("UB", "flash"), "G": ("UG", "ramp")}

    def gavg(col):
        vals = [r for _, r in groups[col] if r is not None]
        return sum(vals) / len(vals) if vals else None
    order = sorted("WRBG", key=lambda c: -(gavg(c) or 0))
    panels = []
    for col in order:
        a = gavg(col)
        cards = [c for c, _ in sorted(groups[col], key=lambda t: -(t[1] or 0))]
        gl, gn = label[col]
        rate = f"{a:.0%}" if a is not None else "—"
        body = (f"<div class='grouphdr'>{gl} {gn} — <span class='wr'>"
                f"{rate}</span> avg · {len(cards)} cards</div>"
                + gallery(cards, deck_sets, rec))
        panels.append((f"{gl} {gn}", body))
    return tabbed_panels("blue", panels, label="Blue partner colors")


def white_block(owners, deck_sets, rec, scry):
    import statistics as st

    def ent(c):
        return scry.get(c.replace(" 2", "", 1)) or scry.get(c) or {}

    def text(c):
        return (ent(c).get("oracle_text") or "").lower()

    def is_white(c):
        return "W" in ent(c).get("colors", []) and not pk.is_land(c, scry)

    def tags(c):
        t = text(c)
        o = set()
        if any(k in t for k in ["destroy target", "exile target", "exile it",
               "exile up to", "exile that", "destroy all", "exile all",
               "damage to any", "put target", "fight", "tap target creature",
               "-1/-1"]):
            o.add("Removal")
        if c in AGGRO_SEED:
            o.add("Aggro")
        if "token" in t and "create" in t:
            o.add("Tokens")
        if any(k in t for k in ["draw a card", "draw two", "draw three",
               "draws a card", "draw x"]):
            o.add("Draws")
        return o

    md = lambda c: sum(p is not None for p in owners[c])
    ct = {c: tags(c) for c in owners if is_white(c)}
    wdecks = [kp for kp in deck_sets if "W" in pk.combo_color(
        [c for c in deck_sets[kp] if not pk.is_land(c, scry)], scry)]
    out = []
    out.append("<table class='dat'><tr><th>Function</th><th class='n'>avg/deck"
               "</th><th class='n'>few → WR</th><th class='n'>many → WR</th></tr>")
    for cat in CATS:
        cnt = {kp: sum(1 for c in deck_sets[kp] if cat in ct.get(c, ()))
               for kp in wdecks}
        vals = list(cnt.values())
        m = st.median(vals)
        few = [kp for kp in wdecks if cnt[kp] <= m]
        many = [kp for kp in wdecks if cnt[kp] > m]
        out.append(f"<tr><td>{cat}</td><td class='n'>{sum(vals)/len(vals):.1f}"
                   f"</td><td class='n'>{wr_str(*wr_of(few, rec))}</td>"
                   f"<td class='n'>{wr_str(*wr_of(many, rec))}</td></tr>")
    out.append("</table>")
    parts = {"functions": "\n".join(out)}
    for cat in CATS:
        cards = sorted([c for c in ct if cat in ct[c] and md(c) >= 5],
                       key=lambda c: (-md(c), c))
        parts[cat.lower()] = gallery(cards, deck_sets, rec)
    return parts


def build():
    drafts, cube, decks, scry, owners, deck_sets, rec, md = load()
    cl = jaccard_components(owners, theta=0.6)

    def pick(seeds):
        for u in cl:
            if all(any(s in c for c in u) for s in seeds):
                return set(u)
        return set()

    sac = pick(["Yawgmoth", "Mayhem Devil", "Priest of Forgotten Gods"])
    dis = pick(["Cool but Rude", "Faithless Looting", "Inti"])

    parts = {"pod-count": str(len(drafts)), "deck-count": str(len(decks))}
    for prefix, values in (
        ("sacrifice", package_block("Sacrifice", sac, owners, deck_sets, rec, md, scry)),
        ("discard", package_block("Discard", dis, owners, deck_sets, rec, md, scry)),
        ("green", green_block(owners, deck_sets, rec, scry)),
        ("white", white_block(owners, deck_sets, rec, scry)),
    ):
        parts.update({f"{prefix}-{key}": value for key, value in values.items()})
    parts["blue-groups"] = blue_block(owners, deck_sets, rec, scry)
    return parts
