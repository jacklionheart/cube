"""Weekly-panel and archetype machinery (promoted from the studies/ scripts).

Everything here reads the cached weekly stat-table snapshots and the public game
logs in <project>/data; nothing hits the network. Functions:

  weekly_panel(tag)        -> weekly card frame (GIH/GNS relativized to weekly
                              format means, week index t), + windows list
  find_movers(w, tag)      -> sustained ATA movers (fitted move + Spearman rho)
  residualize(p, col)      -> two-way (card + week) fixed-effect residual
  panel_slope(...)         -> within-card WR~ATA slope from residualized frame
  arch_baseline(tag)       -> per (archetype=main_colors, week) baseline WR,
                              aligned to the card-window grid
  card_by_archetype(...)   -> a card's GIH games + win rate by archetype & week
  season_split(g)          -> GIH change split into deck (ΔGNS) + individual
                              (ΔIIH), with IIH sampling SE
"""
from pathlib import Path

import numpy as np
import pandas as pd

from . import data

ROOT = Path(__file__).parent.parent
MIN_N = 150
MOVE_THRESH = {"sos": 0.8, "fin": 0.8, "tla": 0.8, "cube": 0.5}
RETAIL = {"sos": "SOS", "fin": "FIN", "tla": "TLA"}


def _q(name):
    return '"' + name.replace('"', '""') + '"'


def _cube_run(window):
    d = window.removeprefix("wk_")
    if d < "2026-02":
        return "Jan"
    if d < "2026-03-10":
        return "Feb-Mar"
    if d < "2026-05":
        return "Mar-Apr"
    return "May-Jun"


def weekly_panel(tag):
    """Weekly card frame: GIH/GNS relativized to weekly format means, with a
    week index t. Cube spans all four 2026 sessions (label in column `run`)."""
    if tag in RETAIL:
        w = data.weekly_tables(RETAIL[tag]).copy()
        w["run"] = "season"
    else:
        ct = pd.read_parquet(ROOT / "data" / "card_tables.parquet")
        w = ct[(ct.expansion == "CubePowered") & (ct.cohort == "all")
               & ct.window.str.startswith("wk_")].copy()
        w["run"] = w.window.map(_cube_run)
    w = w[w.n_gp >= MIN_N].dropna(subset=["alsa", "gp_wr", "gih_wr"]).copy()
    for m, n in [("gp_wr", "n_gp"), ("gih_wr", "n_gih"), ("gns_wr", "n_gns")]:
        if m in w.columns:
            sub = w.dropna(subset=[m, n])
            mu = sub.groupby("window").apply(
                lambda g: np.average(g[m], weights=g[n]), include_groups=False)
            w[m + "_rel"] = w[m] - w.window.map(mu)
    windows = sorted(w.window.unique())
    w["t"] = w.window.map({win: i for i, win in enumerate(windows)})
    return w.sort_values(["name", "t"]), windows


def find_movers(w, tag, min_gih=0):
    """Per-card fitted season ATA move and Spearman rho; sustained movers are
    |move| >= MOVE_THRESH and |rho| >= 0.6. Uses ata if present, else alsa."""
    from scipy.stats import spearmanr
    col = "ata" if ("ata" in w.columns and w.ata.notna().any()) else "alsa"
    w = w[w[col].notna()]
    rows = []
    for name, g in w.groupby("name"):
        if g.t.nunique() < (4 if tag == "cube" else 5) or g.n_gih.mean() < min_gih:
            continue
        x = g.t.to_numpy(float); y = g[col].to_numpy(); wt = g.n_gp.to_numpy(float)
        xm = np.average(x, weights=wt)
        slope = (wt*(x-xm)*(y-np.average(y, weights=wt))).sum() / (wt*(x-xm)**2).sum()
        rows.append({"name": name, "move": slope*(x.max()-x.min()),
                     "rho": spearmanr(x, y).statistic, "first": y[0], "last": y[-1]})
    f = pd.DataFrame(rows).set_index("name")
    movers = f[(f.move.abs() >= MOVE_THRESH[tag]) & (f.rho.abs() >= 0.6)]
    return movers.sort_values("move"), f


def residualize(p, col, wcol="n_gih", iters=40):
    """Two-way (card + week) weighted fixed-effect residual of p[col]."""
    r = p[col].astype(float).copy()
    for _ in range(iters):
        r = r - r.groupby(p.name).transform(lambda s: np.average(s, weights=p.loc[s.index, wcol]))
        r = r - r.groupby(p.window).transform(lambda s: np.average(s, weights=p.loc[s.index, wcol]))
    return r


