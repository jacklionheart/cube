"""Minimal Cube Cobra client for managing jacklionheart's cubes.

Auth is a plain passport-local session: POST /user/login sets a session
cookie. Credentials come from CUBECOBRA_USERNAME / CUBECOBRA_PASSWORD env
vars, falling back to an interactive prompt.

Writes go through POST /cube/api/commit, which uses optimistic locking on
the cube's version field — pass the version from the cubeJSON you diffed
against and the server rejects (409) if the cube changed underneath you.
"""

import datetime
import getpass
import json
import os
import pathlib
import time
from collections import Counter

import requests

BASE = "https://cubecobra.com"
BACKUP_DIR = pathlib.Path(__file__).resolve().parent / "backups"
USER_AGENT = "jacklionheart-cube-scripts/1.0 (personal cube maintenance; jack@loopflow.studio)"
PAUSE_SECONDS = 1.0
READ_ATTEMPTS = 5
READ_RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
COMMIT_BATCH_SIZE = 100
COMMIT_OPERATION_ORDER = ("swaps", "edits", "removes", "adds")

# Fields Cube Cobra strips before storage (CubeDynamoDao.stripDetails), plus
# display-only baggage. Removing them keeps request payloads small.
_STRIP_FIELDS = frozenset({"details", "index", "board", "editIndex", "markedForDelete"})


def clean_card(card):
    """Card dict suitable for a commit `adds` entry or changelog `oldCard`."""
    cleaned = {k: v for k, v in card.items() if k not in _STRIP_FIELDS}
    cleaned.setdefault("name", card_name(card))
    return cleaned


def card_key(card):
    """Identity for delta computation: scryfall printing id."""
    return card["cardID"]


def card_name(card):
    """Card name; not all cubeJSON cards carry a top-level name override."""
    return card.get("name") or card.get("details", {}).get("name", "<unknown>")


def name_key(card):
    """Identity for cross-cube unions: oracle card name, case-insensitive."""
    return card_name(card).lower()


def tag_edit(card, desired_tags):
    """Return a Cube Cobra card edit when ``card`` has stale tags."""
    desired_tags = sorted(desired_tags)
    if sorted(card.get("tags", [])) == desired_tags:
        return None
    old_card = clean_card(card)
    new_card = dict(old_card)
    new_card["tags"] = desired_tags
    return {"index": card["index"], "oldCard": old_card, "newCard": new_card}


def board_tag_edits(cards, tags_by_name, excluded_tags=frozenset()):
    """Make one board's tags match a library, less target-specific exclusions."""
    excluded_tags = set(excluded_tags)
    return [
        edit
        for card in cards
        if (
            edit := tag_edit(
                card,
                set(tags_by_name.get(name_key(card), set())) - excluded_tags,
            )
        )
    ]


def remove_entry(card):
    """A commit `removes` entry. CRITICAL: cubeJSON returns boards sorted for
    display, not in stored order — the card's own `index` field is its stored
    position and is what the server splices on. Never use array position."""
    return {"index": card["index"], "oldCard": clean_card(card)}


def validate_indexes(board_cards, label="board"):
    """Stored indexes must be unique non-negative ints or removes would splice
    the wrong cards. Gaps are normal (null placeholder slots in the stored
    array are filtered out of cubeJSON responses); duplicates are not.
    Aborts rather than corrupting a cube."""
    idxs = [c.get("index", -1) for c in board_cards]
    if any(not isinstance(i, int) or i < 0 for i in idxs) or len(set(idxs)) != len(idxs):
        raise RuntimeError(f"{label}: card index fields are missing or duplicated; refusing to compute removes")


def missing_slot_removals(board_cards, stored_count, label="board"):
    """Build removals for stored board slots omitted from hydrated API cards.

    Cube Cobra can retain empty placeholder objects in a board. They count
    toward ``cardCount`` and occupy indexes, but disappear from the sorted
    ``cubeJSON`` card list. Removing the missing indexes compacts the stored
    array without touching any hydrated card.
    """
    validate_indexes(board_cards, label)
    if not isinstance(stored_count, int) or stored_count < len(board_cards):
        raise RuntimeError(
            f"{label}: invalid stored card count {stored_count!r} for "
            f"{len(board_cards)} hydrated cards"
        )
    indexes = {card["index"] for card in board_cards}
    if any(index >= stored_count for index in indexes):
        raise RuntimeError(
            f"{label}: hydrated card index exceeds stored card count; refusing to compact"
        )
    missing = sorted(set(range(stored_count)) - indexes, reverse=True)
    return [
        {
            "index": index,
            "oldCard": {"cardID": "", "name": f"<empty storage slot {index}>"},
        }
        for index in missing
    ]


