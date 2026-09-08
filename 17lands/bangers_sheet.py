#!/usr/bin/env python3
"""Build the bangers spreadsheet: one row per banger, enriched with
per-cohort win-rate detail (GIH/OH/IWD), ALSA, and Scryfall mana value
and color identity.

Usage: python3 bangers_sheet.py SOS [more sets ...] -o bangers.xlsx
"""

import argparse
import time

import pandas as pd
import requests

from lib17.bangers import DATA, bangers

SCRYFALL_UA = "jacklionheart-cube-scripts/1.0 (jack@loopflow.studio)"


def scryfall_card(name):
    time.sleep(0.15)
    r = requests.get("https://api.scryfall.com/cards/named",
                     params={"exact": name},
                     headers={"User-Agent": SCRYFALL_UA}, timeout=30)
    if r.status_code != 200:
        print(f"  scryfall miss: {name} ({r.status_code})")
        return {}
    return r.json()


def cohort_detail(expansion, cohort, window="full"):
    df = pd.read_parquet(DATA / "card_tables.parquet")
    sub = df[(df.expansion == expansion) & (df.cohort == cohort) & (df.window == window)]
    return sub.set_index("name")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sets", nargs="+")
    parser.add_argument("-o", "--out", default="out/bangers.xlsx")
    args = parser.parse_args()

    rows = []
    for code in args.sets:
        found = bangers(code)
        detail = {c: cohort_detail(code, c) for c in ("all", "top")}
        print(f"{code}: {len(found)} bangers; enriching from Scryfall…")
        for r in found:
            sf = scryfall_card(r["name"])
            d_all = detail["all"].loc[r["name"]]
            d_top = detail["top"].loc[r["name"]]
            rows.append({
                "Set": code,
                "Name": r["name"],
                "Rarity": r["rarity"],
                "Color": "".join(sf.get("color_identity", [])) or "C",
                "Mana Value": sf.get("cmc"),
                "Type": (sf.get("type_line") or "").split(" —")[0],
                "Grade (top)": r["grade_top"],
                "Grade (all)": r["grade_all"],
                "GIH WR (top)": round(d_top.gih_wr, 4),
                "GIH WR (all)": round(d_all.gih_wr, 4),
                "OH WR (top)": round(d_top.oh_wr, 4),
                "OH WR (all)": round(d_all.oh_wr, 4),
                "IWD (top)": round(d_top.gih_wr - d_top.gns_wr, 4),
                "IWD (all)": round(d_all.gih_wr - d_all.gns_wr, 4),
                "ALSA": round(d_all.alsa, 2),
                "ATA": round(d_all.ata, 2),
                "# GIH (all)": int(d_all.n_gih),
                "# GIH (top)": int(d_top.n_gih),
            })

    df = pd.DataFrame(rows)
    out = args.out
    (DATA.parent / "out").mkdir(exist_ok=True)
    with pd.ExcelWriter(out, engine="openpyxl") as xl:
        df.to_excel(xl, index=False, sheet_name="Bangers")
        ws = xl.sheets["Bangers"]
        for col_cells in ws.columns:
            width = max(len(str(c.value)) for c in col_cells if c.value is not None)
            ws.column_dimensions[col_cells[0].column_letter].width = min(width + 2, 32)
        for col in ws.iter_cols(min_row=2):
            header = ws.cell(row=1, column=col[0].column).value or ""
            if "WR" in header or "IWD" in header:
                for c in col:
                    c.number_format = "0.0%"
    df.to_csv(out.rsplit(".", 1)[0] + ".csv", index=False)
    print(f"wrote {len(df)} rows to {out} (+ .csv)")


if __name__ == "__main__":
    main()
