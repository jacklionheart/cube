"""Shared provenance tags for Jack's Cube Cobra cubes."""

import csv
from collections import defaultdict

from cc import name_key

GAELARIA_TAG = "🌍 Gaelaria"
ELEMENTAL_TAG = "🌈 Elemental"
FANTASIA_TAG = "✨ Fantasia"
ALPHA_REIMAGINED_TAG = "🅰️ Alpha Reimagined"
GUT_TAG = "⚛️ GUT"
SACRED_TAG = "📐 Sacred"
LOL_TAG = "👑 LOL"
BANGER_TAG = "🔥 Banger"
LSV_RETRO_TAG = "📼 LSV Retro"

# Cube membership is provenance, not pool membership. Fantasia membership
# includes both boards, even though library tags are only written to its
# maybeboard.
CUBE_SOURCES = [
    ("sealed", GAELARIA_TAG, ("mainboard",)),
    ("elemental", ELEMENTAL_TAG, ("mainboard",)),
    ("fantasia", FANTASIA_TAG, ("mainboard", "maybeboard")),
    ("alpha-reimagined", ALPHA_REIMAGINED_TAG, ("mainboard",)),
]

INSPIRATION_SOURCES = [
    ("GUT", GUT_TAG, ("mainboard",)),
    ("sacred-geometry", SACRED_TAG, ("mainboard",)),
    ("0efda005-7243-457e-9d11-875e37d1b768", LOL_TAG, ("mainboard",)),
    ("LSVRetro", LSV_RETRO_TAG, ("mainboard",)),
]

TAG_SOURCES = CUBE_SOURCES + INSPIRATION_SOURCES


def read_banger_names(path):
    with open(path) as source:
        return sorted({row["Name"] for row in csv.DictReader(source)})


def load_tag_library(cc, bangers_csv, cubes=None):
    """Return ``(tags_by_name, source_cards, banger_names)``.

    ``cubes`` may provide already-fetched cube JSON keyed by short id. The
    returned source cards let pool-building scripts reuse the same snapshots
    without refetching or conflating a tag overlap with board membership.
    """
    cubes = dict(cubes or {})
    tags_by_name = defaultdict(set)
    source_cards = {}

    for cube_id, tag, boards in TAG_SOURCES:
        cube = cubes.get(cube_id)
        if cube is None:
            cube = cc.cube_json(cube_id)
            cubes[cube_id] = cube
        cards = [card for board in boards for card in cube["cards"].get(board, [])]
        source_cards[tag] = cards
        for card in cards:
            tags_by_name[name_key(card)].add(tag)

    banger_names = read_banger_names(bangers_csv)
    for name in banger_names:
        tags_by_name[name.lower()].add(BANGER_TAG)

    return dict(tags_by_name), source_cards, banger_names
