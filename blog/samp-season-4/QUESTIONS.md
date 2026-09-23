# Open questions to resolve after reading the blog post

Deferred design/stats decisions, grouped by section. Nothing here blocks
reading `../site/samp-season-4/index.html`; these are the knobs we skipped past.

## Packages (Sacrifice / Discard)
- **Membership cutoff.** Cluster cards = backbone-depth ≥ 4 (gives the 14-card
  Sacrifice incl. Lord Skitter at depth 4). Keep the cut at 4, or tighten to
  5 (drops Lord Skitter → 13) / 6 (core only → 10)?
- **Deck-tag threshold.** A deck "runs" a package if it maindecks ≥ min(4,
  |cluster|−1). You said "close either way" — lock it at 4?
- **Cluster naming.** Sac/Discard are currently *selected* by seed cards
  (Yawgmoth… / Cool but Rude…). The clusters are algorithmic; only the label
  is hand-set. Want fully-automatic naming, or is seed-to-name fine?
- **WR definition.** Currently pooled match records of the tagged decks
  (deck-level). Alternatives considered: "any constituent strict team"
  (package-level) and average-of-deck-WR. Confirm pooled + deck-level.

## Green (graveyard vs landfall)
- **Emphasis vs overlap.** The 57%-vs-44% signal lives in *emphasis* (more
  landfall cards than graveyard). You asked for "allow multiple, avoid 0,"
  but overlapping membership washes the signal (29/44 decks become "both,"
  all ~50%). Decision: keep the emphasis lean (exclusive-ish, strong signal)
  or a graded weight like blue's?
- **Payoff lists need curation.** Icetill Explorer, Mole Man, Sandman read as
  *both* graveyard and landfall from oracle text. Hand-split them.
- **The "balanced/neither" bucket** (8 decks, 41%) — fold in or keep separate?

## Blue (soft W/R/B/G coloring)
- **Double-printings.** Wan Shi Tong and Jace each have two versions and land
  in two groups — dedup before it's final.
- **Tie-break.** Max-weight ties currently break W→R→B→G. OK?
- **Staple threshold.** Blue groups use maindecked ≥ 6. Right cutoff?

## White (functional tags)
- **Curate the tags.** Auto-removal false-positives on blink cards
  (Ephemerate, Restoration Angel) and Lingering Souls; Aggro is a hand seed.
  Make a curatable `white_tags.tsv` (like `team_themes.tsv`)?
- **Metric.** Deck-level "few vs many" split at the median count. Prefer a
  finer breakdown (e.g. WR vs exact count) or a lean weight?

## Cross-cutting
- **Sheet vs blog.** Sacrifice + Discard are already an "Archetypes" sheet tab.
  Should Green/Blue/White get sheet tabs too, or stay blog-only?
- **Support level.** Locked at 6 to match intuition. Later: the tolerance
  mechanism that lets us raise support and still recover these clusters.
- **Fine-comb pass** on all the auto-classified card lists (your "fine comb
  the data later").
