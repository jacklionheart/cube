# cube

Cube building and MTG limited analysis.

## Layout

- `cubecobra/` — cube lists and automation for [Cube Cobra](https://cubecobra.com/user/view/jacklionheart)
  - [`gaelaria/`](https://cubecobra.com/cube/list/sealed) — main cube, sealed deck-building playground (shortId: `sealed`)
  - [`elemental/`](https://cubecobra.com/cube/list/elemental) — four-elements cube
  - [`fantasia/`](https://cubecobra.com/cube/list/fantasia) — in progress
  - `fetch.sh` — refresh `cards.csv` for each cube from Cube Cobra
  - `cc.py` — Cube Cobra client (session auth, deltas, auto-backup before every mutation)
  - `gaelaria.py` — delete stale "Clone of Gaelaria" cubes; sync [/gaea](https://cubecobra.com/cube/list/gaea) and [/tolaria](https://cubecobra.com/cube/list/tolaria) from the master's 🌳/🧙 tags. Dry-run by default; `--apply` to execute.
  - `fantasia.py` — rebuild Fantasia's maybeboard as the design pool: union of gathered picks (✨) + GUT (⚛️) + Sacred Geometry (📐) + Lords of Limited (👑), mainboard emptied. Dry-run by default.
  - `API-NOTES.md` — Cube Cobra endpoint contracts and gotchas
  - Credentials via `CUBECOBRA_USERNAME` / `CUBECOBRA_PASSWORD` env vars (or interactive prompt)
- `17lands/` — 17lands data analysis (migrated from the old `mtg_analysis` directory)
  - `lib17/` — fetch/metrics/analysis library
  - `bangers.py` — cards overperforming for their rarity (17Lands grade curve, both all + top players): `python3 bangers.py SOS`
  - `pipeline.py`, `notebooks/` — analysis entry points
  - Parquet data files are not tracked (except `data/card_tables.parquet`, an irreplaceable pre-API-gating snapshot); the rest regenerate via `lib17/fetch.py` / public S3
