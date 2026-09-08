"""Format registry, log -> parquet preparation, and the duckdb cell builders
shared by every analysis (formerly duplicated across five scripts)."""

from pathlib import Path

import numpy as np
import pandas as pd

from . import fetch

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"

# ---------------------------------------------------------------- formats ---
FORMATS = {
    "sos": dict(s3="SOS", api="SOS", label="Secrets of Strixhaven",
                table_window=("2026-04-21", "2026-06-11")),
    "fin": dict(s3="FIN", api="FIN", label="Final Fantasy",
                table_window=("2025-06-10", "2025-09-15")),
    "tla": dict(s3="TLA", api="TLA", label="Avatar: The Last Airbender",
                table_window=("2025-11-11", "2026-02-15")),
    "cube": dict(s3="Cube_-_Powered", api="Cube - Powered", label="Arena Powered Cube",
                 # public logs cover ONLY the first run (Oct 30 - Nov 19 2025);
                 # later runs are tables-only
                 table_window=("2026-05-28", "2026-06-11")),
}

# as-picked pick buckets: per-pick early (curvature), wider late; 15 = cube max
BUCKETS = [(1, 1), (2, 2), (3, 3), (4, 4), (5, 6), (7, 9), (10, 15)]
BUCKET_MID = {f"p{a}-{b}": (a + b) / 2 for a, b in BUCKETS}
EARLY = ["p1-1", "p2-2", "p3-3", "p4-4"]
LATE = ["p7-9", "p10-15"]
BUCKET_SQL = ("CASE " + " ".join(
    f"WHEN {{col}} BETWEEN {a} AND {b} THEN 'p{a}-{b}'" for a, b in BUCKETS) + " END")


def _q(name):
    return '"' + name.replace('"', '""') + '"'


def _con():
    import duckdb
    return duckdb.connect()


