"""Deck-composition win-rate primitives — general "which cards/packages win
together" analysis on the public game logs.

A *deck condition* is expressed by card presence: a card is "in the deck" when
its `deck_<card>` column is > 0. These helpers build the (heavily quoted)
duckdb queries so analyses don't re-roll them.

  deck_card_names(tag)              cards that have a deck_ column in the logs
  wr(tag, require=, exclude=)       GP WR + n for decks matching presence rules
  cooccurrence_wr(tag, anchor,      for each candidate: WR of `anchor` decks
                  candidates)       that also run it, and its synergy lift
                                    (WR with anchor − WR without anchor)
  count_bucket_wr(tag, members,     GP WR bucketed by how many of `members` the
                  within=)          deck runs (0/1/2/3+), optionally within a
                                    subset of decks (e.g. those running Flash)
  count_grid_wr(tag, rows, cols,    2-D GP WR + n by counts of two member sets
                within=)            (e.g. # threats × # enablers) — disentangle
                                    two correlated deck-density axes
  synergy_matrix(tag, rows, cols)   pairwise GP WR / lift for every (row × col)
                                    co-occurrence (NB: lifts are co-occurrence,
                                    not isolated marginal effects — see notebook)

`tag` is a format key (e.g. "cube"); games come from data/<tag>_games.parquet.
All win rates are GP WR (deck-level: a game counts if the card was maindecked).
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent.parent


def _q(c):
    return '"' + c.replace('"', '""') + '"'


def _games(tag):
    return f"{ROOT}/data/{tag}_games.parquet"


def _con():
    import duckdb
    return duckdb.connect()


def _present(card):
    return f"{_q('deck_' + card)} > 0"


def _clause(require=(), exclude=()):
    parts = [_present(c) for c in require] + [f"NOT {_present(c)}" for c in exclude]
    return " AND ".join(parts) if parts else "TRUE"


def deck_card_names(tag):
    con = _con()
    cols = {c[0] for c in con.execute(f"DESCRIBE SELECT * FROM '{_games(tag)}' LIMIT 1").fetchall()}
    return sorted(c[len("deck_"):] for c in cols if c.startswith("deck_"))


def wr(tag, require=(), exclude=()):
    """(n_games, GP WR) for decks satisfying the presence conditions."""
    n, w = _con().execute(
        f"SELECT COUNT(*), AVG(won::INT) FROM '{_games(tag)}' WHERE {_clause(require, exclude)}").fetchone()
    return int(n), (float(w) if w is not None else np.nan)


def cooccurrence_wr(tag, anchor, candidates, min_n=1):
    """For each candidate card: GP WR of `anchor` decks that also run it, the
    candidate's win rate in decks WITHOUT the anchor, and the synergy lift
    (with − without, pp). `anchor=None` treats all decks as the anchor set.
    Sorted by WR-with-anchor descending."""
    rows = []
    base = [anchor] if anchor else []
    for c in candidates:
        n_w, w_w = wr(tag, require=base + [c])
        n_o, w_o = wr(tag, require=[c], exclude=base) if anchor else (0, np.nan)
        if n_w < min_n:
            continue
        rows.append({
            "card": c,
            "n (+anchor)": n_w, "WR (+anchor)": round(w_w, 3),
            "n (no anchor)": n_o, "WR (no anchor)": round(w_o, 3) if not np.isnan(w_o) else None,
            "synergy lift (pp)": round((w_w - w_o) * 100, 1) if not np.isnan(w_o) else None})
    return pd.DataFrame(rows).sort_values("WR (+anchor)", ascending=False).reset_index(drop=True)


def synergy_matrix(tag, rows, cols, within=(), baseline="row", min_n=30):
    """Pairwise GP WR for every (row card × col card) co-occurrence, optionally
    within a subset of decks. Returns three aligned DataFrames (rows × cols):
      W  — GP WR of decks running both (NaN if n < min_n)
      N  — game counts
      L  — lift: W minus the per-row baseline (baseline="row", each row card's
           own WR), per-col baseline ("col"), or W itself ("none").
    Use for "which enabler pairs best with which threat" heatmaps."""
    rows, cols = list(rows), list(cols)
    W = pd.DataFrame(index=rows, columns=cols, dtype=float)
    N = pd.DataFrame(index=rows, columns=cols, dtype=float)
    for r in rows:
        for c in cols:
            n, w = wr(tag, require=list(within) + [r, c])
            N.loc[r, c] = n
            W.loc[r, c] = w if n >= min_n else np.nan
    if baseline == "row":
        base = {r: wr(tag, require=list(within) + [r])[1] for r in rows}
        L = W.sub(pd.Series(base), axis=0)
    elif baseline == "col":
        base = {c: wr(tag, require=list(within) + [c])[1] for c in cols}
        L = W.sub(pd.Series(base), axis=1)
    else:
        L = W.copy()
    return W, N, L


def _bucketize(k, edges):
    if k == 0:
        return "0"
    for b in edges[:-1]:
        if k == b:
            return str(b)
    return f"{edges[-1]}+" if k >= edges[-1] else str(k)


def count_grid_wr(tag, row_members, col_members, within=(),
                  row_buckets=(1, 2), col_buckets=(1, 2)):
    """2-D GP WR (and n) by how many of `row_members` and `col_members` a deck
    runs, within decks containing all `within` cards. Returns (wr_pivot,
    n_pivot). Use to disentangle two correlated deck axes (e.g. # threats vs #
    enablers)."""
    rc = " + ".join(f"({_present(c)})::INT" for c in row_members)
    cc = " + ".join(f"({_present(c)})::INT" for c in col_members)
    df = _con().execute(
        f"SELECT ({rc}) AS kr, ({cc}) AS kc, won::INT AS won "
        f"FROM '{_games(tag)}' WHERE {_clause(require=within)}").df()
    df["row"] = df.kr.map(lambda k: _bucketize(k, list(row_buckets)))
    df["col"] = df.kc.map(lambda k: _bucketize(k, list(col_buckets)))
    wrp = df.pivot_table(index="row", columns="col", values="won", aggfunc="mean")
    npv = df.pivot_table(index="row", columns="col", values="won", aggfunc="size")
    ro = ["0"] + [str(b) for b in row_buckets[:-1]] + [f"{row_buckets[-1]}+"]
    co = ["0"] + [str(b) for b in col_buckets[:-1]] + [f"{col_buckets[-1]}+"]
    wrp = wrp.reindex(index=[r for r in ro if r in wrp.index], columns=[c for c in co if c in wrp.columns])
    npv = npv.reindex(index=wrp.index, columns=wrp.columns)
    return wrp, npv


def count_bucket_wr(tag, members, within=(), buckets=(1, 2, 3), labels=None):
    """GP WR bucketed by how many cards from `members` a deck runs, restricted
    to decks that contain all cards in `within`. `buckets` are the inclusive
    upper edges of the named buckets; everything above the last is "Nlast+".
    Returns a frame with the count bucket, n, and GP WR."""
    cnt = " + ".join(f"({_present(c)})::INT" for c in members)
    con = _con()
    df = con.execute(
        f"SELECT ({cnt}) AS k, won::INT AS won FROM '{_games(tag)}' "
        f"WHERE {_clause(require=within)}").df()
    edges = list(buckets)

    def lab(k):
        if k == 0:
            return "0"
        for b in edges[:-1]:
            if k == b:
                return str(b)
        return f"{edges[-1]}+" if k >= edges[-1] else str(k)
    df["bucket"] = df.k.map(lab)
    g = df.groupby("bucket").won.agg(n="size", gp_wr="mean").reset_index()
    g["gp_wr"] = g.gp_wr.round(3)
    order = ["0"] + [str(b) for b in edges[:-1]] + [f"{edges[-1]}+"]
    g["_o"] = g.bucket.map({b: i for i, b in enumerate(order)})
    return g.sort_values("_o").drop(columns="_o").reset_index(drop=True)
