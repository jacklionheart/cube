# Rotisserie analysis

Analysis and spreadsheet tooling live here. Article prose, presentation,
and publishing live in [`../blog/`](../blog/README.md).

## Shared code

- `draft.py`: template parsing, draft/pick records, snake and double-pick ordering.
- `decks.py`: submitted pools, name normalization, companions, coverage checks.
- `colors.py`: metadata-based color and land rules; flashback is an explicit option.
- `packages.py`: owner signatures, co-occurrence, package graphs, flex/pair sets,
  Jaccard clusters, backbone depth, ensembles, and null models.
- `mining.py`: draft-supported frequent itemsets, including tolerated misses.
- `sources.py`: downloads and pool prefetching.
- `sheets.py`: Google credentials, upload/update, and formula verification.
- `xlstyle.py`: workbook palette and cell styling.

These modules take data, paths, and settings as arguments. They must not
import a cube directory or know a live Sheet ID. New reusable analysis
belongs here; do not copy it into each cube.

## Cube-specific inputs and policy

[`lol/`](lol/README.md) and [`samp/`](samp/README.md) own source registries,
local caches, deck TSVs, aliases, pick-order defaults, package thresholds,
workbook layouts, and exploration scripts. Their `packages.py` and
`roto_summary.py` retain compatible imports while delegating common work.

Run `python3 refresh.py --dry-run` **from the relevant cube directory** to
refresh and build locally. Omitting `--dry-run` updates that cube's live
Google Sheet. `samp/refresh_all.py` handles the separate all-seasons sheet.

LoL uses ordinary snake picks; Samp's default doubles picks after round 25,
with per-draft overrides for older seasons. LoL signatures require every
draft; Samp permits partial signatures. These are caller choices, not
branches on a cube name inside the shared algorithms.

## Verification

From the repository root:

```sh
python3 -m unittest discover -s roto/tests
python3 -m unittest discover -s blog/tests
python3 blog/build.py
```

Keep sources and generated workbooks in each cube's ignored `sources/` and
`out/` folders. Builds use local caches; refreshing sources is a separate step.