def board_delta(current, desired, key=card_key):
    """Compute (adds, removes) turning `current` into `desired`.

    current: the target cube board as returned by cubeJSON.
    desired: card dicts specifying what the board should contain.
    Handles duplicate copies via counting.
    """
    validate_indexes(current)
    cur_counts = Counter(key(c) for c in current)
    want_counts = Counter(key(c) for c in desired)

    remove_quota = {
        k: cur_counts[k] - want_counts.get(k, 0)
        for k in cur_counts
        if cur_counts[k] > want_counts.get(k, 0)
    }
    removes = []
    for card in sorted(current, key=lambda c: -c["index"]):
        k = key(card)
        if remove_quota.get(k, 0) > 0:
            removes.append(remove_entry(card))
            remove_quota[k] -= 1

    add_quota = {
        k: want_counts[k] - cur_counts.get(k, 0)
        for k in want_counts
        if want_counts[k] > cur_counts.get(k, 0)
    }
    adds = []
    for c in desired:
        k = key(c)
        if add_quota.get(k, 0) > 0:
            adds.append(clean_card(c))
            add_quota[k] -= 1

    return adds, removes


def change_batches(changes, batch_size=COMMIT_BATCH_SIZE):
    """Split a commit into index-safe, bounded batches.

    Edits happen before removes so they retain the indexes from ``cubeJSON``.
    Removes happen from highest index to lowest, then adds happen last. This
    preserves the semantics of a single Cube Cobra commit across requests.
    """
    if not isinstance(batch_size, int) or batch_size < 1:
        raise ValueError("batch_size must be a positive integer")

    operations = []
    for operation in COMMIT_OPERATION_ORDER:
        for board, board_changes in changes.items():
            entries = list(board_changes.get(operation, []))
            if operation == "removes":
                entries.sort(key=lambda entry: entry["index"], reverse=True)
            operations.extend((board, operation, entry) for entry in entries)

    batches = []
    for start in range(0, len(operations), batch_size):
        batch = {}
        for board, operation, entry in operations[start:start + batch_size]:
            batch.setdefault(board, {}).setdefault(operation, []).append(entry)
        batches.append(batch)
    return batches


