# Handoff: LoL Cube Roto Analysis (2026-09-15)

Catch-up doc for a fresh agent. Everything below lives in `roto/` unless
noted. Read `roto/README.md` first for operational detail; this doc adds
project state, decisions, and what's in flight.

## What this project is

Analysis of three rotisserie drafts of the Lords of Limited cube
(28 players total; pods: Virus Beetle = Draft 1 (9p), Sailor of Means =
Draft 2 (9p), Skittering Surveyor = Draft 3 (10p)). One deliverable is a
live Google Sheet; the other (in progress) is an article about the
cube's "packages," outlined but not yet written — the prose will be
Jack's own.

## The Google Sheet (primary deliverable, live)

https://docs.google.com/spreadsheets/d/1_w-YcYynXZgzObp13fPUB1q8XNxN6IH7gFkyHgH8E8w/edit

- **MUST always be updated in place** (`upload_sheet.py --update <id>`,
  or just `refresh.py`) — it has sharing settings; never create a new
  file for it.
- Tab order: Pick Summary, Color Analysis, Deck Shells (all 3 drafts),
  Packages (2 of 3), Card List, Draft 1–3, Records,
  Decks, Deck Links, Win Rates (raw data deliberately last).
- Pick Summary & Win Rates are computed by **in-cell formulas** from the
  data tabs; sorts are baked at build time. Pick Summary sort:
  (Drafts Taken desc, Avg Round asc, Avg Pick asc). Win Rates sort:
  Wins (Drafted) desc. All count-like columns return real 0s, not ""
  (empty-string formula results break Z→A sorts — bug class hit twice).
- Color Analysis has two native bar charts (converted from openpyxl;
  confirmed rendering).
- A "Pick Value" tab existed and was **dropped** at Jack's request
  (skeptical of WR-vs-pick-position premise). Dead builder function
  `build_pick_value` still in roto_summary.py, uncalled.

## Update flows (fast paths)

- New matches played → `python3 refresh.py`
- New deck link posted in Discord #roto-decks → add row to `decks.tsv`
  (draft⇥player⇥initial|rebuild⇥url; rebuild supersedes initial), then
  `python3 refresh.py`
- `--verify` = build values version + round-trip formula build through a
  temp Sheet, diff every computed cell (has caught real bugs; run it
  after structural changes). `--dry-run` skips publishing.
- Verification status: all green as of today (~23k cells).

## Data model & hard-won gotchas

- Sources: 3 Google Sheets (LoL roto template) → `sources/*.xlsx` via
  export URL (IDs hardcoded in refresh.py). Draft grid is snake order
  (odd rounds L→R). Draft 3 has 10 players → overall picks are NOT
  comparable across drafts raw; heat scales normalize per draft.
- Decks: sealeddeck.tech pools (`deckcache/*.json`), all 28 players
  covered. Balbadorf posted no link — his deck was OCR'd from an Arena
  screenshot (`deckcache/manual-balbadorf-d3.json`, kind `ocr`,
  verified: 29 nonbasic main + 16 side = exactly his 45 picks).
- Name matching: sealeddeck names are lowercase, accent-stripped, and
  use front halves of split/room cards; draft grids are hand-typed with
  case typos. `norm()` handles all of it; three D3 typos exist
  ("Fires of victory" etc.).
