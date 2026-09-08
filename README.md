# cube

Cube building and MTG limited analysis.

## Layout

- `cubecobra/` — cube lists tracked from [Cube Cobra](https://cubecobra.com/user/view/jacklionheart)
  - [`gaelaria/`](https://cubecobra.com/cube/list/sealed) — main cube, sealed deck-building playground (shortId: `sealed`)
  - [`elemental/`](https://cubecobra.com/cube/list/elemental) — four-elements cube
  - [`fantasia/`](https://cubecobra.com/cube/list/fantasia) — in progress
  - `fetch.sh` — refresh `cards.csv` for each cube from Cube Cobra
- `17lands/` — 17lands data analysis (migrated from the old `mtg_analysis` directory)
  - `lib17/` — fetch/metrics/analysis library
  - `pipeline.py`, `notebooks/` — analysis entry points
  - Parquet data files are not tracked; regenerate via `lib17/fetch.py`
