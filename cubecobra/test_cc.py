import unittest

from cc import CubeCobra, board_tag_edits, change_batches, missing_slot_removals
from tag_library import ELEMENTAL_TAG, FANTASIA_TAG


class BoardTagEditsTest(unittest.TestCase):
    def test_excludes_target_self_tag_but_keeps_cross_cube_tags(self):
        cards = [{
            "cardID": "card-id",
            "name": "Overlap",
            "index": 0,
            "tags": [ELEMENTAL_TAG, FANTASIA_TAG],
        }]

        edits = board_tag_edits(
            cards,
            {"overlap": {ELEMENTAL_TAG, FANTASIA_TAG, "🔥 Banger"}},
            excluded_tags={ELEMENTAL_TAG},
        )

        self.assertEqual(
            [FANTASIA_TAG, "🔥 Banger"],
            edits[0]["newCard"]["tags"],
        )


class MissingSlotRemovalsTest(unittest.TestCase):
    def test_returns_only_missing_indexes_in_descending_order(self):
        cards = [{"index": 0}, {"index": 2}, {"index": 4}]

        removals = missing_slot_removals(cards, 5, "fixture")

        self.assertEqual([3, 1], [remove["index"] for remove in removals])
        self.assertEqual(
            ["<empty storage slot 3>", "<empty storage slot 1>"],
            [remove["oldCard"]["name"] for remove in removals],
        )

    def test_contiguous_board_needs_no_repairs(self):
        cards = [{"index": 0}, {"index": 1}]

        self.assertEqual([], missing_slot_removals(cards, 2))

    def test_rejects_metadata_smaller_than_hydrated_board(self):
        with self.assertRaisesRegex(RuntimeError, "invalid stored card count"):
            missing_slot_removals([{"index": 0}, {"index": 1}], 1)

    def test_rejects_indexes_outside_the_stored_span(self):
        with self.assertRaisesRegex(RuntimeError, "exceeds stored card count"):
            missing_slot_removals([{"index": 0}, {"index": 2}], 2)


class ChangeBatchesTest(unittest.TestCase):
    def test_preserves_index_safe_operation_order(self):
        changes = {
            "mainboard": {
                "adds": [{"name": "add-a"}, {"name": "add-b"}],
                "removes": [{"index": 1}, {"index": 4}],
                "edits": [{"index": 0}, {"index": 2}],
            }
        }

        batches = change_batches(changes, batch_size=2)
        flattened = [
            (operation, entry)
            for batch in batches
            for operation, entries in batch["mainboard"].items()
            for entry in entries
        ]

        self.assertEqual(3, len(batches))
        self.assertEqual(
            [
                ("edits", {"index": 0}),
                ("edits", {"index": 2}),
                ("removes", {"index": 4}),
                ("removes", {"index": 1}),
                ("adds", {"name": "add-a"}),
                ("adds", {"name": "add-b"}),
            ],
            flattened,
        )

    def test_rejects_invalid_batch_size(self):
        with self.assertRaisesRegex(ValueError, "positive integer"):
            change_batches({"mainboard": {"adds": [{}]}}, batch_size=0)

    def test_chains_versions_and_backs_up_once(self):
        class FakeCubeCobra(CubeCobra):
            def __init__(self):
                self.backups = []
                self.commits = []

            def backup(self, cube_id):
                self.backups.append(cube_id)

            def _commit_once(self, cube_id, changes, expected_version, title):
                self.commits.append((changes, expected_version, title))
                return {"success": "true", "version": expected_version + 1}

        client = FakeCubeCobra()
        changes = {"mainboard": {"edits": [{"index": i} for i in range(5)]}}

        result = client.commit_batched(
            "cube-id", changes, 10, "Sync tags", batch_size=2,
        )

        self.assertEqual(["cube-id"], client.backups)
        self.assertEqual([10, 11, 12], [commit[1] for commit in client.commits])
        self.assertEqual(
            ["Sync tags (1/3)", "Sync tags (2/3)", "Sync tags (3/3)"],
            [commit[2] for commit in client.commits],
        )
        self.assertEqual(13, result["version"])


if __name__ == "__main__":
    unittest.main()
