# roto

Analysis of Lords of Limited cube rotisserie drafts → one Google Sheet:
[LoL Cube Roto — Pick Summary](https://docs.google.com/spreadsheets/d/1_w-YcYynXZgzObp13fPUB1q8XNxN6IH7gFkyHgH8E8w/edit)

## Quick updates

- **New matches played** (source spreadsheets' Matches tabs changed):
  `python3 refresh.py`
- **New deck link posted** in #roto-decks: add a row to `decks.tsv`
  (`draft<TAB>player<TAB>initial|rebuild<TAB>url`), then `python3 refresh.py`.
  A `rebuild` row supersedes an `initial` for the same player.
- Add `--verify` to any run to round-trip the formula build through a temp
  Google Sheet and diff every computed cell against a values build before
  publishing. `--dry-run` builds without publishing.

## Files

- `refresh.py` — one-command pipeline: download the three source draft
  spreadsheets → fetch missing sealeddeck pools → rebuild → (verify) →
  update the Sheet in place (same URL/permissions; sheet id hardcoded here)
- `roto_summary.py` — parses the LoL roto-template exports (Draft grid,
  Cube list, Matches) and builds the workbook. Pick Summary and Win Rates
  are computed by in-cell formulas from the data tabs (Card List, Draft N,
  Records, Decks); `--values` writes precomputed values instead (used for
  verification)
- `packages.py` — package analysis library + CLI over the maindecks:
  strict signature packages, 2-of-3 edges and archetype components
  (default), per-package halos (`--loose`), mermaid graph (`--mermaid`),
  a permutation test (`--null [--iters N] [--seed S]`) that re-splits
  each player's picks into random same-size maindecks to check the
  observed package structure against chance (deckbuild stage only —
  picks stay as drafted), straddle detection (`--straddles`: decks whose 2-of-3 cores pair them with two+ decks of one other draft), and relaxed definitions (`--relax K1 K2`:
  tolerate k1 missing cards per deck / k2 missing drafts — (0,1) yields
  cross-draft deck-pair intersections, (1,0) strict cores + per-draft
  flex buckets; both also ship as sheet tabs). Importable primitives:
  `maindeck_owners`, `co_maindeck_counts`, `signature_groups`,
  `package_edges`, `components`, `halos`, `deck_sets`, `pair_packages`,
  `flex_packages`, `never_drafted`, `never_maindecked`,
  `late_first_pick`, `null_model`
- `upload_sheet.py` — xlsx → native Google Sheet via Drive API
  (`--update <fileId>` replaces content in place). OAuth: installed-app
  client from ~/Downloads (GCP project `hootro`), token cached at
  `~/.config/cube-roto/token.json`, scope `drive.file`
- `decks.tsv` — deck links per draft/player (from #roto-decks on the LoL
  Discord). `deckcache/` holds fetched sealeddeck pool JSONs, plus
  `manual-balbadorf-d3.json`, transcribed by OCR from a screenshot
  (no link was posted; kind `ocr` in the tsv)
- `sources/`, `out/` — downloaded inputs and built workbooks (gitignored)

## Gotchas

- sealeddeck card names are lowercase, accent-stripped, and use only the
  front half of split/room cards; matching handles all three
- Unlisted picks count as "not maindecked" — safe only because every deck
  is either a full 40 or lists all 45 picks (`check_deck_coverage` warns)
- Companions sit in the sideboard slot of exported pools but count as
  maindecked (zone `companion`) — only if the maindeck actually satisfies
  their deckbuilding requirement (`companion_ok`, using `scryfall.json`
  cmc/type data; e.g. Mark's D1 Lurrus deck fails MV≤2 and stays a true
  sideboard card). Yorion's 60-card check also accepts >40 listed cards in
  a pool that omits basics (some pools skip them entirely, e.g.
  ColdBrewNate's). Kaheera/Jegantha/Umori/Zirda checks are unimplemented
  and warn if ever seen in a sideboard. `scryfall.json` is keyed by cube
  card names; regenerate via Scryfall /cards/collection if the cube changes
- Draft 3 has 10 players (vs 9), so overall pick numbers aren't directly
  comparable across drafts; heat scales normalize per draft
- urllib SSL is broken on this python install; all fetching goes through
  curl (see `refresh.py:prefetch_pools`)

## Article

Prose and presentation live in [`../../blog/lol-kickoff/`](../../blog/lol-kickoff/post.md).
From the repository root, build with `python3 blog/build.py lol-kickoff`.
