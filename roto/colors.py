"""Card-color and front-face land rules over caller-provided metadata."""
import re as _re
WUBRG = "WUBRG"

def card_colors(name, scry, *, include_flashback=False):
    """Systematic color assignment: the card's mana-cost colors, plus —
    for lands only — the colors of mana it produces, unless it produces
    all five (rainbow utility lands like Edgewall Inn or Spire of
    Industry count as colorless, same as fetches). So Path to the World
    Tree is G (not its WUBRG identity), Everything Pizza and Shattered
    Landscape are colorless, Temple Garden is GW. Produced mana on
    nonlands is ignored (else every Treasure-maker reads 5c)."""
    info = scry[name]
    colors = set(info.get("colors", []))
    if "Land" in info["type_line"]:
        produced = set(info.get("produced_mana", [])) & set(WUBRG)
        if len(produced) < 5:
            colors |= produced
    if include_flashback:
        import re as _re
        for line in _re.findall(r"Flashback[^\n]*",
                                info.get("oracle_text", "")):
            for grp in _re.findall(r"\{([^}]*)\}", line):
                colors |= set(grp) & set(WUBRG)
    return colors


def colors_str(cards, scry, *, include_flashback=False):
    """WUBRG-ordered union of card_colors over a card set; 'C' if none."""
    u = set()
    for c in cards:
        u |= card_colors(c, scry, include_flashback=include_flashback)
    return "".join(c for c in WUBRG if c in u) or "C"


def _mana_cost(card, scry):
    b = _re.sub(r" \\d+$", "", card)
    return (scry.get(b) or scry.get(card) or {}).get("mana_cost") or ""


def combo_color(cards, scry):
    """WUBRG-ordered colors of a card set, hybrid-aware: hybrid pips are
    resolved last and only add a color if the set has none of theirs
    (else no-op; ties pick the WUBRG-first option). Figure of Destiny
    {R/W} thus stays out of a red team's color."""
    colors, hybrids = set(), []
    for c in cards:
        for sym in _re.findall(r"\{([^}]+)\}", _mana_cost(c, scry)):
            letters = [x for x in sym.split("/") if x in WUBRG]
            if "/" in sym and letters:
                hybrids.append(set(letters))
            elif sym in WUBRG:
                colors.add(sym)
    for hy in hybrids:
        if not (colors & hy):
            colors |= {min(hy, key=WUBRG.index)}
    return "".join(c for c in WUBRG if c in colors) or "C"


def is_land(name, scry):
    """Front-face land check (MDFC spell//land faces count as nonland)."""
    return "Land" in scry[name]["type_line"].split(" // ")[0]


def nonland_owners(owners, scry):
    """Restrict the maindeck-owners map to nonland cards — the whole
    analysis then ignores lands (lane cores become 3+ nonland cards)."""
    return {c: sig for c, sig in owners.items() if not is_land(c, scry)}