def panel_slope(p, xr, yr, wcol="n_gih"):
    """Variance-weighted within-card slope = Σ w·xr·yr / Σ w·xr² (in pp)."""
    D = (p[wcol] * p[xr] ** 2).sum()
    return (p[wcol] * p[xr] * p[yr]).sum() / D * 100 if D > 0 else np.nan


def _edges(windows):
    e = list(pd.to_datetime([x.removeprefix("wk_") for x in sorted(windows)]))
    return e + [e[-1] + pd.Timedelta(days=7)]


def arch_baseline(tag, windows, ncol=(2, 5)):
    """Per (archetype=main_colors, week t) baseline win rate and its deviation
    from the weekly format mean, aligned to the card-window grid."""
    import duckdb
    edges = _edges(windows)
    g = duckdb.connect().execute(
        f"SELECT main_colors arch, draft_time::DATE dt, won::INT won "
        f"FROM '{ROOT}/data/{tag}_games.parquet' "
        f"WHERE LENGTH(main_colors) BETWEEN {ncol[0]} AND {ncol[1]}").df()
    g["t"] = pd.cut(pd.to_datetime(g.dt), bins=edges, labels=False, right=False)
    g = g.dropna(subset=["t"]); g["t"] = g.t.astype(int)
    aw = g.groupby(["arch", "t"]).won.agg(base="mean", base_n="size").reset_index()
    wrw = aw.groupby("t").apply(lambda d: np.average(d.base, weights=d.base_n), include_groups=False)
    aw["arch_rel"] = aw.base - aw.t.map(wrw)
    return aw


def card_by_archetype(tag, card, windows, ncol=(2, 5)):
    """A card's GIH games and win rate by (archetype, week). Returns an empty
    frame if the card has no columns in this format's game logs (e.g. cube
    cards that only appear in the 2026 weekly tables, not the Nov-2025 logs)."""
    import duckdb
    games = f"{ROOT}/data/{tag}_games.parquet"
    cols = {c[0] for c in duckdb.connect().execute(
        f"DESCRIBE SELECT * FROM '{games}' LIMIT 1").fetchall()}
    if f"deck_{card}" not in cols:
        return pd.DataFrame(columns=["arch", "t", "card_gih", "n_gih"])
    edges = _edges(windows)
    ih = f"(({_q('opening_hand_' + card)}+{_q('drawn_' + card)})>0)"
    g = duckdb.connect().execute(
        f"SELECT main_colors arch, draft_time::DATE dt, won::INT won, {ih}::INT inhand "
        f"FROM '{ROOT}/data/{tag}_games.parquet' "
        f"WHERE LENGTH(main_colors) BETWEEN {ncol[0]} AND {ncol[1]} AND {_q('deck_' + card)}>0").df()
    g["t"] = pd.cut(pd.to_datetime(g.dt), bins=edges, labels=False, right=False)
    g = g.dropna(subset=["t"]); g["t"] = g.t.astype(int)
    return g[g.inhand == 1].groupby(["arch", "t"]).won.agg(card_gih="mean", n_gih="size").reset_index()


def season_split(g):
    """First-vs-last-fortnight change in GIH (total, vs format), GNS (deck, vs
    format), and IIH = GIH-GNS (individual), with the IIH sampling SE.
    Requires gih_wr_rel, gns_wr_rel, gih_wr, gns_wr, n_gih, n_gns."""
    g = g.sort_values("t")
    e = g[g.t <= g.t.min() + 1]; l = g[g.t >= g.t.max() - 1]
    wm = lambda s, c, n: np.average(s[c], weights=s[n])
    d_gih = (wm(l, "gih_wr_rel", "n_gih") - wm(e, "gih_wr_rel", "n_gih")) * 100
    d_gns = (wm(l, "gns_wr_rel", "n_gns") - wm(e, "gns_wr_rel", "n_gns")) * 100
    iih = lambda s: wm(s, "gih_wr", "n_gih") - wm(s, "gns_wr", "n_gns")
    d_iih = (iih(l) - iih(e)) * 100
    var = lambda s: (wm(s, "gih_wr", "n_gih") * (1 - wm(s, "gih_wr", "n_gih")) / s.n_gih.sum()
                     + wm(s, "gns_wr", "n_gns") * (1 - wm(s, "gns_wr", "n_gns")) / s.n_gns.sum())
    return dict(d_gih=d_gih, d_gns=d_gns, d_iih=d_iih, se_iih=np.sqrt(var(e) + var(l)) * 100)
