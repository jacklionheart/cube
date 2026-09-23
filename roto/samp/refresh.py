"""One-command refresh of the Samp Cube Roto s4 Google Sheet.

Downloads fresh exports of the 11 sheet-based pod spreadsheets, converts
the 2 read-the-bones pods (rtb_to_xlsx.py), rebuilds the workbook, and
updates the Google Sheet in place — same URL, same sharing settings.
v1 treats every drafted card as maindecked (--md-picks); sealeddeck pools
and deck pics are a later refinement.

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
# Samp Cube Roto season 4: 13 pods in chronological order. 11 live in the
# LoL-template Google Sheets; kishla + raven-eagle ran on
# read-the-bones.vercel.app and are synthesized into the same xlsx shape
# by rtb_to_xlsx.py from cached API payloads in rtb/.
SOURCES = {
    "Mockingbird": "1IJ90RKGsvJsjF3C8vpwoF0u5zbQHHRa6GEnZEss5EWo",
    "Yorion": "1QmNInG_tr27jdePxJoIHX3YRh8O4n7q6QDGb0VtqFSQ",
    "Goose Mother": "1GvW_9aQT3EgsPBuRXBjZ2N4qaT8Q2UpAEgK7DRUXvfI",
    "Baleful Strix": "1BZc5bW2iHzl-OMeM6UrUQGQFioZfYCdRGN_frCTrlgQ",
    "Ledger Shredder": "1eHX8qG-jCvycyzkCwI1fKaQOL3wnQ2Mh_oJoROvW4lU",
    "Kishla Skimmer": "rtb:kishla-skimmer",
    "Raven Eagle": "rtb:raven-eagle",
    "Hardened Academic": "1cyQKgJBBp3HEOA1ECvd3iAZ_uGn0lpOj3N3y_0G359Y",
    "Slickshot": "1aSjy4BenSzlMkZubCSm6Jq0fV0WjdEao2EH25VaoJbY",
    "Aven Interrupter": "1VzCUYnjbE4-jP4dK0sjFoLILe46lyu7Bml9cCpyy1vk",
    "Skycoach Conductor": "12CEsijxs6i2oIfytVl25VZnF0Cvpwn7RNNZc6D7ml1k",
    "Sinkhole Surveyor": "1jm5xS8MIkx6WhBthiqBshxItFIGwM0sizx_ZuHE3ZFE",
    "Eagles of the North": "1_PMi90Uj-S3RpFeqHF_g9WmGrsIzW6cHtvY_uELydFg",
}


def slugify(name):
    return name.lower().replace(" ", "-")
# The live sheet — always update in place (same URL, same sharing):
# https://docs.google.com/spreadsheets/d/1VcZrPKd_UypiJUpbs3CJ6-ysmBhkGapnq8VJ3duJ3cc/edit
TARGET_SHEET_ID = "1VcZrPKd_UypiJUpbs3CJ6-ysmBhkGapnq8VJ3duJ3cc"
TITLE = "Samp Cube Roto s4 — Pick Summary"
COMPUTED_TABS = ["Pick Summary", "Win Rates", "Color Analysis",
                 "Teams", "Teams (Full)"]
FUZZY_HEADERS = ("Avg", "Win Rate", "Score")  # float columns: rounding wiggle


def download_sources(src_dir):
    src_dir.mkdir(exist_ok=True)
    for name, sid in SOURCES.items():
        out = src_dir / f"{slugify(name)}.xlsx"
        if sid.startswith("rtb:"):
            subprocess.run(
                [sys.executable, str(HERE / "rtb_to_xlsx.py"),
                 sid.removeprefix("rtb:"), str(out)],
                check=True)
        else:
            curl(f"https://docs.google.com/spreadsheets/d/{sid}/export?format=xlsx",
                 out)
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
    inputs = [f"{n}={src_dir / (slugify(n) + '.xlsx')}" for n in SOURCES]
    build_cmd = [sys.executable, str(HERE / "roto_summary.py")]

    formulas_x = out_dir / "samp-roto-summary.xlsx"
    subprocess.run(build_cmd + [str(formulas_x)] + inputs, check=True)

    if do_verify:
        values_x = out_dir / "samp-roto-summary-values.xlsx"
        subprocess.run(build_cmd + ["--values", str(values_x)] + inputs, check=True)
        sys.path.insert(0, str(HERE))
        verify(formulas_x, values_x)

    if dry_run:
        print("dry run: skipping publish")
        return
    if not TARGET_SHEET_ID:
        sys.exit("TARGET_SHEET_ID unset: create the sheet once with "
                 "upload_sheet.py, then paste its id into refresh.py")
    subprocess.run(
        [sys.executable, str(HERE / "upload_sheet.py"), str(formulas_x),
         TITLE, "--update", TARGET_SHEET_ID],
        check=True,
    )


if __name__ == "__main__":
    main()
