import csv
import pathlib
import tempfile
import unittest

from tag_library import (
    ALPHA_REIMAGINED_TAG,
    BANGER_TAG,
    ELEMENTAL_TAG,
    FANTASIA_TAG,
    GAELARIA_TAG,
    GUT_TAG,
    LOL_TAG,
    LSV_RETRO_TAG,
    SACRED_TAG,
    load_tag_library,
)


def card(name):
    return {"cardID": f"id-{name}", "name": name}


class FakeCubeCobra:
    def __init__(self, cubes):
        self.cubes = cubes

    def cube_json(self, cube_id):
        return self.cubes[cube_id]


class TagLibraryTest(unittest.TestCase):
    def test_collects_cube_and_inspiration_membership_by_board_scope(self):
        cubes = {
            "sealed": {"cards": {"mainboard": [card("Overlap")], "maybeboard": [card("Ignored Gaelaria")]}},
            "elemental": {"cards": {"mainboard": [card("Overlap")], "maybeboard": [card("Ignored Elemental")]}},
            "fantasia": {"cards": {"mainboard": [card("Overlap")], "maybeboard": [card("Fantasia Maybe")]}},
            "alpha-reimagined": {"cards": {"mainboard": [card("Overlap")]}},
            "GUT": {"cards": {"mainboard": [card("Overlap")]}},
            "sacred-geometry": {"cards": {"mainboard": [card("Overlap")]}},
            "0efda005-7243-457e-9d11-875e37d1b768": {"cards": {"mainboard": [card("Overlap")]}},
            "LSVRetro": {"cards": {"mainboard": [card("Overlap")]}},
        }
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "bangers.csv"
            with path.open("w", newline="") as output:
                writer = csv.DictWriter(output, fieldnames=["Name"])
                writer.writeheader()
                writer.writerow({"Name": "Overlap"})
            library, _, _ = load_tag_library(FakeCubeCobra(cubes), path)

        self.assertEqual(
            {
                ALPHA_REIMAGINED_TAG,
                GAELARIA_TAG,
                ELEMENTAL_TAG,
                FANTASIA_TAG,
                GUT_TAG,
                SACRED_TAG,
                LOL_TAG,
                LSV_RETRO_TAG,
                BANGER_TAG,
            },
            library["overlap"],
        )
        self.assertEqual({FANTASIA_TAG}, library["fantasia maybe"])
        self.assertNotIn("ignored gaelaria", library)
        self.assertNotIn("ignored elemental", library)


if __name__ == "__main__":
    unittest.main()
