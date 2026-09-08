"""Study designs and robustness checks.

Design A — as-picked (logs): same card taken at different picks, card FE.
Design B — re-pricing panel (weekly tables): WR ~ ALSA + card FE + week FE.
Plus the robustness battery the report's causal claims rest on.
"""

import numpy as np
import pandas as pd

from . import data
from .data import BUCKET_MID, EARLY, LATE


def _gwmean(d, by, val, w):
    t = pd.DataFrame({"v": d[val].to_numpy() * d[w].to_numpy(),
                      "w": d[w].to_numpy(), "by": d[by].to_numpy()})
    g = t.groupby("by")[["v", "w"]].sum()
    return (g.v / g.w).rename_axis(by)


# ------------------------------------------------------------- design A -----
def within_card(cells, m, n, min_n=25):
    """Pooled within-card curve and slope of metric m over taken-at position.
    Returns (curve indexed by pick_mid, slope_pp, card-clustered se_pp)."""
    d = cells.dropna(subset=[m, n, "pick_mid"]).copy()
    d = d[d[n] >= min_n]
    d["dev"] = d[m] - d.name.map(_gwmean(d, "name", m, n))
    curve = d.groupby("pick_mid").apply(
        lambda g: np.average(g.dev, weights=g[n]), include_groups=False)
    x = d.pick_mid - d.name.map(_gwmean(d, "name", "pick_mid", n))
    sxx = (d[n] * x * x).sum()
    beta = (d[n] * x * d.dev).sum() / sxx
    d = d.assign(u=d[n] * x * (d.dev - beta * x))
    se = np.sqrt(d.groupby("name").u.sum().pow(2).sum()) / sxx
    return curve, beta * 100, se * 100


def aspicked_slopes(tag):
    """All as-picked slopes for a format, pp per pick taken later."""
    a = data.aspicked(tag)
    out = {}
    for m, n in [("gp_wr", "n_gp"), ("gih_wr", "n_gih"), ("oh_wr", "n_oh"),
                 ("gns_wr", "n_gns"), ("event_wr", "n_picked"),
                 ("md_rate", "n_picked")]:
        _, b, se = within_card(a, m, n)
        out[m] = (b, se)
    return out


def early_late(tag, min_n=300, metric=("gih_wr", "n_gih")):
    """Per-card early (picks 1-4) vs late (7+) comparison with binomial SEs.
    No draft clustering — treat per-card z's as looser than pooled slopes."""
    a = data.aspicked(tag)
    m, n = metric

    def side(buckets, suffix):
        s = a[a.bucket.isin(buckets)]
        t = pd.DataFrame({"name": s.name.to_numpy(),
                          "wv": s[m].fillna(0).to_numpy() * s[n].to_numpy(),
                          "n": s[n].to_numpy()})
        g = t.groupby("name")[["wv", "n"]].sum()
        return pd.DataFrame({f"wr_{suffix}": (g.wv / g.n).where(g.n > 0),
                             f"n_{suffix}": g.n})

    pc = side(EARLY, "e").join(side(LATE, "l"), how="inner").dropna()
    pc = pc[(pc.n_e >= min_n) & (pc.n_l >= min_n)].copy()
    pc["diff"] = (pc.wr_l - pc.wr_e) * 100
    pc["se"] = np.sqrt(pc.wr_e * (1 - pc.wr_e) / pc.n_e
                       + pc.wr_l * (1 - pc.wr_l) / pc.n_l) * 100
    pc["z"] = pc["diff"] / pc.se
    return pc


# ------------------------------------------------- design A robustness ------
def _cells_slope(cells, fe_extra=None):
    import statsmodels.formula.api as smf
    cells = cells[cells.n >= 25].dropna(subset=["pick_mid"]).reset_index(drop=True)
    f = "gp_wr ~ pick_mid + C(name)" + (f" + C({fe_extra})" if fe_extra else "")
    m = smf.wls(f, data=cells, weights=cells.n).fit(
        cov_type="cluster", cov_kwds={"groups": cells.name})
    return m.params["pick_mid"] * 100, m.bse["pick_mid"] * 100


def slope_with_rank_fe(tag):
    cells = data.fe_cells(tag,
        extra_select=", CASE WHEN rank IN ('diamond','mythic') THEN 'hi' "
                     "WHEN rank='platinum' THEN 'mid' "
                     "WHEN rank IS NULL THEN 'na' ELSE 'lo' END AS rk",
        extra_col="rk")
    return _cells_slope(cells), _cells_slope(cells, "rk")


def slope_with_week_fe(tag):
    cells = data.fe_cells(tag, extra_select=", strftime(draft_time, '%Y-%W') AS wk",
                          extra_col="wk")
    return _cells_slope(cells), _cells_slope(cells, "wk")


