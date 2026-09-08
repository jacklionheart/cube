"""lib17 — a small library for 17Lands limited-data analysis.

Modules:
  fetch    — data acquisition: 17Lands card_ratings API (cached, rate-limited),
             public S3 draft/game logs, Scryfall oracle bulk
  data     — format registry, log -> parquet preparation, cell builders,
             per-card aggregates, weekly stat-table snapshots
  metrics  — 17Lands metric definitions, their known biases, and corrected
             per-card quality/context measures (constants: KAPPA, BOOST_PER_PICK)
  analysis — cross-sectional designs: as-picked curves (card FE), robustness
             checks (pod / rank / week FE), re-pricing panel slope, kappa
  weekly   — weekly-panel + archetype machinery: weekly_panel, find_movers,
             residualize, arch_baseline, card_by_archetype, season_split
  htmlfmt  — shared HTML/figure styling for report pages

Every function reads from the local cache in <project>/data; nothing hits the
network except fetch.* (3s spacing, backoff — be a good 17Lands citizen).
"""
from . import fetch, data, metrics, analysis, weekly, overview, decks, htmlfmt  # noqa: F401
