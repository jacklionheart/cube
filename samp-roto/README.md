# samp-roto

Analysis of the 13 Samp Cube Roto season-4 pods (summer 2026) → one
Google Sheet, at feature parity with the LoL roto sheet (`../roto/`).

## Quick updates

- **New matches played** (active pods' Matches tabs changed):
  `python3 refresh.py`
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
  pipeline. Coverage: 105 of 129 decks — Sinkhole Surveyor and Eagles
  of the North are unscraped; Dom (Slickshot) is transcribed from his
  posted image (`deckcache/manual-dom-slickshot.json`, validated
  against his 45 picks); tenderdrafter/Rocketman/Rob/aidybaby posted
  nothing usable (Baleful trio posted images — pending capture). Unknown
  decks show blank MD, like LoL. `--md-picks` remains as a fallback
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

Same layout as `../roto/` plus `rtb_to_xlsx.py`, `rtb/`,
`discord-scrape/` (deck-link scrape + `sheets.tsv` pod→sheet map +
`notes.txt` caveats). `themes.tsv` doesn't exist yet — Theme columns
are blank until someone hand-labels samp lanes.