def slope_with_pod_control(tag):
    """Leave-one-out pool-acquisition (pod generosity) quintile control.
    NOTE: whole-draft and color-agnostic — same-color lane openness is NOT
    controlled and remains a live alternative for part of the premium."""
    import duckdb
    picks_pq, games_pq = data.prep_logs(tag)
    con = duckdb.connect()
    con.execute(f"CREATE TEMP TABLE ata AS SELECT pick AS name, "
                f"AVG(pick_number) AS ata FROM '{picks_pq}' GROUP BY 1")
    con.execute(f"""
      CREATE TEMP TABLE pk2 AS
      WITH steal AS (SELECT p.draft_id, p.pick AS name, p.pick_number,
                            (a.ata - p.pick_number) AS s
                     FROM '{picks_pq}' p JOIN ata a ON a.name = p.pick),
      firsts AS (SELECT draft_id, name, MIN(pick_number) AS pn FROM steal GROUP BY 1, 2),
      gd AS (SELECT draft_id, SUM(s) AS tot, COUNT(*) AS n FROM steal GROUP BY 1)
      SELECT f.draft_id, f.name, f.pn,
             NTILE(5) OVER (ORDER BY (gd.tot - (a.ata - f.pn)) / (gd.n - 1)) AS gq
      FROM firsts f JOIN gd USING (draft_id) JOIN ata a ON a.name = f.name""")
    cards = data.game_card_names(con, games_pq)
    groups = ",\n".join(f"({data._q('deck_' + c)}) AS {data._q(c)}" for c in cards)
    sel = ", ".join(data._q("deck_" + c) for c in cards)
    case_pn = data.BUCKET_SQL.format(col="p.pn")
    cells = con.execute(f"""
      WITH long AS (SELECT name, draft_id, won FROM (
        UNPIVOT (SELECT draft_id, won::INT AS won, {sel} FROM '{games_pq}')
        ON {groups} INTO NAME name VALUE deck_n) WHERE deck_n > 0)
      SELECT l.name, p.gq, {case_pn} AS bucket, COUNT(*) AS n, AVG(l.won) AS gp_wr
      FROM long l JOIN pk2 p ON p.draft_id = l.draft_id AND p.name = l.name
      GROUP BY 1, 2, 3""").df().assign(pick_mid=lambda d: d.bucket.map(BUCKET_MID))
    return _cells_slope(cells), _cells_slope(cells, "gq")


def staples_cohort(tag="sos"):
    """Pre-specified no-filter cohort (md_early>70%, md drop<10pp): pooled
    within-card late premium — the pure opportunity-cost reading."""
    a = data.aspicked(tag)

    def agg(buckets):
        s = a[a.bucket.isin(buckets)]
        return s.groupby("name").apply(lambda x: pd.Series({
            "md": np.average(x.md_rate.dropna(),
                             weights=x.loc[x.md_rate.notna(), "n_picked"])
            if x.md_rate.notna().any() else np.nan,
            "wr": (x.gih_wr * x.n_gih).sum() / x.n_gih.sum() if x.n_gih.sum() else np.nan,
            "n": x.n_gih.sum()}), include_groups=False)

    j = agg(EARLY).join(agg(LATE), lsuffix="_e", rsuffix="_l").dropna()
    j = j[(j.n_e >= 300) & (j.n_l >= 300)]
    cohort = j[(j.md_e > 0.70) & (j.md_e - j.md_l < 0.10)]
    prem = np.average(cohort.wr_l - cohort.wr_e, weights=cohort.n_l) * 100
    se = np.sqrt(np.average(((cohort.wr_l - cohort.wr_e) * 100 - prem) ** 2,
                            weights=cohort.n_l) / max(len(cohort) - 1, 1))
    return prem, se, list(cohort.index)


def class_late_premium(tag, names):
    """Pre-specified class test: inverse-variance-weighted mean of WITHIN-card
    late-early GIH diffs for a card class vs the rest."""
    pc = early_late(tag, min_n=100)
    pc["w"] = 1 / (pc.se ** 2)

    def cls(sub):
        c = pc[sub]
        return np.average(c["diff"], weights=c.w), np.sqrt(1 / c.w.sum()), len(c)

    in_cls = cls(pc.index.isin(names))
    out_cls = cls(~pc.index.isin(names))
    return in_cls, out_cls


# ------------------------------------------------------------- design B -----
def weekly_panel(expansion, outcome="gp_wr", n_col="n_gp", min_n=150):
    """WR ~ ALSA + card FE + week FE on weekly table snapshots, clustered by
    card. Slope is per ALSA pick (divide by metrics.KAPPA for taken-at units).
    CAVEATS: identification is concentrated in weeks 1-2; selection-into-
    re-pricing + mean reversion can generate part of the slope; archetype
    tides ride along (see congestion())."""
    import statsmodels.formula.api as smf
    w = data.weekly_tables(expansion)
    p = w[w[n_col] >= min_n].dropna(subset=[outcome, "alsa", n_col]).reset_index(drop=True)
    keep = p.groupby("name").window.nunique()
    p = p[p.name.isin(keep[keep >= 3].index)].reset_index(drop=True)
    m = smf.wls(f"{outcome} ~ alsa + C(name) + C(window)", data=p,
                weights=p[n_col]).fit(cov_type="cluster",
                                      cov_kwds={"groups": p.name})
    return m.params["alsa"] * 100, m.bse["alsa"] * 100, len(p)


def kappa():
    """Within-card weekly dATA/dALSA on SOS (the units conversion), with SE."""
    import statsmodels.formula.api as smf
    p = data.weekly_tables("SOS")
    p = p[p.n_picked >= 150].dropna(subset=["ata", "alsa"]).reset_index(drop=True)
    keep = p.groupby("name").window.nunique()
    p = p[p.name.isin(keep[keep >= 3].index)].reset_index(drop=True)
    m = smf.wls("ata ~ alsa + C(name) + C(window)", data=p,
                weights=p.n_picked).fit(cov_type="cluster",
                                        cov_kwds={"groups": p.name})
    return m.params["alsa"], m.bse["alsa"]
