"""General-purpose format-context primitives — reusable well beyond this
project's tax question. Each concept comes in a whole-format and a weekly form.

  top_cards(tag, ...)            best cards over the whole format
  top_cards_week(tag, window)    best cards in one weekly snapshot
  archetype_summary(tag)         archetype metagame share + win rate, whole format
  archetype_trends(tag)          archetype share + win rate, week by week
  biggest_movers(tag, ...)       cards whose ATA moved most over the season
  rarity_map(tag)                name -> rarity (from the cached stat tables)
"""
from pathlib import Path

import numpy as np
import pandas as pd

from . import data, weekly

ROOT = Path(__file__).parent.parent


def _weekly_tables(tag):
    """All weekly snapshots for a format with a rarity column where available."""
    w, _ = weekly.weekly_panel(tag)
    return w


def rarity_map(tag):
    w = _weekly_tables(tag)
    if "rarity" not in w.columns:
        return {}
    return w.dropna(subset=["rarity"]).groupby("name").rarity.first().to_dict()


# ------------------------------------------------------------ top cards -----
def top_cards(tag, by="gih_wr", rarity=None, n=15, min_gih=400):
    """Best cards over the WHOLE format (log-based per-card aggregates), with
    GIH/GP win rates, ATA, play rate, and rarity. `by` is a column to sort on;
    `rarity` filters to e.g. 'common' / 'uncommon'."""
    s = data.card_stats(tag)
    s = s[s.n_gih >= min_gih].copy()
    s["play_rate"] = s.n_gp / s.n_pool
    s["rarity"] = s.name.map(rarity_map(tag))
    if rarity is not None:
        rl = [rarity] if isinstance(rarity, str) else list(rarity)
        s = s[s.rarity.isin(rl)]
    cols = ["name", "rarity", "ata", "play_rate", "gih_wr", "gp_wr", "n_gih"]
    return s.sort_values(by, ascending=False)[cols].head(n).reset_index(drop=True)


def top_cards_week(tag, window=None, by="gih_wr", rarity=None, n=15, min_gih=150):
    """Best cards in ONE weekly snapshot (defaults to the latest week)."""
    w = _weekly_tables(tag)
    if window is None:
        window = sorted(w.window.unique())[-1]
    s = w[(w.window == window) & (w.n_gih >= min_gih)].copy()
    if rarity is not None and "rarity" in s.columns:
        rl = [rarity] if isinstance(rarity, str) else list(rarity)
        s = s[s.rarity.isin(rl)]
    keep = [c for c in ["name", "rarity", "ata", "alsa", "gih_wr", "gp_wr", "n_gih"] if c in s.columns]
    return s.sort_values(by, ascending=False)[keep].head(n).reset_index(drop=True), window


# ------------------------------------------------------------ archetypes ----
def archetype_trends(tag, min_n=2000, ncol=(2, 2)):
    """Per (archetype = main_colors, week) metagame share and win rate, plus
    win rate relative to that week's overall. The weekly time series. `ncol`
    bounds the number of colors (default 2 = clean color-pair metagame; widen
    to e.g. (2, 5) to include multicolor / Converge archetypes)."""
    import duckdb
    g = duckdb.connect().execute(
        f"WITH g AS (SELECT main_colors arch, draft_time, won::INT won "
        f"FROM '{ROOT}/data/{tag}_games.parquet' "
        f"WHERE LENGTH(main_colors) BETWEEN {ncol[0]} AND {ncol[1]}), "
        f"a AS (SELECT MIN(draft_time::DATE) d0 FROM g) "
        f"SELECT arch, CAST(FLOOR(DATEDIFF('day',(SELECT d0 FROM a),draft_time::DATE)/7) AS INT) wk, "
        f"COUNT(*) n, AVG(won) wr FROM g GROUP BY 1,2").df()
    tot = g.groupby("wk").n.sum().rename("n_wk")
    wrw = g.groupby("wk").apply(lambda d: np.average(d.wr, weights=d.n), include_groups=False).rename("wr_wk")
    g = g.join(tot, on="wk").join(wrw, on="wk")
    g["share"] = g.n / g.n_wk
    g["rel_wr"] = g.wr - g.wr_wk
    return g[g.n >= min_n].sort_values(["arch", "wk"]).reset_index(drop=True)


