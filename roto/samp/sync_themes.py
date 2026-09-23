"""Pull hand-edited team theme labels from the sheet into team_themes.tsv.

Downloads the live Google Sheet, reads the Theme column of the Teams and
Teams (Full) tabs, and writes each team's label keyed by its card set.
Run this BEFORE any rebuild/republish so in-sheet edits survive (a
republish overwrites the whole sheet; the build re-seeds the Theme
column from team_themes.tsv).

Usage: python3 sync_themes.py            # default s4 sheet
       python3 sync_themes.py <sheetId>
"""

import io
import sys
import pathlib

import openpyxl
import upload_sheet
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

HERE = pathlib.Path(__file__).parent
DEFAULT_SHEET = "1VcZrPKd_UypiJUpbs3CJ6-ysmBhkGapnq8VJ3duJ3cc"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def col_index(ws, name):
    for c in range(1, ws.max_column + 1):
        if ws.cell(1, c).value == name:
            return c
    return None


def main():
    sheet_id = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SHEET
    drive = build("drive", "v3", credentials=upload_sheet.get_credentials())
    buf = io.BytesIO()
    dl = MediaIoBaseDownload(
        buf, drive.files().export_media(fileId=sheet_id, mimeType=XLSX))
    done = False
    while not done:
        _, done = dl.next_chunk()
    wb = openpyxl.load_workbook(io.BytesIO(buf.getvalue()), data_only=True)

    labels = {}  # card-set key -> theme (last non-empty wins)
    for tab in ("Teams",):  # the edited tab; Full holds only auto-seeds
        if tab not in wb.sheetnames:
            continue
        ws = wb[tab]
        theme_col = col_index(ws, "Theme")
        cards_col = next((c for c in range(1, ws.max_column + 1)
                          if str(ws.cell(1, c).value or "").startswith("Cards")),
                         None)
        if not theme_col or not cards_col:
            continue
        for r in range(2, ws.max_row + 1):
            cards = ws.cell(r, cards_col).value
            theme = ws.cell(r, theme_col).value
            if cards and theme and str(theme).strip():
                key = "|".join(sorted(
                    x.strip() for x in str(cards).split("\n") if x.strip()))
                labels[key] = str(theme).strip()

    out = ["cards\ttheme"] + [f"{k}\t{v}" for k, v in sorted(labels.items())]
    (HERE / "team_themes.tsv").write_text("\n".join(out) + "\n")
    print(f"team_themes.tsv: {len(labels)} hand team labels pulled")


if __name__ == "__main__":
    main()
