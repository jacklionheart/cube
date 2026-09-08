#!/usr/bin/env python3
"""Build the bangers spreadsheet: one row per banger, enriched with
per-cohort win-rate detail (GIH/OH/IWD), ALSA/ATA, and Scryfall mana
value, color identity, and type.

Data from 17Lands (17lands.com) — cited per their usage guidelines.

Usage:
  python3 bangers_sheet.py SOS FIN TLA        # specific sets
  python3 bangers_sheet.py --all              # every premier-draft set
"""

import argparse
import datetime
import json

import pandas as pd

from lib17 import fetch
from lib17.bangers import bangers

# Non-set / meta formats and Alchemy rebalanced duplicates to skip in --all.
EXCLUDE = {"", "Cube", "Cube - Planar", "Cube - Powered", "Chaos", "Ravnica",
           "RAVM", "Remix - Artifacts", "CORE", "DBL"}


def all_premier_sets():
    meta = fetch.filters()
    return [
        e for e in meta["expansions"]
        if e not in EXCLUDE and not e.startswith("Y2")
        and "PremierDraft" in meta["formats_by_expansion"].get(e, [])
    ]


def scryfall_index():
    """name -> {mv, colors, type} from the cached Scryfall oracle bulk dump."""
    skip = {"art_series", "token", "double_faced_token", "emblem", "scheme", "vanguard"}
    out = {}
    for c in fetch.scryfall_oracle_cards():
        if c.get("layout") in skip or c.get("set_type") == "memorabilia":
            continue
        rec = {"mv": c.get("cmc"),
               "colors": "".join(c.get("color_identity", [])) or "C",
               "type": (c.get("type_line") or "").split(" //")[0]}
        out[c["name"]] = rec
        if "//" in c["name"]:
            out[c["name"].split(" //")[0]] = rec
    return out


def api_detail(expansion, cohort):
    raw = fetch.card_data(expansion,
                          user_group=None if cohort == "all" else cohort)
    return {r["name"]: r for r in raw}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sets", nargs="*", help="set codes, e.g. FIN TLA SOS")
    parser.add_argument("--all", action="store_true", help="every premier-draft set")
    parser.add_argument("--min-games-all", type=int, default=500)
    parser.add_argument("--min-games-top", type=int, default=100)
    parser.add_argument("-o", "--out", default="out/bangers.xlsx")
    args = parser.parse_args()

    codes = all_premier_sets() if args.all else args.sets
    if not codes:
        parser.error("give set codes or --all")

    sf = scryfall_index()
    rows, skipped = [], []
    for code in codes:
        try:
            found = bangers(code, min_games_all=args.min_games_all,
                            min_games_top=args.min_games_top)
        except Exception as e:
            skipped.append((code, str(e)))
            print(f"{code}: SKIPPED ({e})")
            continue
        d_all = api_detail(code, "all")
        d_top = api_detail(code, "top")
        print(f"{code}: {len(found)} bangers")
        for r in found:
            a = d_all[r["name"]]
            # No top cohort for this set -> leave top columns blank rather
            # than showing the API's zeroed placeholder rows.
            t = d_top[r["name"]] if r["grade_top"] is not None else {}
            card = sf.get(r["name"], {})
            rows.append({
                "Set": code,
                "Name": r["name"],
                "Rarity": r["rarity"],
                "Color": card.get("colors"),
                "Mana Value": card.get("mv"),
                "Type": card.get("type"),
                "Grade (top)": r["grade_top"],
                "Grade (all)": r["grade_all"],
                "GIH WR (top)": t.get("ever_drawn_win_rate"),
                "GIH WR (all)": a.get("ever_drawn_win_rate"),
                "OH WR (top)": t.get("opening_hand_win_rate"),
                "OH WR (all)": a.get("opening_hand_win_rate"),
                "IWD (top)": t.get("drawn_improvement_win_rate"),
                "IWD (all)": a.get("drawn_improvement_win_rate"),
                "ALSA": a.get("avg_seen"),
                "ATA": a.get("avg_pick"),
                "# GIH (all)": a.get("ever_drawn_game_count"),
                "# GIH (top)": t.get("ever_drawn_game_count"),
            })

    df = pd.DataFrame(rows)
    (fetch.ROOT / "out").mkdir(exist_ok=True)
    about = pd.DataFrame({"About": [
        "Bangers: cards overperforming for their rarity on 17Lands.",
        "Bar: common >= B, uncommon >= B+, rare >= A, mythic >= A+,",
        "required for BOTH all players and top players.",
        "Grades: 17Lands method (normal curve centered at C, 0.33 sigma per",
        "grade step, GIH WR, graded within each set+cohort population).",
        "",
        "Card win-rate data retrieved from 17Lands (https://www.17lands.com),",
        "Card Data tables, Premier Draft, all-time.",
        "Card attributes from Scryfall (https://scryfall.com).",
        f"Generated {datetime.date.today().isoformat()}.",
        f"Thresholds: >= {args.min_games_all} GIH games (all), "
        f">= {args.min_games_top} (top).",
    ] + [f"Skipped {c}: {why}" for c, why in skipped]})

    with pd.ExcelWriter(args.out, engine="openpyxl") as xl:
        df.to_excel(xl, index=False, sheet_name="Bangers")
        about.to_excel(xl, index=False, sheet_name="About")
        ws = xl.sheets["Bangers"]
        for col_cells in ws.columns:
            width = max(len(str(c.value)) for c in col_cells if c.value is not None)
            ws.column_dimensions[col_cells[0].column_letter].width = min(width + 2, 32)
        for col in ws.iter_cols(min_row=2):
            header = ws.cell(row=1, column=col[0].column).value or ""
            if "WR" in header or "IWD" in header:
                for c in col:
                    c.number_format = "0.0%"
            if header in ("ALSA", "ATA"):
                for c in col:
                    c.number_format = "0.00"
    df.to_csv(args.out.rsplit(".", 1)[0] + ".csv", index=False)
    print(f"\nwrote {len(df)} bangers across {df['Set'].nunique() if len(df) else 0} sets "
          f"to {args.out} (+ .csv); skipped {len(skipped)} sets")


if __name__ == "__main__":
    main()
