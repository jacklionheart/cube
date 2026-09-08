# Project notes — confounders, hypotheses, and what worked

Companion to `notebooks/00_master.ipynb`. The notebook reproduces the analyses;
this file is the exhaustive prose record so the notebook stays runnable rather
than gigantic. Everything here was established in the session that built the
project; numbers are SOS unless noted, "pp" = percentage points of win rate,
"per pick" = per pick a card was actually taken at (ATA), not ALSA.

---

## 1. The question and the estimands

**Goal.** Separate two reasons a card has high 17Lands win-rate stats: (a) it is
genuinely strong, so it gets picked early *and* wins; (b) its stats are inflated
*because* it is picked late. Produce an "adjusted" win rate comparable across
cards regardless of where they are taken.

**The mechanism we are trying to measure — the "ATA tax" / "slept-on boost".**
A card taken later was acquired more cheaply (lower opportunity cost), so the
deck around it has better surrounding pieces. It is fundamentally a *deck-quality*
effect, so it must show up in **GNS WR** (games-not-seen: the card's decks'
win rate when the card was never drawn), not in the card's own in-hand value.

**Estimands that came up (they are NOT the same number):**
- **Per-pick tax (the core):** at a common counterfactual, how much WR does one
  pick of lateness add? Measured cleanly by the as-picked design. ≈ +0.10–0.15pp
  GIH per taken-at pick; loads largest on GNS.
- **"If picked early" (estimand B):** a card's expected stats if you *start*
  taking it early — must shrink the in-hand effect by play rate, because an
  early pick forfeits the deployment filter (see §2.2).
- **Pricing-policy counterfactual (Aang vs Teferi):** a *bundle* — position,
  deployment breadth, deck mix, pilot mix. Nested E1 (position) ⊂ E2 (+deploy)
  ⊂ E3 (+deck context). Even E3 is partial (can't swap signal value,
  equilibrium, tempo-vs-control identity, intent).
- **Discovery counterfactual:** what happens to printed stats when the *crowd*
  re-prices a card. This is what the weekly panel measures, and it is NOT the
  per-pick tax (§3).

---

## 2. The metrics and their biases (lib17/metrics.py)

| metric | conditions on | bias to remember |
|---|---|---|
| GP WR | card in maindeck | deck-level; per-card signal ~1/23 diluted; **only metric that charges build-around deckbuilding tax** |
| GIH WR | card reached hand | **game-length bias: oversamples long games** → inflates slow/blue/control ~3–5pp |
| OH WR | card in kept opener | mulligan-keep clunk + early slice → **monotone CMC penalty** (+1.7pp at MV0 → −2.0pp at MV6+) |
| GD WR | drawn after opener | long-game oversampling, anti-aggro |
| GNS WR | in deck, never seen | **the deck-context control group** (zero card effect); but **oversamples SHORT games** → inflates fast/aggro context ~+0.5–1pp; length-correct it |
| IIH = GIH−GNS | within-deck draw-vs-not | the **card-individual** signal; deck-quality and pilot skill cancel by construction (within-game contrast) |
| ALSA / ATA | last-seen / taken pick | ALSA compressed by passes; **within-card dATA/dALSA = 1.546 ± 0.028** (κ), nonlinear & rarity-dependent |

**Key identity:** `GIH = GNS + IIH`. GNS = deck (archetype mix + tide + build +
pilot). IIH = the card's own marginal in-hand value, *immune to deck quality and
pilot skill* — except a genuine **card×support interaction** for build-arounds
(a card drawn into a deck that supports it wins more when drawn; as it spreads to
worse-fitting decks IIH falls — that is legitimately the card's effective value
declining, e.g. Chocobo Racetrack, FIN).

---

## 3. The two designs (and why they disagree)

**Design A — as-picked (the trustworthy one).** From the public draft+game logs:
the *same card* taken at pick 3 vs pick 10 across simultaneous drafts, card fixed
effects. Holds the season/discovery state fixed; the pick is exogenous to that
draft's result. Stable at **≈ +0.13 GIH / +0.15 GNS per taken-at pick** (SOS),
robust to pod-generosity, ladder-rank, and draft-week fixed effects, and to
dropping the maindeck condition (event-level). **GNS slope is the largest of all
metrics → the tax is the surrounding deck, confirmed.** Residual confound:
drafter intent (early takes are deliberate) → treat as a near-lower-bound; the
one untested alternative is *color-lane* openness.