- Maindeck semantics: pool-unlisted picks = sideboard (safe: every deck
  is either full-40 or lists all 45; `check_deck_coverage` warns).
  **Companions**: sideboard companion counts as maindecked (zone
  `companion`) only if the deck passes its requirement — checked via
  `companion_ok` with `scryfall.json` (cmc/type keyed by cube names).
  Ground truth: Mark's D1 Lurrus is NOT a companion (fails MV≤2);
  imrahil327/bengolds Lurrus are; Yorion companion in all 3 (ColdBrew-
  Nate's pool omits basics — 44 listed nonbasics ⇒ 60-deck, handled);
  Dawn's Obosh genuinely sided; FOOMP's Gyruda companion.
- Match records: parsed from template Matches tabs, cross-checked
  against the template's own tallies (exact). Draft 3 round robin is
  still early; records keep accruing → refresh regularly.
- Known cosmetic warnings (ignore): two junk `hidden`-zone entries in
  Aviseras's pool.
- Python/urllib SSL is broken on this machine → ALL fetching via curl
  (refresh.py handles). OAuth for Drive: installed-app client (GCP
  project `hootro`), token cached ~/.config/cube-roto/token.json,
  drive.file scope. See memory: gdrive-upload-setup, roto-refresh-workflow.

## The article (in flight — Level 1)

- `article-outline.md` = full skeleton with per-section key metrics and
  per-reader framing. **Language must be Jack's**; my archetype labels
  are placeholders.
- Three readers: Ben/Mister Metronome (no bucket-scores, present
  choices not verdicts), Ethan/lordtupperware (steward; cut-list
  section with 4 differently-biased lists + caveats), samp/Rough Drafts
  (gift = precise reusable methods, exploration framing).
- Win-rate data informs ordering/attention only — NO records or
  percentages in the article.
- Core concept: package = maximal card set maindecked in the same deck
  in all 3 drafts (owner-signature grouping). 25 packages / 81 cards.
  Graph: edges = signatures agreeing in exactly 2/3 (documented forks);
  19 edges, 8 components (White nexus 8-pkg; UR/WU spells fork —
  Jack's favorite example: G17-UR/G13-WU split in D3; Blue tempo web;
  Boros 10-card monolith w/ no edges; 5c Fires; BG graveyard; sac/
  treasure; U oddments). Halos = per-package cards co-maindecked ≥2/3
  with every member (naive 2/3 components fuse into 274-card blob).
- Cut lists: never-drafted 24; drafted-never-maindecked 89 (44/29/16 by
  taken); taken-3×-never-played 16; never-picked-before-350 38; the 9
  late-but-maindecked counter-examples (Rise of the Varmints...) are
  the key caveat.

## Statistical machinery (Level 2, done)

- `packages.py` = importable library + CLI (default / --loose /
  --mermaid / --null [--iters N] [--seed S] / --relax K1 K2).
- Relaxed package definitions (n−k1 of the cards in one deck, in n−k2
  drafts): (0,0)=strict; (0,1)=cross-draft deck-pair intersections
  (71 maximal cores, biggest 17 — the recurring decklists themselves);
  (1,0)=strict cores + per-draft flex buckets (near-members absent from
  exactly one of the triple's decks); (1,1)=(0,1) cores + 2 free slots
  (flex is unconstrained at pair level, so only the size bound is
  meaningful). Two analyses ship in the sheet: Deck Shells (all 3 drafts) (strict >=3 cores merged with their ±1 flex: Theme/Colors/Core/Flex/All + owners + record) and Packages (2 of 3) (pair cores, min size 5 — Jack's naming: pair intersections are the package-sized units, core+flex is a deck shell; packages.py --straddles lists decks pairing with >=2 decks of the same other draft — the merge/split seams).
- "Packages ±1 Card" tab layout (iterated with Jack): P#, Colors,
  Core — in all 3 decks, Flex — in 2 of 3 (each flex line marked with
  the deck that skipped it), Combined, Core #, Flex #, Total #; sorted
  by Total #. A legal ±1 package is still core + ≤1 card per draft
  bucket; Total # is the "archetype orbit" size, not the legal max.
- Package Colors (packages.py card_colors/colors_str, data in
  scryfall.json now incl. colors/color_identity/produced_mana/oracle):
  mana-cost colors, plus for LANDS ONLY the colors they produce —
  except rainbow lands producing all five count as colorless (Edgewall
  Inn, Capital City, Spire of Industry...). Fetches (Evolving Wilds,
  Shattered Landscape) colorless; Temple Garden WG; Path to the World
  Tree G not WUBRG; produced mana on nonlands ignored (Treasure-makers
  would read 5c). Rule iterated twice with Jack — do not "improve" it
  back toward color identity.
- Null model (permutation, deckbuild stage only — picks kept, maindecks
  re-drawn as random same-size subsets of each player's pool):
  observed 25 pkgs / 81 cards / largest 10 vs null 15.7±2.6 / 40.6±6.1
  / 5.0±1.0 → p≈.002 / <.0005 / <.0005. Framing: big cores are signal;
  any individual pair could be chance (~15 packages arise randomly).
  Replicated across seeds.

## Repo state

- `roto/` is **entirely uncommitted** (git status: untracked). Jack was
  offered a commit and hasn't said yes. `sources/` and `out/` are
  gitignored build products; `deckcache/`, `scryfall.json`, `decks.tsv`
  are data worth committing.
- Files: refresh.py, roto_summary.py (workbook builder), packages.py
  (analysis lib), upload_sheet.py, decks.tsv, deckcache/, scryfall.json,
  article-outline.md, README.md.
- Session scratchpad verify script is obsolete — refresh.py --verify is
  canonical.

## Porting this analysis to samp's rotos

The pipeline assumes the LoL/Lucky Paper roto template (Draft grid with
players in row 3 / snake order, Cube tab card list in B/C/D, Matches tab
round-robin). samp's pod spreadsheets appear to use the same family of
templates — VERIFY the tab layout first (parse_draft constants at top of
roto_summary.py). Already visible in Jack's Drive: "⚡🤠 Slickshot
Show-Off Pod - Samp Cube Roto" (id 1aSjy4BenSzlMkZubCSm6Jq0fV0WjdEao2EH25VaoJbY),
"Samp Cube Roto s4 - 🤣🐦 Mockingbird Pod" (1IJ90RKGsvJsjF3C8vpwoF0u5zbQHHRa6GEnZEss5EWo),
"😡🏞️ Raging Ravine Pod - Samp Cube Roto" (1tV7db2X21V1uWwRDe_Z4aBLNMJWMbjbXKlIrE2gy_ZE).

To port, in a copy of roto/ (keep this one intact):
1. refresh.py: replace SOURCES ids; set TARGET_SHEET_ID to a NEW sheet
   (create once via upload_sheet.py without --update) — never point at
   the LoL sheet id.
2. decks.tsv: rebuild from samp's deck-links channel (Rough Drafts
   discord; Chrome extension flow worked well for scraping #roto-decks).
3. scryfall.json: regenerate for samp's cube list (it's keyed by cube
   card names — the LoL one will silently mismatch). Use the batched
   /cards/collection fetch with User-Agent header + 0.3s sleeps, front-
   half fallback for split cards; fields: cmc, type_line, colors,
   color_identity, produced_mana, oracle_text.
4. Sanity gates before trusting output: pick counts = rounds × players
   per draft; every deck 40-or-fully-listed (check_deck_coverage);
   Matches tallies match the template's own Results block; companion
   adjudication cases eyeballed.
5. Drafts count other than 3 mostly generalizes (n_d is parameterized
   in roto_summary; packages.py signature/edge logic assumes per-draft
   uniqueness of ownership, which holds for any roto).

## Likely next steps

1. Jack drafts article prose from the outline (his voice; labels his).
2. Re-run `refresh.py` + `packages.py` before publishing anything —
   D3 matches and possible new REBUILD links will shift numbers (match
   records don't change packages; new decks do).
3. Maybe: commit roto/ to git; mermaid graph rendering for the article;
   the open questions in outline §6 (seat effects, package-free cards,
   cross-community comparison with samp's pods).
