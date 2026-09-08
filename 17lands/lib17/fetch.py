"""Data acquisition: 17Lands card_ratings API, public S3 logs, Scryfall bulk.

All responses are cached under data/raw/. API calls are spaced >=3s with
exponential backoff on 403/429 (we were rate-limited once at 1.2s).
"""

import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent.parent
RAW = ROOT / "data" / "raw"
API = "https://www.17lands.com/card_ratings/data"
S3 = "https://17lands-public.s3.amazonaws.com/analysis_data"
UA = "Mozilla/5.0 (limited-data-analysis; contact jackstah@gmail.com)"
SLEEP = 3.0


def _cache_key(expansion, fmt, user_group, start, end, colors):
    key = f"{expansion}_{fmt}_{user_group or 'all'}_{start or 'min'}_{end or 'max'}_{colors or 'any'}"
    return key.replace(" ", "").replace("-", "")


def card_ratings(expansion, fmt="PremierDraft", user_group=None,
                 start=None, end=None, colors=None):
    """One filtered snapshot of the 17Lands card table, as a list of dicts.
    Cached forever by query; identical to what the website's table shows."""
    import requests

    RAW.mkdir(parents=True, exist_ok=True)
    cache = RAW / f"{_cache_key(expansion, fmt, user_group, start, end, colors)}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    params = {"expansion": expansion, "format": fmt}
    if user_group:
        params["user_group"] = user_group
    if start:
        params["start_date"] = str(start)
    if end:
        params["end_date"] = str(end)
    if colors:
        params["colors"] = colors
    for attempt in range(4):
        r = requests.get(API, params=params, headers={"User-Agent": UA}, timeout=60)
        if r.status_code in (403, 429):
            wait = 60 * (2 ** attempt)
            print(f"  rate-limited ({r.status_code}), backing off {wait}s")
            time.sleep(wait)
            continue
        r.raise_for_status()
        break
    else:
        raise RuntimeError(f"rate-limited after retries: {params}")
    data = r.json()
    cache.write_text(json.dumps(data))
    time.sleep(SLEEP)
    return data


def download_logs(s3_name):
    """Fetch the public draft+game log csv.gz for a format (spaces in 17Lands
    expansion names become underscores in S3 keys, e.g. Cube_-_Powered)."""
    RAW.mkdir(parents=True, exist_ok=True)
    paths = {}
    for sub in ("draft_data", "game_data"):
        f = RAW / f"{sub}_public.{s3_name}.PremierDraft.csv.gz"
        if not f.exists():
            url = f"{S3}/{sub}/{f.name}"
            print(f"downloading {url}")
            urllib.request.urlretrieve(url, f)
        paths[sub] = f
    return paths


def scryfall(refresh=False):
    """name -> (mana_value, type_line) from the Scryfall oracle bulk dump.
    Skips art-series/token/emblem objects that shadow real cards with mv 0."""
    import requests

    f = RAW / "scryfall_oracle.json"
    if refresh or not f.exists():
        meta = requests.get("https://api.scryfall.com/bulk-data",
                            headers={"User-Agent": UA}, timeout=60).json()
        uri = next(x["download_uri"] for x in meta["data"] if x["type"] == "oracle_cards")
        print(f"downloading {uri}")
        urllib.request.urlretrieve(uri, f)
    skip = {"art_series", "token", "double_faced_token", "emblem", "scheme", "vanguard"}
    out = {}
    for c in json.loads(f.read_text()):
        if c.get("layout") in skip or c.get("set_type") == "memorabilia":
            continue
        rec = (c.get("cmc", 0), c.get("type_line", ""))
        out[c["name"]] = rec
        if "//" in c["name"]:
            out[c["name"].split(" //")[0]] = rec
    return out