**Design B — weekly re-pricing panel (the misleading one).** WR ~ ALSA + card FE
+ week FE on weekly stat-table snapshots; identified by the community re-pricing
cards over a season. Reads 2–5× higher (GP +0.35/ALSA-pick SOS) and is unstable
across metric/units/subset (−0.07 to +0.35). **It is not a clean tax estimator**
(§4). Use it only to forecast what discovery does to a card's *published* numbers.

**Reconciliation:** the panel mixes a contemporaneous positive tax (price →
cheaper deck → WR) with a reverse-causal negative *lead* (hot WR → taken earlier
next week). Convert ALSA→ATA (÷κ) and subtract the archetype-week WR and the two
designs converge.

---

## 4. The confounders, in full

For each: what it is → how it bites → how we handled it → verdict.

### 4.1 Cross-card quality confounding
Good cards are picked early *and* win. So a cross-sectional regression of WR on
ALSA across cards measures the **quality gradient**, with the tax buried inside
and the wrong sign. *Handled:* never use cross-sectional WR~ALSA for the tax
(this is "M1", shown only as a trap). All designs are **within-card**.

### 4.2 Deployment selection / survivorship
A narrow card is only maindecked when the deck wants it; GIH conditions on the
maindeck. Late picks face a harsher filter, so their stats describe survivors.
*Evidence:* maindeck rate falls **−4.2pp per pick** (retail; −3.6 cube);
Fix What's Broken maindecks 44% of early copies, 9% of late, survivors +11pp.
*Handled:* report filter rates alongside; for "if-early" shrink the effect by the
*early-pick* maindeck rate; gate actionable lists on play rate ≥35% & n_gih ≥1000.
*Verdict:* real and large; the single biggest reason low-play-rate late stats
mislead.

### 4.3 Opportunity cost (THE tax itself, not a nuisance)
Cheaper late acquisition → better surrounding deck. *Lives in GNS.* The as-picked
GNS slope (+0.15/pick) is the cleanest measurement. *Verdict:* this is the effect
we want; it correctly shows up in deck quality.

### 4.4 Game-length bias (GIH and GNS, opposite directions)
GIH oversamples long games (inflates slow/blue cards ~3–5pp); GNS oversamples
short games (inflates fast/aggro context ~+0.5–1pp). *Handled:* card effect from
cost-adjusted OH+GD within-deck contrasts; length-reweight GNS strata to the
format turn distribution (Boros cube context +3.0 → +2.2pp after correction).

### 4.5 Mana-value / cost bias in OH
Mulligan-keep selection + early-game slice penalize expensive/scaling cards
monotonically in MV (+1.7pp MV0 → −2.0pp MV6+). Caught via Pyrogoyf looking
falsely terrible. *Handled:* demean OH/GD contrasts within MV bucket. *Pitfall:*
in cube the MV-0 bucket is dominated by Power → exclude Power from bucket
baselines (else Chrome Mox etc. taxed for not being Black Lotus — a retraction).

### 4.6 ALSA ≠ ATA scale
ALSA (last-seen) is compressed by passes; per-ALSA-pick numbers must be ÷1.546 to
compare with per-taken-at-pick. Nonlinear (mild early, severe late) and
rarity-dependent. *Handled:* work in ATA throughout; κ estimated with SE.

