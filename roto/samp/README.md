# Samp roto

Analysis of the Samp Cube Roto pods → two Google Sheets, at feature
parity with the LoL roto sheet (`../lol/`):

1. **Season 4** (13 pods, summer 2026) — `refresh.py`, the original
   sheet. Never touched by anything else.
2. **All Drafts** (37 drafts, Oct 2025 – Sep 2026, seasons 1–4) —
   `refresh_all.py`, a second sheet ("Samp Cube Roto — All Drafts").
   Old-season pods are suffixed ("Tarmogoyf (s3)"); s4 pods keep their
   names. Teams support scales to ~⅓ of decked drafts (`--teams-frac`),
   and `report.scaled_lock_budgets` gives the matching ~90% locks
   budgets for report runs. Old-pod decklists come from the Archive -
   Roto Decks channels via `build_decks_all.py` → `decks_all.tsv`
   (content-matched to players since old RTB drafts only know "Seat
   N"); see `discord-scrape/notes.txt` for per-pod coverage and gaps.

## Quick updates

- **New matches played** (active pods' Matches tabs changed):
  `python3 refresh.py` — s4 sheet; `python3 refresh_all.py` — all-drafts
  sheet.
- Add `--verify` to round-trip the formula build through a temp Google
  Sheet and diff every computed cell before publishing. `--dry-run`
  builds without publishing.

## Data sources (13 pods, chronological)

- 11 pods use the LoL-template Google Sheets (ids in `refresh.py`
  SOURCES): Mockingbird, Yorion, Goose Mother, Baleful Strix, Ledger
  Shredder, Hardened Academic, Slickshot, Aven Interrupter (9 players),
  and the three active pods Skycoach Conductor, Sinkhole Surveyor,
  Eagles of the North.
- **Kishla Skimmer and Raven Eagle** ran on read-the-bones.vercel.app.
  `rtb_to_xlsx.py` synthesizes template-shaped xlsx from cached API
  payloads in `rtb/` (`/api/drafts/<slug>/live` for picks,
  `/standings` for match results, `/api/cards` for the cube list).

## Differences from the LoL pipeline

- **True pick order**: samp drafts take two consecutive rounds per
  traversal after round 25 (`DOUBLE_PICK_AFTER`); `overall_pick` and the
  Pick Summary formulas both model this, validated pick-for-pick against
  read-the-bones `pickN`.
- **Real maindecks**: `build_decks_tsv.py` maps Discord authors to
  grid players (hand aliases for by-elimination cases) and writes
  `decks.tsv`; `load_decks` then applies the LoL companion-aware
  pipeline. Coverage: 129 of 129. Five decks are hand-transcribed from
  posted images (`deckcache/manual-*.json`: Dom, aidybaby, Rob,
  Rocketman, tenderdrafter — the last found via a from:+has:image
  server search), each validated card-for-card against the player's 45
  picks; aidybaby's is his v2 list (a v3 image was posted 27 minutes
  later but never recovered). `--md-picks` remains as a fallback
  mode (drafted = maindecked). Alternate-name pools are aliased
  (DECK_CARD_ALIASES: 'the scouring stormsoul' = Sandman).
- **Packages tab** (replaces Lanes/Teams): every nonland card set
  (pairs and bigger) whose whole set sat in one maindeck in more than
  half of the drafts with known decklists. Subsets included; filter
  the Maximal column to Y for non-subsets. Host columns name the
  certifying deck per draft; W/L totals their match records.
  `lane_compare.py` remains as the definition-exploration report.
- Duplicated lands ("Hallowed Fountain 2") follow the template's suffix
  convention; `fetch_scryfall.py` strips the suffix for lookups and
  unions all 13 cube lists (556 cards; lists drift between waves).

## Files

Same layout as `../lol/` plus `rtb_to_xlsx.py`, `rtb/`,
`discord-scrape/` (deck-link scrape + `sheets.tsv` pod→sheet map +
`notes.txt` caveats). `themes.tsv` doesn't exist yet — Theme columns
are blank until someone hand-labels samp lanes.

## Article

Prose and presentation live in [`../../blog/samp-season-4/`](../../blog/samp-season-4/post.md).
From the repository root, build with `python3 blog/build.py samp-season-4`.
