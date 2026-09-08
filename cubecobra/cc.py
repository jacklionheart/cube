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


class CubeCobra:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self.logged_in = False

    def _request(self, method, path, **kwargs):
        time.sleep(PAUSE_SECONDS)
        r = self.session.request(method, BASE + path, timeout=60, **kwargs)
        r.raise_for_status()
        return r

    def login(self):
        username = os.environ.get("CUBECOBRA_USERNAME") or input("Cube Cobra username: ")
        password = os.environ.get("CUBECOBRA_PASSWORD") or getpass.getpass("Cube Cobra password: ")
        self._request(
            "POST", "/user/login",
            data={"username": username, "password": password},
            allow_redirects=False,
        )
        # Login always redirects; verify the session actually took.
        r = self.session.get(BASE + "/cube/api/mycubes", timeout=60)
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
        r = self._request("POST", f"/cube/remove/{cube_id}", data={}, allow_redirects=False)
        if r.status_code not in (200, 302):
            raise RuntimeError(f"remove_cube({cube_id}) unexpected status {r.status_code}")

    def commit(self, cube_id, changes, expected_version, title):
        """Apply a changes dict {board: {adds: [...], removes: [...]}} atomically."""
        self.backup(cube_id)
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
            timeout=120,
        )
        data = r.json()
        if r.status_code == 409:
            raise RuntimeError(f"Version conflict on {cube_id}: cube changed mid-run; re-run the script.")
        if r.status_code != 200 or data.get("success") != "true":
            raise RuntimeError(f"commit({cube_id}) failed: {r.status_code} {data.get('message')}")
        return data


def describe_delta(label, adds, removes, add_names=None, remove_names=None):
    print(f"  {label}: +{len(adds)} / -{len(removes)}")
    for name in sorted(add_names if add_names is not None else [card_name(c) for c in adds]):
        print(f"    + {name}")
    for name in sorted(remove_names if remove_names is not None else [card_name(rm['oldCard']) for rm in removes]):
        print(f"    - {name}")
