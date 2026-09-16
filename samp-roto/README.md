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
  pipeline. Coverage: 104 of 129 decks — Sinkhole Surveyor and Eagles
  of the North are unscraped, Dom (Slickshot) is image-only
  (`discord-scrape/dom-slickshot-deck.png`, pending OCR), and
  tenderdrafter/Rocketman/Rob/aidybaby posted nothing usable. Unknown
  decks show blank MD, like LoL. `--md-picks` remains as a fallback
  mode (drafted = maindecked). Alternate-name pools are aliased
  (DECK_CARD_ALIASES: 'the scouring stormsoul' = Sandman).
- **Lanes rescaled**: one shared owner-signature across 13 pods never
  happens, so a lane is a connected component of the co-maindeck graph
  (edges: co-maindecked in >= LANE_MIN_CO=6 of the 11 decked drafts),
  with per-draft Host columns. Teams keep the LoL pair-core definition
  at MIN_PAIR_CORE=12. `lane_compare.py` renders the definition
  comparison (maximal same-deck groups at 7/6/5 support vs component
  lanes) as an essay-style report.
- Duplicated lands ("Hallowed Fountain 2") follow the template's suffix
  convention; `fetch_scryfall.py` strips the suffix for lookups and
  unions all 13 cube lists (556 cards; lists drift between waves).

## Files

Same layout as `../roto/` plus `rtb_to_xlsx.py`, `rtb/`,
`discord-scrape/` (deck-link scrape + `sheets.tsv` pod→sheet map +
`notes.txt` caveats). `themes.tsv` doesn't exist yet — Theme columns
are blank until someone hand-labels samp lanes.