# ----------------------------------------------------------------- prep -----
def prep_logs(tag, force=False):
    """csv.gz logs -> {tag}_picks.parquet (pick_number normalized to 1-based)
    and {tag}_games.parquet. Skips work if the parquets exist."""
    picks_pq, games_pq = DATA / f"{tag}_picks.parquet", DATA / f"{tag}_games.parquet"
    if picks_pq.exists() and games_pq.exists() and not force:
        return picks_pq, games_pq
    paths = fetch.download_logs(FORMATS[tag]["s3"])
    con = _con()
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE _src AS
        SELECT draft_id, pick, pack_number, pick_number, pick_maindeck_rate,
               event_match_wins, event_match_losses, rank, draft_time
        FROM read_csv('{paths["draft_data"]}', header=true, auto_detect=true)""")
    con.execute(f"""
        COPY (SELECT * REPLACE (pick_number + (1 - (SELECT MIN(pick_number) FROM _src))
                                AS pick_number) FROM _src)
        TO '{picks_pq}' (FORMAT parquet)""")
    con.execute(f"""
        COPY (SELECT * FROM read_csv('{paths["game_data"]}', header=true, auto_detect=true))
        TO '{games_pq}' (FORMAT parquet)""")
    return picks_pq, games_pq


def game_card_names(con, games_pq, prefixes=("deck_",)):
    cols = {c[0] for c in con.execute(
        f"DESCRIBE SELECT * FROM '{games_pq}' LIMIT 1").fetchall()}
    cards = sorted({c[len("deck_"):] for c in cols if c.startswith("deck_")})
    matched = [c for c in cards if all(p + c in cols for p in prefixes)]
    dropped = sorted(set(cards) - set(matched))
    if dropped:
        print(f"WARNING: {len(dropped)} cards missing required game columns "
              f"(list churn), excluded: {', '.join(dropped[:6])}"
              + (" ..." if len(dropped) > 6 else ""))
    return matched


# -------------------------------------------------------- cell builders -----
def aspicked_cells(tag):
    """(card, taken-at bucket) cells: GP/GIH/OH/GNS counts & win rates,
    maindeck rate, picked count, event match WR. The core as-picked table."""
    picks_pq, games_pq = prep_logs(tag)
    con = _con()
    cards = game_card_names(con, games_pq,
                            ("deck_", "opening_hand_", "drawn_", "tutored_"))
    prefixes = ("deck_", "opening_hand_", "drawn_", "tutored_")
    sel = ", ".join(_q(p + c) for c in cards for p in prefixes)
    groups = ",\n".join("(" + ", ".join(_q(p + c) for p in prefixes)
                        + f") AS {_q(c)}" for c in cards)
    case_pn = BUCKET_SQL.format(col="pn")
    return con.execute(f"""
      WITH pk AS (
        SELECT draft_id, pick AS name, MIN(pick_number) AS pn,
               AVG(pick_maindeck_rate) AS md_rate,
               MAX(event_match_wins) AS w, MAX(event_match_losses) AS l
        FROM '{picks_pq}' GROUP BY draft_id, pick),
      pk2 AS (SELECT *, {case_pn} AS bucket FROM pk),
      pick_stats AS (
        SELECT name, bucket, AVG(md_rate) AS md_rate, COUNT(*) AS n_picked,
               SUM(w)::DOUBLE / NULLIF(SUM(w + l), 0) AS event_wr
        FROM pk2 GROUP BY 1, 2),
      long AS (
        SELECT name, draft_id, won, oh_n, drawn_n, tut_n FROM (
          UNPIVOT (SELECT draft_id, won::INT AS won, {sel} FROM '{games_pq}')
          ON {groups} INTO NAME name VALUE deck_n, oh_n, drawn_n, tut_n
        ) WHERE deck_n > 0),
      game_stats AS (
        SELECT l.name, b.bucket,
               COUNT(*)::BIGINT AS n_gp, AVG(l.won) AS gp_wr,
               SUM((l.oh_n + l.drawn_n > 0)::INT)::BIGINT AS n_gih,
               AVG(CASE WHEN l.oh_n + l.drawn_n > 0 THEN l.won END) AS gih_wr,
               SUM((l.oh_n > 0)::INT)::BIGINT AS n_oh,
               AVG(CASE WHEN l.oh_n > 0 THEN l.won END) AS oh_wr,
               SUM((l.oh_n + l.drawn_n + l.tut_n = 0)::INT)::BIGINT AS n_gns,
               AVG(CASE WHEN l.oh_n + l.drawn_n + l.tut_n = 0 THEN l.won END) AS gns_wr
        FROM long l JOIN pk2 b ON b.draft_id = l.draft_id AND b.name = l.name
        GROUP BY 1, 2)
      SELECT g.*, p.md_rate, p.n_picked, p.event_wr
      FROM game_stats g
      LEFT JOIN pick_stats p USING (name, bucket)
      ORDER BY g.name, g.bucket
    """).df()


def aspicked(tag, force=False):
    """Cached aspicked_cells with a pick_mid column."""
    pq = DATA / f"{tag}_aspicked.parquet"
    if force or not pq.exists():
        aspicked_cells(tag).to_parquet(pq, index=False)
    a = pd.read_parquet(pq)
    a["pick_mid"] = a.bucket.map(BUCKET_MID)
    return a


def fe_cells(tag, extra_select="", extra_col=None):
    """(card, bucket[, extra]) GP-WR cells for fixed-effect robustness checks.
    extra_select: SQL appended to the games scan (e.g. a rank or week column);
    extra_col: the column name it produces."""
    picks_pq, games_pq = prep_logs(tag)
    con = _con()
    cards = game_card_names(con, games_pq)
    groups = ",\n".join(f"({_q('deck_' + c)}) AS {_q(c)}" for c in cards)
    sel = ", ".join(_q("deck_" + c) for c in cards)
    case_pn = BUCKET_SQL.format(col="p.pn")
    ec = f", {extra_col}" if extra_col else ""
    return con.execute(f"""
      WITH pk AS (SELECT draft_id, pick AS name, MIN(pick_number) AS pn
                  FROM '{picks_pq}' GROUP BY 1, 2),
      long AS (SELECT name, draft_id, won{ec} FROM (
        UNPIVOT (SELECT draft_id, won::INT AS won{extra_select}, {sel} FROM '{games_pq}')
        ON {groups} INTO NAME name VALUE deck_n) WHERE deck_n > 0)
      SELECT l.name, {case_pn} AS bucket{ec and ', ' + extra_col},
             COUNT(*) AS n, AVG(l.won) AS gp_wr
      FROM long l JOIN pk p ON p.draft_id = l.draft_id AND p.name = l.name
      GROUP BY ALL
    """).df().assign(pick_mid=lambda d: d.bucket.map(BUCKET_MID))


def card_stats(tag):
    """Per-card whole-format aggregates from the logs: GP/OH/GD/GIH/GNS with
    counts, turn-stratified GNS (for the length-reweighted version), modal
    deck colors, ATA, pool/play counts."""
    picks_pq, games_pq = prep_logs(tag)
    con = _con()
    prefixes = ("deck_", "sideboard_", "opening_hand_", "drawn_", "tutored_")
    cards = game_card_names(con, games_pq, prefixes)
    sel = ", ".join(_q(p + c) for c in cards for p in prefixes)
    groups = ",\n".join("(" + ", ".join(_q(p + c) for p in prefixes)
                        + f") AS {_q(c)}" for c in cards)
    gns_strata = ", ".join(
        f"SUM((deck_n>0 AND oh_n+drawn_n+tut_n=0 AND tb={t})::INT) AS n_gns_t{t}, "
        f"AVG(CASE WHEN deck_n>0 AND oh_n+drawn_n+tut_n=0 AND tb={t} THEN won END) AS gns_wr_t{t}"
        for t in (1, 2, 3, 4))
    df = con.execute(f"""
      WITH long AS (
        SELECT name, won, main_colors, tb, deck_n, oh_n, drawn_n, tut_n FROM (
          UNPIVOT (SELECT won::INT AS won, main_colors,
                   CASE WHEN num_turns<=5 THEN 1 WHEN num_turns<=7 THEN 2
                        WHEN num_turns<=9 THEN 3 ELSE 4 END AS tb, {sel}
                   FROM '{games_pq}')
          ON {groups} INTO NAME name VALUE deck_n, sb_n, oh_n, drawn_n, tut_n
        ) WHERE deck_n + sb_n > 0)
      SELECT name,
        MODE(CASE WHEN deck_n>0 THEN main_colors END) AS modal_deck,
        COUNT(*) AS n_pool, SUM((deck_n>0)::INT) AS n_gp,
        AVG(CASE WHEN deck_n>0 THEN won END) AS gp_wr,
        SUM((deck_n>0 AND oh_n>0)::INT) AS n_oh,
        AVG(CASE WHEN deck_n>0 AND oh_n>0 THEN won END) AS oh_wr,
        SUM((deck_n>0 AND drawn_n>0)::INT) AS n_gd,
        AVG(CASE WHEN deck_n>0 AND drawn_n>0 THEN won END) AS gd_wr,
        SUM((deck_n>0 AND oh_n+drawn_n>0)::INT) AS n_gih,
        AVG(CASE WHEN deck_n>0 AND oh_n+drawn_n>0 THEN won END) AS gih_wr,
        SUM((deck_n>0 AND oh_n+drawn_n+tut_n=0)::INT) AS n_gns,
        AVG(CASE WHEN deck_n>0 AND oh_n+drawn_n+tut_n=0 THEN won END) AS gns_wr,
        {gns_strata}
      FROM long GROUP BY name
    """).df()
    tw = con.execute(f"""
      SELECT CASE WHEN num_turns<=5 THEN 1 WHEN num_turns<=7 THEN 2
                  WHEN num_turns<=9 THEN 3 ELSE 4 END AS tb, COUNT(*) AS n
      FROM '{games_pq}' GROUP BY 1""").df().set_index("tb").n
    tw = tw / tw.sum()
    num = sum(df[f"gns_wr_t{t}"].fillna(0) * df[f"n_gns_t{t}"].gt(0) * tw[t]
              for t in (1, 2, 3, 4))
    den = sum(df[f"n_gns_t{t}"].gt(0) * tw[t] for t in (1, 2, 3, 4))
    df["gns_wr_lenadj"] = (num / den).where(den > 0)
    ata = con.execute(f"""
      SELECT pick AS name, AVG(pick_number) AS ata, COUNT(*) AS n_picked
      FROM '{picks_pq}' GROUP BY 1""").df()
    return df.merge(ata, on="name", how="left")


# -------------------------------------------------------------- loaders -----
def card_table(expansion, window="full", cohort="all"):
    """One snapshot from the scraped website tables (card_tables.parquet)."""
    df = pd.read_parquet(DATA / "card_tables.parquet")
    return df[(df.expansion == expansion) & (df.window == window)
              & (df.cohort == cohort)].copy()


def weekly_tables(expansion):
    """Weekly table snapshots for the re-pricing panel. SOS lives in
    card_tables.parquet; FIN/TLA/CubeRun4 in e2_extra_weekly.parquet."""
    if expansion == "SOS":
        df = pd.read_parquet(DATA / "card_tables.parquet")
        return df[(df.expansion == "SOS") & (df.cohort == "all")
                  & df.window.str.startswith("wk_")].copy()
    df = pd.read_parquet(DATA / "e2_extra_weekly.parquet")
    return df[df.expansion == expansion].copy()