class CubeCobra:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self.logged_in = False

    def _request(self, method, path, *, retry=True, **kwargs):
        """Make a request, retrying only calls the caller identifies as safe.

        Cube Cobra sometimes stalls or returns a transient gateway error even
        on a healthy connection. Mutations pass ``retry=False`` so a lost
        response can never cause the same write to be sent twice.
        """
        attempts = READ_ATTEMPTS if retry else 1
        for attempt in range(1, attempts + 1):
            time.sleep(PAUSE_SECONDS)
            try:
                r = self.session.request(method, BASE + path, timeout=(15, 60), **kwargs)
                if r.status_code not in READ_RETRY_STATUSES or attempt == attempts:
                    r.raise_for_status()
                    return r
                reason = f"HTTP {r.status_code}"
                r.close()
            except (requests.Timeout, requests.ConnectionError) as error:
                if attempt == attempts:
                    raise
                reason = error.__class__.__name__
            # Discard pooled sockets after a timeout/disconnect while retaining
            # the Session's cookies (including an authenticated login).
            self.session.close()
            delay = 2 ** attempt
            print(f"  Cube Cobra {reason} for {path}; retrying in {delay}s "
                  f"({attempt}/{attempts})")
            time.sleep(delay)

        raise AssertionError("request retry loop exited unexpectedly")

    def login(self):
        username = os.environ.get("CUBECOBRA_USERNAME") or input("Cube Cobra username: ")
        password = os.environ.get("CUBECOBRA_PASSWORD") or getpass.getpass("Cube Cobra password: ")
        self._request(
            "POST", "/user/login",
            data={"username": username, "password": password},
            allow_redirects=False,
            retry=False,
        )
        # Login always redirects; verify the session actually took.
        r = self._request("GET", "/cube/api/mycubes")
        if r.status_code != 200:
            raise SystemExit("Cube Cobra login failed (bad credentials?)")
        self.logged_in = True
        return r.json()["cubes"]

    def cube_json(self, cube_id):
        """Full cube including cards; works unauthenticated for public/unlisted cubes."""
        return self._request("GET", f"/cube/api/cubeJSON/{cube_id}").json()

    def mycubes(self):
        """[{id, shortId, name, pinnedByCurrentUser}] for the logged-in user."""
        return self._request("GET", "/cube/api/mycubes").json()["cubes"]

    def resolve_cards(self, names, default_printing="recent"):
        """Resolve card names to printing details via /cube/api/getcardsforcube
        (no auth). Returns {lowercased name: details-or-None}, parallel to the
        server's response order."""
        out = {}
        names = list(names)
        for i in range(0, len(names), 100):
            batch = names[i:i + 100]
            r = self._request("POST", "/cube/api/getcardsforcube",
                              json={"names": batch, "defaultPrinting": default_printing})
            for n, details in zip(batch, r.json()["cards"]):
                out[n.lower()] = details
        return out

    def backup(self, cube_id):
        """Snapshot a cube's full JSON and CSV to backups/<timestamp>/.

        Called automatically before every mutation; safe to call ad hoc too.
        Returns the directory the snapshot was written to.
        """
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        dest = BACKUP_DIR / stamp
        dest.mkdir(parents=True, exist_ok=True)
        cube = self.cube_json(cube_id)
        safe_id = str(cube_id).replace("/", "_")
        (dest / f"{safe_id}.json").write_text(json.dumps(cube, indent=1))
        csv = self._request("GET", f"/cube/download/csv/{cube_id}")
        (dest / f"{safe_id}.csv").write_text(csv.text)
        print(f"  backed up {cube.get('name', cube_id)} -> {dest}/{safe_id}.{{json,csv}}")
        return dest

    def remove_cube(self, cube_id):
        """Delete a cube (backing it up first). Success is a redirect (302)."""
        self.backup(cube_id)
        r = self._request(
            "POST", f"/cube/remove/{cube_id}", data={}, allow_redirects=False,
            retry=False,
        )
        if r.status_code not in (200, 302):
            raise RuntimeError(f"remove_cube({cube_id}) unexpected status {r.status_code}")

    def _commit_once(self, cube_id, changes, expected_version, title):
        """Send one commit exactly once; callers resolve ambiguous timeouts."""
        time.sleep(PAUSE_SECONDS)
        r = self.session.post(
            BASE + "/cube/api/commit",
            json={
                "id": cube_id,
                "changes": changes,
                "title": title,
                "blog": "",
                "useBlog": False,
                "expectedVersion": expected_version,
            },
            timeout=(15, 90),
        )
        try:
            data = r.json()
        except requests.exceptions.JSONDecodeError:
            data = {}
        if r.status_code == 409:
            raise RuntimeError(f"Version conflict on {cube_id}: cube changed mid-run; re-run the script.")
        if r.status_code != 200 or data.get("success") != "true":
            raise RuntimeError(f"commit({cube_id}) failed: {r.status_code} {data.get('message')}")
        return data

    def _recover_commit_version(self, cube_id, expected_version):
        """Resolve a lost commit response without ever replaying the write."""
        print("  commit response timed out; checking Cube Cobra's live version…")
        self.session.close()
        time.sleep(5)
        live_version = self.cube_json(cube_id).get("version", 0)
        if live_version == expected_version + 1:
            print(f"  batch was accepted; recovered at version {live_version}")
            return {"success": "true", "version": live_version}
        if live_version == expected_version:
            raise RuntimeError(
                f"Commit response timed out and {cube_id} is still at version "
                f"{live_version}. The write was not replayed; re-run the sync to "
                "diff against live state."
            )
        raise RuntimeError(
            f"Commit response timed out and {cube_id} moved from expected version "
            f"{expected_version} to {live_version}. Refusing to continue across a "
            "possible concurrent edit; re-run the sync."
        )

    def commit(self, cube_id, changes, expected_version, title):
        """Apply one changes dict, with a backup and no automatic write retry."""
        self.backup(cube_id)
        try:
            return self._commit_once(cube_id, changes, expected_version, title)
        except (requests.Timeout, requests.ConnectionError):
            return self._recover_commit_version(cube_id, expected_version)

    def commit_batched(
        self,
        cube_id,
        changes,
        expected_version,
        title,
        batch_size=COMMIT_BATCH_SIZE,
    ):
        """Apply a large change in bounded commits, backing up exactly once.

        Each successful response supplies the optimistic-lock version for the
        next batch. A timed-out write is never repeated: the live version is
        consulted to determine whether Cube Cobra accepted it.
        """
        batches = change_batches(changes, batch_size)
        if not batches:
            raise ValueError("cannot commit an empty change set")

        self.backup(cube_id)
        version = expected_version
        result = None
        for index, batch in enumerate(batches, start=1):
            batch_title = title if len(batches) == 1 else f"{title} ({index}/{len(batches)})"
            operation_count = sum(
                len(entries)
                for board_changes in batch.values()
                for entries in board_changes.values()
            )
            print(f"  committing batch {index}/{len(batches)} ({operation_count} changes)…")
            try:
                result = self._commit_once(cube_id, batch, version, batch_title)
            except (requests.Timeout, requests.ConnectionError):
                result = self._recover_commit_version(cube_id, version)
            next_version = result.get("version")
            if not isinstance(next_version, int) or next_version <= version:
                raise RuntimeError(
                    f"commit({cube_id}) returned invalid version {next_version!r} "
                    f"after expected version {version}"
                )
            version = next_version
        return result


def describe_delta(label, adds, removes, add_names=None, remove_names=None):
    print(f"  {label}: +{len(adds)} / -{len(removes)}")
    for name in sorted(add_names if add_names is not None else [card_name(c) for c in adds]):
        print(f"    + {name}")
    for name in sorted(remove_names if remove_names is not None else [card_name(rm['oldCard']) for rm in removes]):
        print(f"    - {name}")