def archetype_summary(tag, min_n=4000):
    """Whole-format archetype metagame share and win rate (2-color mains)."""
    t = archetype_trends(tag, min_n=0)
    s = t.groupby("arch").apply(lambda d: pd.Series({
        "share_%": d.n.sum() / t.groupby("wk").n.sum().sum() * 100,
        "win_rate": np.average(d.wr, weights=d.n),
        "games": int(d.n.sum())}), include_groups=False)
    return s[s.games >= min_n].sort_values("share_%", ascending=False).reset_index()


# --------------------------------------------------------------- movers -----
def _archetype_wr_moves(tag):
    """Per archetype: first-to-last-fortnight change in win rate vs format (pp).
    Covers multicolor archetypes so movers' 3+-color decks are matched."""
    t = archetype_trends(tag, min_n=0, ncol=(2, 5))
    lo, hi = t.wk.min(), t.wk.max()
    out = {}
    for arch, g in t.groupby("arch"):
        e = g[g.wk <= lo + 1]; l = g[g.wk >= hi - 1]
        if len(e) and len(l):
            out[arch] = (np.average(l.rel_wr, weights=l.n) - np.average(e.rel_wr, weights=e.n)) * 100
    return out


def biggest_movers(tag, n=10, direction="up", min_gih=800, archetype=True):
    """The n cards whose ATA moved most over the season, in one direction:
    `direction="up"` = taken progressively EARLIER (discovered);
    `direction="down"` = taken progressively LATER (faded).

    Columns: ATA first/last/move, GIH win rate vs format before & after, and
    (retail formats) the card's most-played archetypes and shares (`mix`), plus
    that top archetype's own win-rate movement over the season (`top arch ΔWR`)
    — so you can see whether the card moved with its deck."""
    w, windows = weekly.weekly_panel(tag)
    _, allf = weekly.find_movers(w, tag, min_gih=min_gih)
    pool = allf[allf.move < 0].sort_values("move") if direction == "up" \
        else allf[allf.move > 0].sort_values("move", ascending=False)
    sel = pool.head(n)
    use_arch = archetype and tag in weekly.RETAIL
    amove = _archetype_wr_moves(tag) if use_arch else {}
    out = []
    for name in sel.index:
        g = w[w.name == name].sort_values("t")
        e = g[g.t <= g.t.min() + 1]; l = g[g.t >= g.t.max() - 1]
        gih_e = round(np.average(e.gih_wr_rel, weights=e.n_gih) * 100, 1)
        gih_l = round(np.average(l.gih_wr_rel, weights=l.n_gih) * 100, 1)
        row = {
            "name": name, "ata_first": round(sel.loc[name, "first"], 1),
            "ata_last": round(sel.loc[name, "last"], 1),
            "ata_move": round(sel.loc[name, "move"], 1),
            "GIH early": gih_e, "GIH late": gih_l}
        mix_str, arch_dwr = None, None
        if use_arch:
            mix = weekly.card_by_archetype(tag, name, windows)
            if len(mix):
                ms = mix.groupby("arch").n_gih.sum().sort_values(ascending=False)
                tot = ms.sum()
                mix_str = " / ".join(f"{a} {ms[a] / tot:.0%}" for a in ms.index[:3])
                arch_dwr = round(amove.get(ms.index[0], np.nan), 1)
            row["mix (top archetypes)"] = mix_str
        # the card's GIH move next to its top archetype's WR move, for comparison
        row["ΔGIH"] = round(gih_l - gih_e, 1)
        if use_arch:
            row["top arch ΔWR"] = arch_dwr
        out.append(row)
    return pd.DataFrame(out)
