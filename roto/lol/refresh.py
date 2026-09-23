"""One-command refresh of the LoL roto Google Sheet.

Downloads fresh exports of the three draft spreadsheets (match results live
in their Matches tabs), fetches any deck pools missing from deckcache/,
rebuilds the workbook, and updates the Google Sheet in place — same URL,
same sharing settings.

  new deck link posted -> add a row to decks.tsv, then: python3 refresh.py
  new matches played   -> python3 refresh.py

Flags:
  --verify   before publishing, also build a --values version, upload the
             formula build to a temporary Sheet, export Google's evaluated
             values, and diff every cell of the computed tabs
  --dry-run  build (and verify) but skip publishing
"""

import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from roto.sources import curl, prefetch_pools as _prefetch_pools

HERE = pathlib.Path(__file__).parent
SOURCES = {
    "draft1": "1i5IK8JKOeZpKZpV27YbqIFVNEkOQZq1rXRJQq-IBwCw",
    "draft2": "13ffofLIEuHaFgvHKmB308NNZWQi1YgeVFEKsTlCUc04",
    "draft3": "1AY8wUfcQLltu4D-rFOSfRfcTxuFNgL68EGY26WmaiDU",
}
TARGET_SHEET_ID = "1_w-YcYynXZgzObp13fPUB1q8XNxN6IH7gFkyHgH8E8w"
TITLE = "LoL Cube Roto — Pick Summary"
COMPUTED_TABS = ["Pick Summary", "Win Rates", "Color Analysis",
                 "Lanes (all 3 drafts)", "Teams (2 of 3)"]
FUZZY_HEADERS = ("Avg", "Win Rate", "Score")  # float columns: rounding wiggle


def download_sources(src_dir):
    src_dir.mkdir(exist_ok=True)
    for name, sid in SOURCES.items():
        curl(f"https://docs.google.com/spreadsheets/d/{sid}/export?format=xlsx",
             src_dir / f"{name}.xlsx")
        print(f"downloaded {name}")


def prefetch_pools():
    return _prefetch_pools(HERE / "decks.tsv")


def verify(formulas_path, values_path):
    from roto.sheets import verify as verify_workbooks
    return verify_workbooks(formulas_path, values_path,
                            tabs=COMPUTED_TABS, fuzzy_headers=FUZZY_HEADERS)


def main():
    do_verify = "--verify" in sys.argv
    dry_run = "--dry-run" in sys.argv

    src_dir = HERE / "sources"
    download_sources(src_dir)
    prefetch_pools()

    out_dir = HERE / "out"
    out_dir.mkdir(exist_ok=True)
    inputs = [str(src_dir / f"{n}.xlsx") for n in SOURCES]
    build_cmd = [sys.executable, str(HERE / "roto_summary.py")]

    formulas_x = out_dir / "lol-roto-summary.xlsx"
    subprocess.run(build_cmd + [str(formulas_x)] + inputs, check=True)

    if do_verify:
        values_x = out_dir / "lol-roto-summary-values.xlsx"
        subprocess.run(build_cmd + ["--values", str(values_x)] + inputs, check=True)
        sys.path.insert(0, str(HERE))
        verify(formulas_x, values_x)

    if dry_run:
        print("dry run: skipping publish")
        return
    subprocess.run(
        [sys.executable, str(HERE / "upload_sheet.py"), str(formulas_x),
         TITLE, "--update", TARGET_SHEET_ID],
        check=True,
    )


if __name__ == "__main__":
    main()
