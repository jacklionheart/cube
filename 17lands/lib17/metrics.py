"""17Lands metric definitions, their known biases, and corrected measures.

The raw metrics (per card):
  GP WR   win rate of games with the card maindecked. Deck-level; per-card
          signal is diluted ~1/23, but it's the only stat that charges
          build-arounds their deckbuilding tax.
  GIH WR  win rate of games where the card reached hand. BIAS: oversamples
          long games (inflates slow/blue decks' cards ~3-5pp).
  OH WR   win rate with the card in the kept opening seven. BIAS: kept-hand
          mulligan selection + the early-game slice penalize expensive and
          scaling cards monotonically in mana value (~3.7pp spread MV0->6+).
  GD WR   drawn after the opener. BIAS: long-game oversampling, anti-aggro.
  GNS WR  card maindecked but never seen — the control group: deck context
          with zero card contribution. BIAS: oversamples SHORT games (fewer
          cards seen), inflating fast decks' context; corrected here by
          reweighting turn strata to the format distribution.
  ALSA/ATA average last-seen / actually-taken pick. ALSA is compressed by
          passes: within-card dATA/dALSA = KAPPA below.

Corrected quality (the "v3 effect"): mean of the two within-deck contrasts
(OH WR - GP WR, GD WR - GP WR), each demeaned within a mana-value bucket
whose baseline EXCLUDES Power (else every cheap artifact is taxed for not
being Black Lotus), then shrunk toward zero in proportion to sampling noise
(empirical Bayes) before ranking. Quantile-mapped onto the in-hand effect
distribution to express it in familiar GIH units.
"""

import numpy as np
import pandas as pd

POWER = {"Black Lotus", "Mox Sapphire", "Mox Jet", "Mox Ruby", "Mox Pearl",
         "Mox Emerald", "Time Walk", "Ancestral Recall", "Timetwister",
         "Sol Ring", "Mana Crypt"}

# within-card dATA/dALSA, SOS weekly tables (robustness: analysis.kappa()).
# Cross-card static slopes run 1.49-1.65 by format; treat as +-10%.
KAPPA = 1.546

# pooled as-picked lateness slopes, pp of WR per pick taken later, by format
# (analysis.aspicked_slopes; card-clustered SEs 0.006-0.011)
BOOST_PER_PICK = {
    "sos": {"gp_wr": 0.131, "gih_wr": 0.135, "oh_wr": 0.095, "gns_wr": 0.154},
    "fin": {"gp_wr": 0.096, "gih_wr": 0.100, "oh_wr": 0.082, "gns_wr": 0.124},
    "tla": {"gp_wr": 0.091, "gih_wr": 0.075, "oh_wr": 0.058, "gns_wr": 0.121},
    "cube": {"gp_wr": 0.084, "gih_wr": 0.074, "oh_wr": 0.052, "gns_wr": 0.089},
}

MIN_GIH = 400  # default per-card sample floor


def wmean(d, col, w):
    d = d.dropna(subset=[col])
    return np.average(d[col], weights=d[w]) if len(d) else np.nan


def format_mean(stats):
    """Deck-game-weighted mean GP WR over ALL cards (the format baseline)."""
    sa = stats.dropna(subset=["gp_wr"])
    return (sa.n_gp * sa.gp_wr).sum() / sa.n_gp.sum()


def card_quality(stats, scry, min_gih=MIN_GIH):
    """Per-card corrected measures from data.card_stats output + a scryfall
    lookup. Returns the stats frame with added columns:
      context        GNS elevation vs format mean, game-length-reweighted
      effect_v3      cost-adjusted within-deck effect (Power-free baselines)
      effect_shrunk  EB-shrunk effect (rank on this)
      se_v3          sampling SE of effect_v3
      adj_gih_wr     quality in an average deck, GIH units
      lam_early      P(maindeck | taken picks 1-4), where measured
      early_gih_wr   expected GIH if prioritized (quality x lam_early)
    """
    s = stats.copy()
    mu = format_mean(s)
    s = s[(s.n_gih >= min_gih) & (s.n_gns >= min_gih)].dropna(
        subset=["gp_wr", "oh_wr", "gd_wr", "gih_wr", "gns_wr"]).copy()
    s["cmc"] = s.name.map(lambda n: scry.get(n, (np.nan, ""))[0])
    s["type"] = s.name.map(lambda n: scry.get(n, (np.nan, ""))[1])
    unmatched = s[s.cmc.isna()]
    if len(unmatched):
        print(f"WARNING: {len(unmatched)} cards missing from scryfall dump, "
              f"excluded: {', '.join(unmatched.name.head(6))}")
        s = s[s.cmc.notna()].copy()

    s["mu"] = mu
    s["pct_gp"] = s.n_gp / s.n_pool
    s["context_raw"] = s.gns_wr - mu
    s["context"] = s.gns_wr_lenadj - mu
    s["oh_eff"] = s.oh_wr - s.gp_wr
    s["gd_eff"] = s.gd_wr - s.gp_wr
    s["effect_iih"] = s.gih_wr - s.gns_wr
    s["bucket"] = np.where(s.type.str.contains("Land", na=False), "land",
                           s.cmc.clip(upper=6).astype(int).astype(str))
    base = s[~s.name.isin(POWER)]
    for col, n in [("oh_eff", "n_oh"), ("gd_eff", "n_gd")]:
        bm = base.groupby("bucket").apply(lambda g: wmean(g, col, n),
                                          include_groups=False)
        s[col + "_adj"] = s[col] - s.bucket.map(bm)
    s["effect_v3"] = (s.oh_eff_adj + s.gd_eff_adj) / 2
    s["se_v3"] = 0.5 * np.sqrt(s.oh_wr * (1 - s.oh_wr) / s.n_oh
                               + s.gd_wr * (1 - s.gd_wr) / s.n_gd)
    var_sig = max(np.average((s.effect_v3 - wmean(s, "effect_v3", "n_gih")) ** 2,
                             weights=s.n_gih) - (s.se_v3 ** 2).mean(), 1e-6)
    s["effect_shrunk"] = s.effect_v3 * var_sig / (var_sig + s.se_v3 ** 2)

    iih_sorted = np.sort(s.effect_iih.values)
    ranks = (s.effect_shrunk.rank(method="first") - 1).astype(int).clip(0, len(s) - 1)
    s["adj_gih_wr"] = mu + iih_sorted[ranks]
    return s


def attach_early_deployment(quality, aspicked, min_picked=200):
    """Add lam_early (P(maindeck | taken picks 1-4)) and early_gih_wr.
    Falls back to overall play rate where the early sample is too thin to
    mean anything (a 12-ATA card taken early 30 times is self-selected)."""
    from .data import EARLY
    s = quality.copy()
    early = aspicked[aspicked.bucket.isin(EARLY)].dropna(subset=["md_rate"])
    eg = early.groupby("name").agg(md=("md_rate", "mean"), n=("n_picked", "sum"))
    s["lam_early"] = s.name.map(eg[eg.n >= min_picked].md).fillna(s.pct_gp).clip(0, 1)
    iih_sorted = np.sort(s.effect_iih.values)
    ranks = (s.effect_shrunk.rank(method="first") - 1).astype(int).clip(0, len(s) - 1)
    s["early_gih_wr"] = s.mu + s.lam_early * iih_sorted[ranks]
    return s
