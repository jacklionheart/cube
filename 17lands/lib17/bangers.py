"""Banger detection: cards that overperform for their rarity on 17Lands.

Replicates 17Lands' letter grades (https://blog.17lands.com/posts/using-win-rate-data/):
grades assume a normal distribution centered at C, each letter gradation a
band of 0.33 standard deviations of GIH WR, computed within whatever
population is being graded. We grade separately for the full population and
for top players; a card is a banger only if it clears its rarity's bar in
BOTH populations:

    common   >= B
    uncommon >= B+
    rare     >= A
    mythic   >= A+

Data sources, in order of preference:
  - card_tables.parquet: full-format website-table snapshots with
    all/top/middle/bottom cohorts (scraped June 2026; the live
    card_ratings API has since been gated and returns only stub counts).
  - The 17Lands public S3 game logs (lib17.fetch.s3 / lib17.data) — the
    long-term route to "every set ever"; per-set aggregation TBD.

Rows are normalized to {name, rarity, gih_wr, n_gih} regardless of source.
"""

import statistics
from pathlib import Path

GRADES = ["F", "D-", "D", "D+", "C-", "C", "C+", "B-", "B", "B+", "A-", "A", "A+"]
_C = GRADES.index("C")
_BAND = 0.33  # standard deviations per grade step

RARITY_BAR = {
    "common": GRADES.index("B"),
    "uncommon": GRADES.index("B+"),
    "rare": GRADES.index("A"),
    "mythic": GRADES.index("A+"),
}

DATA = Path(__file__).parent.parent / "data"


def rows_from_parquet(expansion, cohort, window="full"):
    """Normalized rows from the scraped website-table snapshots."""
    import pandas as pd

    df = pd.read_parquet(DATA / "card_tables.parquet")
    sub = df[(df.expansion == expansion) & (df.cohort == cohort) & (df.window == window)]
    if sub.empty:
        have = df[df.window == "full"].groupby(["expansion", "cohort"]).size()
        raise ValueError(
            f"no {expansion}/{cohort}/{window} snapshot in card_tables.parquet; have:\n{have}")
    return [
        {"name": r["name"], "rarity": (r.get("rarity") or "").lower(),
         "gih_wr": r["gih_wr"], "n_gih": r["n_gih"]}
        for r in sub.to_dict("records")
    ]


def assign_grades(rows, min_games):
    """{card name: (grade index, gih_wr, n_gih)} for rows with enough data.

    The z-score population is exactly the rows that pass min_games, mirroring
    how 17Lands redistributes grades when filters change.
    """
    graded_pop = [
        r for r in rows
        if r["gih_wr"] is not None and r["gih_wr"] == r["gih_wr"]  # NaN guard
        and (r["n_gih"] or 0) >= min_games
    ]
    if len(graded_pop) < 20:
        raise ValueError(f"only {len(graded_pop)} cards pass min_games={min_games}; not enough to grade")
    values = [r["gih_wr"] for r in graded_pop]
    mean = statistics.fmean(values)
    std = statistics.pstdev(values)
    out = {}
    for r in graded_pop:
        z = (r["gih_wr"] - mean) / std
        idx = max(0, min(len(GRADES) - 1, _C + round(z / _BAND)))
        out[r["name"]] = (idx, r["gih_wr"], r["n_gih"])
    return out


def bangers(expansion, min_games_all=500, min_games_top=100, window="full"):
    """Cards clearing their rarity bar for both all users and top users.

    Returns a list of dicts sorted by top-player grade, best first.
    """
    all_rows = rows_from_parquet(expansion, "all", window)
    top_rows = rows_from_parquet(expansion, "top", window)

    rarity = {r["name"]: r["rarity"] for r in all_rows}
    all_grades = assign_grades(all_rows, min_games_all)
    top_grades = assign_grades(top_rows, min_games_top)

    found = []
    for name in all_grades.keys() & top_grades.keys():
        bar = RARITY_BAR.get(rarity.get(name))
        if bar is None:  # basics, specials
            continue
        a_idx, a_wr, a_games = all_grades[name]
        t_idx, t_wr, t_games = top_grades[name]
        if a_idx >= bar and t_idx >= bar:
            found.append({
                "set": expansion,
                "name": name,
                "rarity": rarity[name],
                "grade_all": GRADES[a_idx],
                "grade_top": GRADES[t_idx],
                "gih_wr_all": round(a_wr, 4),
                "gih_wr_top": round(t_wr, 4),
                "games_all": int(a_games),
                "games_top": int(t_games),
            })
    found.sort(key=lambda r: (-top_grades[r["name"]][0], -r["gih_wr_top"]))
    return found
