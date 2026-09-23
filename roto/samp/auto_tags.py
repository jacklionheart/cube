"""Mechanical theme tags — the seed for hand labels.

Single source of truth shared by the sheet builder (roto_summary) and
the theme report (theme_report). Each card's tags are derived by regex
over its Scryfall oracle text; these seed the editable Card Themes tab,
which Jack overrides by hand. themes.tsv (the synced hand labels) wins
over these wherever a card is present.
"""

import re

# (tag, regex over lowercased oracle text). A card may carry several;
# the first match is used as the single-label seed.
TAG_RULES = [
    ("Sacrifice", r"sacrifice (a|an|another|any|two|this)"),
    ("Aristocrats", r"(whenever|when) .{0,40}(dies|is put into a graveyard)"),
    ("Reanimation", r"(return|put) .{0,40}creature card.{0,40}(from your|from a) graveyard.{0,30}(battlefield|hand)"),
    ("Graveyard", r"(from (your|a) graveyard|mill|surveil|escape|flashback|delirium|threshold|descend|unearth|disturb|embalm)"),
    ("Discard", r"(discards? (a|two|three|that) card|madness|each player discards|blood token)"),
    ("Tokens", r"create (a|two|three|x|that many).{0,60}token"),
    ("Counters", r"\+1/\+1 counter"),
    ("Blink/ETB", r"(exile .{0,40}return (it|that|those).{0,20}battlefield|flicker|when(ever)? .{0,30}enters)"),
    ("Spells-matter", r"(prowess|magecraft|whenever you cast (a|an|your) (instant|sorcery|noncreature)|instant and sorcery)"),
    ("Artifacts", r"(artifact you control|artifacts you control|whenever (a|an|another) artifact|affinity|metalcraft|treasure)"),
    ("Card-selection", r"(scry|draw (a|two|three|that many) cards?|look at the top|surveil|connive)"),
    ("Counterspells", r"counter target"),
    ("Removal", r"(destroy target|exile target|deals? \d+ damage to (target|any|each))"),
    ("Ramp/Dorks", r"(add \{|search your library for (a|up to two) (basic )?land)"),
    ("Lifegain", r"(you gain \d+ life|whenever you gain life|lifelink)"),
    ("Burn/Aggro", r"(haste|deals? damage equal|attacks? each (turn|combat))"),
    ("Equipment", r"(equip \{|equipped creature)"),
    ("Landfall", r"(landfall|whenever a land you control enters)"),
]


def base_name(card):
    """A duplicated land's ' 2' suffix names the same card."""
    return card[:-2].strip() if card.endswith(" 2") else card


def tags_for(card, scry):
    """All mechanical tags a card matches (most-specific rules first)."""
    info = scry.get(base_name(card)) or scry.get(card) or {}
    text = (info.get("oracle_text") or "").lower()
    tl = (info.get("type_line") or "").lower()
    tags = [t for t, rx in TAG_RULES if re.search(rx, text)]
    if "planeswalker" in tl and not tags:
        tags.append("Card-selection")
    return tags


def seed_theme(card, scry):
    """Single-label seed for the editable Card Themes column."""
    tags = tags_for(card, scry)
    return tags[0] if tags else ""
