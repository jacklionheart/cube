import unittest

from fantasia import (
    added_names_between,
    mainboard_tag_edits,
    maybeboard_tag_edits,
    one_time_imports,
)
from tag_library import FANTASIA_TAG


def card(name, tags):
    return {
        "cardID": f"id-{name}",
        "name": name,
        "index": 0,
        "tags": tags,
    }


class FantasiaTagSyncTest(unittest.TestCase):
    def test_snapshot_diff_identifies_only_later_additions(self):
        before = {"cards": {"maybeboard": [card("Kept", [])]}}
        after = {
            "cards": {"maybeboard": [card("Kept", []), card("Added", [])]}
        }

        self.assertEqual({"added"}, added_names_between(before, after))

    def test_one_time_import_dedupes_and_omits_self_tag(self):
        imports = one_time_imports(
            {"already here"},
            [[card("Already Here", []), card("New", [])], [card("New", [])]],
            {"new": {FANTASIA_TAG, "🅰️ Alpha Reimagined"}},
        )

        self.assertEqual(["New"], [imported["name"] for imported in imports])
        self.assertEqual(["🅰️ Alpha Reimagined"], imports[0]["tags"])

    def test_mainboard_keeps_only_allies_and_enemies(self):
        edits = mainboard_tag_edits([
            card("Hero", ["🤝 Allies", "✨ Picked", "🔥 Banger"]),
            card("Villain", ["⚔️ Enemies", "⚛️ GUT"]),
        ])

        self.assertEqual(2, len(edits))
        self.assertEqual(["🤝 Allies"], edits[0]["newCard"]["tags"])
        self.assertEqual(["⚔️ Enemies"], edits[1]["newCard"]["tags"])

    def test_maybeboard_replaces_all_tags_with_live_provenance(self):
        moved_card = card("Moved Card", ["🤝 Allies", "✨ Picked"])
        edits = maybeboard_tag_edits(
            [moved_card],
            {"moved card": {FANTASIA_TAG, "⚛️ GUT", "🔥 Banger"}},
        )

        self.assertEqual(1, len(edits))
        self.assertEqual(["⚛️ GUT", "🔥 Banger"], edits[0]["newCard"]["tags"])

    def test_maybeboard_never_writes_fantasia_self_tag(self):
        edits = maybeboard_tag_edits(
            [card("Current", [FANTASIA_TAG, "👑 LOL"])],
            {"current": {FANTASIA_TAG, "👑 LOL"}},
        )

        self.assertEqual(["👑 LOL"], edits[0]["newCard"]["tags"])

    def test_maybeboard_removes_stale_tags_when_sources_disappear(self):
        edits = maybeboard_tag_edits(
            [card("Former Banger", ["✨ Picked", "🔥 Banger"])],
            {},
        )

        self.assertEqual([], edits[0]["newCard"]["tags"])

    def test_matching_tags_do_not_generate_an_edit(self):
        edits = maybeboard_tag_edits(
            [card("Current", ["👑 LOL", "🔥 Banger"])],
            {"current": {"👑 LOL", "🔥 Banger"}},
        )

        self.assertEqual([], edits)


if __name__ == "__main__":
    unittest.main()