### 4.7 Archetype tide (the big one for the panel)
The panel has **week** FE but no **archetype** FE, so an archetype's own seasonal
WR arc survives. A card whose ATA drifts a little while its archetype's WR swings
a lot inherits the swing. *Decisive test:* re-net each card's weekly WR against
*its own archetype's* weekly WR → the panel slope collapses in every set
(GIH~ATA, all cards: SOS +0.03→−0.23, FIN +0.17→−0.05, TLA +0.38→−0.19; this is
the notebook's `panel_vs_archetype`). *Verdict:* the panel's
positive slope on discovered cards is mostly the archetype underneath them. This
is a *different* deck-quality effect from the opportunity cost (4.3): tide is
seasonal/within-card-across-weeks; opportunity cost is cross-sectional/within-week.
Both live in GNS; only the as-picked design isolates the tax.

### 4.8 Reverse causality / "luck-chasing"
A hot week pulls the price earlier the *next* week → negative next-week (lead)
coefficient, distinct from the contemporaneous term. Dominates the *movers*
(their WR drove their re-pricing). *Note:* this was mislabeled "luck-chasing" at
one point; it is reverse causality and bends the panel slope, it is not the tax.

### 4.9 Mean reversion in the panel
Re-pricing responds to *published* WR; transitory luck reverts. The panel cannot
separate this from a real tide; identification lives in weeks 1–2 where both are
strongest. *Handled:* flagged; dynamic spec is Nickell-biased at 8 weeks.

### 4.10 Leverage / few-card artifacts
The non-mover panel slope (+0.14) has median per-card slope −0.02 and only ~50%
positive; the top 5 cards carry the variance and dropping them → +0.06 (i.e. the
typical card is ~0; the pooled positive is a few cards). Those 5 are **discovery
co-trends** (ATA and WR falling together over the season). *This
is the answer to "why don't non-movers cancel to zero": the typical one does; the
residual is 5 leverage cards that are 4.7's archetype tide in disguise.* *Pitfall
retracted:* an earlier reading called this a "clean contemporaneous tax in
staples" — a leverage check killed it.

### 4.11 Pod generosity / open seat
A good card going late may mean the pod is weak → whole deck better. *Test:*
leave-one-out pool-acquisition index (quintiles span 8.7pp of deck WR) added to
the as-picked regression leaves the slope unchanged (+0.131→+0.131). *Verdict:*
not an open-seat artifact (whole-draft, color-agnostic index).

### 4.12 Color-lane openness (UNTESTED)
The pod index is color-agnostic; a good card arriving late also signals *its
colors* are open at your seat → genuine conditional equity, not bias. Not
separated. *Verdict:* treat the as-picked slope as an upper bound on pure
circumstance.

### 4.13 Drafter intent / self-selection
Who takes a card early differs from who wheels it. Rank FE doesn't move the slope
(+0.131→+0.135), but intent-within-rank is uncontrolled. *Verdict:* near-lower-
bound on the single-seat tax.

### 4.14 Pilot skill and deck-build fit
Both live in **GNS** (the deck's win rate reflects pilots and builds). **IIH is
immune** by construction — except the build-around card×support interaction
(4.0). So a skill/build shift cannot masquerade as "individual" for ordinary
cards. The coarse color-pair "mix" view cannot *see* skill/build shifts, but they
are not lost — they fold into the GNS deck channel.

### 4.15 Archetype definition (multicolor / Converge)
`main_colors` filtered to 2 colors drops 3–5 color decks. Arcane Omens is ~half
3+ color (blue-green ramp), so a 2-color-only archetype view sees half its games.
*Handled:* broaden archetype to `LENGTH BETWEEN 2 AND 5`. *Note:* the headline
GNS/IIH split never filtered colors, so it was always correct; only the figure
layer had the bug.

### 4.16 Build-around deckbuilding tax
A build-around (Mishra's Workshop, Tinker) forces clunky cards into the deck, so
its decks are bad *because of it* — its GP WR is correctly low while its draw-
based effect is high. The gap between GP and draw-based numbers = the tax. GP
charges it; draw-conditioned metrics forgive it. Read build-around adjusted ranks
as *conditional on building that deck*.

### 4.17 Format / structural confounders (named, mostly unhandled)
BO1 hand smoother + no sideboarding shape every number; on-play/draw and mulligan
data unused. Pick numbers pooled across packs (P1P10 ≠ P3P10) and rarities;
multi-copy retail decks booked at earliest pick. Per-card z-scores use binomial
SEs without draft-level clustering (per-card lists looser than pooled slopes).
Format heterogeneity: discovery is genuine congestion in FIN (71% of movers show
the tide signature) but shared weekly shocks in SOS/TLA. Cube: known list → no
within-session ALSA movement (panel is amplified noise); 2026-session logs don't
exist publicly (only Nov-2025), and table-movers span sessions with list churn.

---

## 5. The hypotheses we tested, and the verdicts

| hypothesis | verdict |
|---|---|
| Cross-card WR~ALSA measures the tax | **No** — measures quality, wrong sign (4.1) |
| The weekly panel measures the per-pick tax | **No** — it measures discovery; mostly archetype tide + reverse causality (3, 4.7–4.10) |
| Non-movers' price jitter cancels to zero | **Yes for the typical card**; pooled residual is 5 leverage cards (4.10) |
| The non-mover slope is archetype movement | **Yes** — archetype-netting collapses it (4.7) |
| Staples isolate a clean contemporaneous tax | **No** — leverage artifact, retracted (4.10) |
| Discovered cards' WR decline is card opportunity cost | **No, mostly archetype** — gold cards: tide dominates, within-deck lift ≈ 0 (card_vs_archetype) |
| The 10 biggest movers are individual re-evaluations | **No — 26/30 deck-driven** by ΔGNS; only 4 individual by ΔIIH (master notebook §5) |
| The ATA tax shows up in deck quality (GNS) | **Yes** — as-picked GNS slope is the largest; the project's core mechanism result |
| Aang priced like Teferi still clears Teferi | **Yes** — every adjusting estimator lands above Teferi's GIH; TLA out-of-sample confirms |
| Fixing earns a late premium like other cards | **No** — +0.05pp vs +0.71pp class test |
| Cube "fast mana / tutors overpicked" | **Partly retracted** — Power-baseline artifact; true Power is the best in cube |

---

## 6. What worked / what didn't (methods retrospective)

**Worked (keep):**
- **As-picked design** — the one estimator stable across metric, units, controls.
- **GNS as the deck-context control, IIH as the card** — `GIH = GNS + IIH` is the
  cleanest, best-sampled decomposition; immune to the per-archetype noise.
- **Archetype-netting** as a falsification tool (collapsed the panel → proved
  it's tide).
- **Leverage / jackknife** checks — overturned two of my own overclaims.
- **Cross-format replication** (SOS/FIN/TLA) — caught FIN-specific congestion.
- **κ conversion** to put ALSA and ATA on one ruler.
- **Cost-bucket demeaning with Power excluded; length-reweighted GNS** — removed
  the two biggest metric biases.

**Didn't work (avoid):**
- Cross-sectional WR~ALSA (quality, not tax).
- The weekly panel as a tax estimator (confounded; unstable).
- Controlling for %GP when estimating the boost (it's the *mediator*; flipped the
  sign — an early error).
- Per-card-per-archetype-per-fortnight "lift" (noise-inflated; gave 22/30
  individual where the robust GNS/IIH split gives 3/30).
- Endpoint (first/last fortnight) per-card deltas without significance gates —
  noisy; gate on sampling SE.
- Treating a few high-leverage cards as a mechanism ("staples", "non-movers").

**The one-line synthesis.** The ATA tax is real, small, front-loaded, and lives
in deck quality (GNS): ≈ +0.1–0.15pp GIH per taken-at pick. The log-based
as-picked design measures it cleanly; the weekly re-pricing panel does not
(it mostly measures the archetype underneath the card). The card's own in-hand
value (IIH) barely moves with pick position — which is exactly why "would this
card be as good picked early?" usually answers *yes for the card, no for the
deck around it.*

---

## 7. Data and reproduction

- **Tables:** 17Lands `card_ratings` JSON (cached in `data/raw/`), tidied into
  `data/card_tables.parquet` (SOS + cube weekly, cohorts, 31 deck-color tables),
  `data/color_tables.parquet`, `data/e2_extra_weekly.parquet` (FIN/TLA/cube
  weekly, with ATA backfilled from cache).
- **Logs:** public S3 draft+game `.csv.gz` for SOS/FIN/TLA and the Nov-2025 cube
  run, converted to `data/{tag}_{picks,games,aspicked}.parquet`.
- **Scryfall:** oracle bulk in `data/raw/` for mana value, type, color identity.
- **Formats:** sos, fin, tla, cube. Cube caveat: public logs = Nov-2025 run only.
- Everything runs offline from `data/`; only `lib17.fetch.*` hits the network
  (≥3s spacing + backoff — rate-limited once at 1.2s).
- `notebooks/00_master.ipynb` regenerates every figure inline from `lib17`; it
  does **not** depend on anything in `out/`, so `out/` can be cleared freely.
