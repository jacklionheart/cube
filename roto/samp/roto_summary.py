"""Combine rotisserie draft exports into one pick-summary workbook.

Input: xlsx exports of the Lords of Limited roto template (one per draft),
each with a 'Draft' sheet (rounds x players snake grid, player names in row 3
starting at column C) and a 'Cube' sheet (card list: Card/Type/Color in B/C/D).

Output workbook sheets:
  - Card List           union of the cube lists, in cube order
  - Draft 1..N          values-only copy of each draft grid
  - Pick Summary        per card: round + overall pick in each draft, plus
                        first pick (min overall), last pick (max overall),
                        and how many drafts it was taken in

Usage: python3 roto_summary.py out.xlsx draft1.xlsx draft2.xlsx [...]
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from roto.draft import (Pick, Draft, round1, overall_pick as _overall_pick,
                        parse_draft as _parse_draft, DRAFT_SHEET, CUBE_SHEET,
                        MATCHES_SHEET, FIRST_ROUND_ROW, PLAYER_HEADER_ROW,
                        FIRST_PLAYER_COL)
from roto.decks import (BASICS, COMPANIONS, MAIN_ZONES, PERMANENT_TYPES,
                        companion_ok, norm, check_deck_coverage)
from roto.decks import load_decks as _load_decks
from roto.xlstyle import (COLOR_FILLS, HEADER_FILL, HEADER_FONT, CARD_FONT,
                          CENTER, color_fill, style_card_cell, style_header)


import openpyxl
from openpyxl.chart import BarChart, Reference, ScatterChart, Series
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

DOUBLE_PICK_AFTER = 25

def overall_pick(rnd, seat, n, dpa=DOUBLE_PICK_AFTER):
    return _overall_pick(rnd, seat, n, dpa)


def parse_draft(path, name, dpa=DOUBLE_PICK_AFTER):
    return _parse_draft(path, name, dpa)


DECK_CARD_ALIASES = {
    "the scouring stormsoul": "Sandman, Shifting Scoundrel",
    "school daze": "Outsmart the Amateur",
}


def load_decks(tsv_path, cube):
    return _load_decks(tsv_path, cube, aliases=DECK_CARD_ALIASES)


COLOR_GROUPS = ["W", "U", "B", "R", "G", "Multi", "C"]


def build_staples(wb, drafts, cube, availability, decks):
    """Staples = the Locks (nonland cards maindecked by every deck that
    could cast them, available >=5 pods, <=2 misses / <=1 on-color
    bench). Table of WR + avg round taken per card, plus three charts:
    WR by card, round-taken vs WR (scatter), avg WR by color."""
    import packages as pk
    scry = pk.load_scryfall()

    drafted, mained, rounds = {}, {}, {}
    for d in drafts:
        for c, p in d.picks.items():
            drafted[c] = drafted.get(c, 0) + 1
            rounds.setdefault(c, []).append(p.round)
            deck = decks.get((d.name, p.player))
            z = deck.get(c) if deck else None
            if z is None and c.endswith(" 2") and deck:
                z = deck.get(c[:-2].strip())
            if z in MAIN_ZONES:
                mained[c] = mained.get(c, 0) + 1

    def cols(c):
        b = c[:-2].strip() if c.endswith(" 2") else c
        return set((scry.get(b) or scry.get(c) or {}).get("colors") or [])

    deck_cols = {}
    for key, cards in decks.items():
        u = set()
        for c2, z in cards.items():
            if z in MAIN_ZONES:
                u |= cols(c2)
        deck_cols[key] = u

    locks = []
    for c, _, _ in cube:
        if pk.is_land(c, scry) or availability.get(c, 0) < 5:
            continue
        hard = soft = md = taken = 0
        for d in drafts:
            p = d.picks.get(c)
            if p is None:
                continue
            taken += 1
            deck = decks.get((d.name, p.player))
            if deck is None:
                continue
            z = deck.get(c) or (deck.get(c[:-2].strip())
                                if c.endswith(" 2") else None)
            if z in MAIN_ZONES:
                md += 1
            elif cols(c) <= deck_cols[(d.name, p.player)]:
                hard += 1
            else:
                soft += 1
        undr = availability[c] - taken
        if hard <= 1 and hard + soft + undr <= 2 and md >= 1:
            locks.append(c)

    def record(c):
        w = l = 0
        for d in drafts:
            p = d.picks.get(c)
            if p:
                dw, dl = d.records.get(p.player, (0, 0))
                w, l = w + dw, l + dl
        return w, l

    def avg_round(c):
        return round1(sum(rounds[c]) / len(rounds[c]))

    def cgroup(c):
        cc = pk.combo_color([c], scry)
        return "Multi" if len(cc) > 1 else cc

    rec = {c: record(c) for c in locks}
    locks.sort(key=lambda c: -(rec[c][0] / sum(rec[c]) if sum(rec[c]) else 0))

    ws = wb.create_sheet("Staples")
    ws.append(["Card", "Color", "Drafted", "Avg Round",
               "Wins", "Losses", "Win Rate"])
    style_header(ws)
    for c in locks:
        w, l = rec[c]
        cc = pk.combo_color([c], scry)
        wrr = w / (w + l) if w + l else None
        ws.append([c, cc, drafted[c], avg_round(c), w, l, wrr])
        r = ws.max_row
        style_card_cell(ws.cell(r, 1), "" if cc == "C" else cc)
        ws.cell(r, 4).number_format = "0.0"
        ws.cell(r, 7).number_format = "0.0%"
        for col in range(2, 8):
            ws.cell(r, col).alignment = CENTER
    ws.freeze_panes = "A2"
    ws.column_dimensions["A"].width = 30
    ws.auto_filter.ref = ws.dimensions
    last = ws.max_row

    # by-color aggregate (avg of per-card WR) for the color chart
    groups = list("WUBRG") + ["Multi", "C"]
    per = {g: [] for g in groups}
    for c in locks:
        w, l = rec[c]
        if w + l:
            per[cgroup(c)].append(w / (w + l))
    ci = 9  # side block in columns I..J
    ws.cell(1, ci, "Color").font = HEADER_FONT
    ws.cell(1, ci + 1, "Avg WR").font = HEADER_FONT
    present = [g for g in groups if per[g]]
    for i, g in enumerate(present):
        ws.cell(2 + i, ci, g)
        vc = ws.cell(2 + i, ci + 1, sum(per[g]) / len(per[g]))
        vc.number_format = "0.0%"
    color_last = 1 + len(present)

    # 1. WR by card
    c1 = BarChart()
    c1.title = "Win Rate by staple"
    c1.add_data(Reference(ws, min_col=7, min_row=1, max_row=last),
                titles_from_data=True)
    c1.set_categories(Reference(ws, min_col=1, min_row=2, max_row=last))
    c1.y_axis.numFmt = "0%"
    c1.legend = None
    c1.height, c1.width = 30, 16
    ws.add_chart(c1, "L2")

    # 2. round taken vs WR (scatter)
    sc = ScatterChart()
    sc.title = "Round taken vs win rate"
    sc.x_axis.title = "Avg round taken"
    sc.y_axis.title = "Win rate"
    sc.y_axis.numFmt = "0%"
    xref = Reference(ws, min_col=4, min_row=2, max_row=last)
    yref = Reference(ws, min_col=7, min_row=2, max_row=last)
    ser = Series(yref, xref, title="staples")
    ser.marker.symbol = "circle"
    ser.graphicalProperties.line.noFill = True
    sc.series.append(ser)
    sc.height, sc.width = 11, 16
    ws.add_chart(sc, "L64")

    # 3. avg WR by color (staples only)
    c3 = BarChart()
    c3.title = "Avg win rate by color (staples)"
    c3.add_data(Reference(ws, min_col=ci + 1, min_row=1, max_row=color_last),
                titles_from_data=True)
    c3.set_categories(Reference(ws, min_col=ci, min_row=2,
                                max_row=color_last))
    c3.y_axis.numFmt = "0%"
    c3.legend = None
    c3.height, c3.width = 9, 14
    ws.add_chart(c3, "L87")


def build_color_analysis(wb, drafts, formulas, cube=None, decks=None):
    """Per-color aggregates over the Win Rates tab, with bar charts, then
    a deck-level color-combo win-rate table + chart."""
    wr = wb["Win Rates"]
    n = wr.max_row
    # Win Rates summary columns are fixed up front: D..L
    col = {"wrd": "F", "wrm": "I", "md": "J", "grp": "L"}
    ws = wb.create_sheet("Color Analysis")
    ws.append(["Color", "Cards Drafted", "Cards Maindecked",
               "Avg Win Rate (Drafted)", "Avg Win Rate (Maindeck)"])
    style_header(ws)
    rng = {k: f"'Win Rates'!${v}$2:${v}${n}" for k, v in col.items()}
    for i, g in enumerate(COLOR_GROUPS):
        r = i + 2
        if formulas:
            ws.append([
                g,
                f"=COUNTIF({rng['grp']},$A{r})",
                f'=COUNTIFS({rng["grp"]},$A{r},{rng["md"]},">0")',
                f'=IFERROR(AVERAGEIFS({rng["wrd"]},{rng["grp"]},$A{r}),"")',
                f'=IFERROR(AVERAGEIFS({rng["wrm"]},{rng["grp"]},$A{r}),"")',
            ])
        else:
            drafted = md = 0
            wrd, wrm = [], []
            for row in wr.iter_rows(min_row=2, values_only=True):
                if row[11] != g:  # Color Group (L)
                    continue
                drafted += 1
                if row[9] > 0:  # Maindecked (J)
                    md += 1
                if isinstance(row[5], (int, float)):  # WR Drafted (F)
                    wrd.append(row[5])
                if isinstance(row[8], (int, float)):  # WR Maindeck (I)
                    wrm.append(row[8])
            ws.append([g, drafted, md,
                       sum(wrd) / len(wrd) if wrd else None,
                       sum(wrm) / len(wrm) if wrm else None])
        fill = color_fill(g if g != "Multi" else "WU")
        if fill:
            ws.cell(r, 1).fill = fill
        ws.cell(r, 1).font = CARD_FONT
        ws.cell(r, 4).number_format = "0.0%"
        ws.cell(r, 5).number_format = "0.0%"
        for c in range(1, 6):
            ws.cell(r, c).alignment = CENTER
    for letter, w in zip("ABCDE", (10, 13, 17, 20, 21)):
        ws.column_dimensions[letter].width = w

    last = 1 + len(COLOR_GROUPS)
    chart = BarChart()
    chart.title = "Avg Win Rate by Color"
    chart.add_data(
        Reference(ws, min_col=4, max_col=5, min_row=1, max_row=last),
        titles_from_data=True,
    )
    chart.set_categories(Reference(ws, min_col=1, min_row=2, max_row=last))
    chart.y_axis.numFmt = "0%"
    chart.height, chart.width = 9, 14
    ws.add_chart(chart, "A11")

    chart = BarChart()
    chart.title = "Cards Maindecked by Color"
    chart.add_data(
        Reference(ws, min_col=3, max_col=3, min_row=1, max_row=last),
        titles_from_data=True,
    )
    chart.set_categories(Reference(ws, min_col=1, min_row=2, max_row=last))
    chart.height, chart.width = 9, 14
    ws.add_chart(chart, "H11")

    if cube is None or decks is None:
        return
    # -- deck-level color-combo win rates (hybrid-aware) --------------
    import packages as pk
    scry = pk.load_scryfall()
    name2k = {d.name: k for k, d in enumerate(drafts)}
    combo = {}  # combo -> [wins, losses, decks]
    for (dname, player), zones in decks.items():
        md = [c for c, z in zones.items()
              if z in MAIN_ZONES and not pk.is_land(c, scry)]
        if not md:
            continue
        cc = pk.combo_color(md, scry)
        k = name2k.get(dname)
        w, l = drafts[k].records.get(player, (0, 0)) if k is not None else (0, 0)
        e = combo.setdefault(cc, [0, 0, 0])
        e[0] += w
        e[1] += l
        e[2] += 1
    rows = sorted(((cc, d, w, l, w / (w + l) if w + l else None)
                   for cc, (w, l, d) in combo.items()),
                  key=lambda r: -(r[4] if r[4] is not None else -1))
    top = 30  # header row for the combo block
    ws.cell(top, 1, "Color Combo").font = HEADER_FONT
    for cix, name in enumerate(["Color Combo", "Decks", "Wins", "Losses",
                                "Win Rate"]):
        c = ws.cell(top, cix + 1, name)
        c.font = HEADER_FONT
        c.fill = HEADER_FILL
        c.alignment = CENTER
    for i, (cc, d, w, l, cwr) in enumerate(rows):
        r = top + 1 + i
        ws.append([]) if False else None
        ws.cell(r, 1, cc)
        ws.cell(r, 2, d)
        ws.cell(r, 3, w)
        ws.cell(r, 4, l)
        wc = ws.cell(r, 5, cwr)
        wc.number_format = "0.0%"
        fill = color_fill(cc if cc in COLOR_FILLS or len(cc) == 1 else "WU")
        if fill:
            ws.cell(r, 1).fill = fill
        for cix in range(1, 6):
            ws.cell(r, cix).alignment = CENTER
    combo_last = top + len(rows)
    cchart = BarChart()
    cchart.title = "Win Rate by Color Combo (decks)"
    cchart.add_data(Reference(ws, min_col=5, min_row=top, max_row=combo_last),
                    titles_from_data=True)
    cchart.set_categories(Reference(ws, min_col=1, min_row=top + 1,
                                    max_row=combo_last))
    cchart.y_axis.numFmt = "0%"
    cchart.legend = None
    cchart.height, cchart.width = 12, 20
    ws.add_chart(cchart, "H30")


def build_pick_value(wb, drafts, cube, decks, formulas):
    """Maindeck wins relative to draft position, as wins over expectation.
    Exp Win Rate is a linear fit (SLOPE/INTERCEPT) of maindeck win rate vs
    average pick across all cards with a maindeck record; Exp Wins = the
    drafters' total games x that rate; Value = MD Wins - Exp Wins. Late
    picks that won beat low expectations; early picks that missed the
    maindeck or lost fall short of high ones; early picks that won still
    score positive."""
    stats = {}
    for card, ctype, color in cube:
        picked = [(d, d.picks[card]) for d in drafts if card in d.picks]
        if not picked:
            continue
        w = l = md = games = 0
        for d, p in picked:
            dw, dl = d.records.get(p.player, (0, 0))
            games += dw + dl
            deck = decks.get((d.name, p.player))
            if deck and deck.get(card) in MAIN_ZONES:
                md += 1
                w, l = w + dw, l + dl
        stats[card] = {
            "type": ctype, "color": color,
            "avg_pick": round(sum(p.overall for _, p in picked) / len(picked), 1),
            "md": md, "w": w, "l": l,
            "wr": w / (w + l) if w + l else None,
            "games": games,
        }
    # least-squares fit of maindeck WR on avg pick (same math as SLOPE/INTERCEPT)
    pairs = [(s["avg_pick"], s["wr"]) for s in stats.values() if s["wr"] is not None]
    mx = sum(x for x, _ in pairs) / len(pairs)
    my = sum(y for _, y in pairs) / len(pairs)
    slope = (sum((x - mx) * (y - my) for x, y in pairs)
             / sum((x - mx) ** 2 for x, _ in pairs))
    intercept = my - slope * mx
    for s in stats.values():
        s["exp_wr"] = intercept + slope * s["avg_pick"]
        s["exp_wins"] = s["games"] * s["exp_wr"]
        s["value"] = s["w"] - s["exp_wins"]

    n_d = len(drafts)
    avg_pick_col = 2 * n_d + 6  # in Pick Summary
    wrbase = 4 + 4 * n_d  # in Win Rates
    wr_end = get_column_letter(wrbase + 8)
    ps_end = get_column_letter(2 * n_d + 9)

    ws = wb.create_sheet("Pick Value")
    header = ["Card", "Type", "Color", "Avg Pick", "Maindecked", "MD Wins",
              "MD Losses", "MD Win Rate", "Drafter Games", "Exp Win Rate",
              "Exp Wins", "Value (MD Wins − Exp)"]
    ws.append(header)
    last = 1 + len(stats)
    fit_y, fit_x = f"$H$2:$H${last}", f"$D$2:$D${last}"
    for card in sorted(stats, key=lambda c: (-stats[c]["value"], c)):
        r = ws.max_row + 1
        s = stats[card]
        if formulas:
            wrv = f"=VLOOKUP($A{r},'Win Rates'!$A:${wr_end},{{}},FALSE)"
            row = [
                card,
                f"=VLOOKUP($A{r},'Card List'!$A:$D,2,FALSE)",
                f"=VLOOKUP($A{r},'Card List'!$A:$D,3,FALSE)",
                f"=VLOOKUP($A{r},'Pick Summary'!$A:${ps_end},{avg_pick_col},FALSE)",
                wrv.format(wrbase + 6),
                wrv.format(wrbase + 3),
                wrv.format(wrbase + 4),
                wrv.format(wrbase + 5),
                (f"=VLOOKUP($A{r},'Win Rates'!$A:${wr_end},{wrbase},FALSE)"
                 f"+VLOOKUP($A{r},'Win Rates'!$A:${wr_end},{wrbase + 1},FALSE)"),
                f"=INTERCEPT({fit_y},{fit_x})+SLOPE({fit_y},{fit_x})*$D{r}",
                f"=$I{r}*$J{r}",
                f"=$F{r}-$K{r}",
            ]
        else:
            row = [card, s["type"], s["color"], s["avg_pick"], s["md"],
                   s["w"], s["l"], s["wr"], s["games"], s["exp_wr"],
                   s["exp_wins"], s["value"]]
        ws.append(row)
        style_card_cell(ws.cell(r, 1), s["color"])
        for c in range(3, len(header) + 1):
            ws.cell(r, c).alignment = CENTER
        ws.cell(r, 8).number_format = "0.0%"
        ws.cell(r, 10).number_format = "0.0%"
        ws.cell(r, 11).number_format = "0.0"
        ws.cell(r, 12).number_format = "0.0"

    style_header(ws)
    ws.freeze_panes = "B2"
    ws.column_dimensions["A"].width = 32
    ws.column_dimensions["B"].width = 32
    ws.auto_filter.ref = ws.dimensions
    ws.conditional_formatting.add(
        f"L2:L{ws.max_row}",
        ColorScaleRule(
            start_type="min", start_color="E67C73",
            mid_type="num", mid_value=0, mid_color="FFD666",
            end_type="max", end_color="57BB8A",
        ),
    )
    ws.conditional_formatting.add(
        f"H2:H{ws.max_row}",
        ColorScaleRule(
            start_type="num", start_value=0, start_color="E67C73",
            mid_type="num", mid_value=0.5, mid_color="FFD666",
            end_type="num", end_value=1, end_color="57BB8A",
        ),
    )


TEAMS_MIN_SUP = 6  # explicit support bar for the Teams tabs (None = >50%)


def team_key(cards):
    """Stable identity for a team across rebuilds: its sorted card set."""
    return "|".join(sorted(cards))


def load_team_themes():
    """card-set key -> hand theme label, from team_themes.tsv (synced
    from the sheet's editable Theme column by sync_themes.py)."""
    path = pathlib.Path(__file__).parent / "team_themes.tsv"
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text().splitlines()[1:]:
        if "\t" in line:
            key, theme = line.split("\t", 1)
            if theme.strip():
                out[key] = theme.strip()
    return out


def build_packages(wb, drafts, cube, decks, teams_frac=None):
    """Teams: every nonland card set (pairs and bigger) whose WHOLE set
    sat in one maindeck in more than half of the drafts with known
    decklists. The Teams tab shows only maximal (non-subset) sets — the
    default view; Teams (Full) keeps every qualifying subset with a
    Maximal flag for filtering. Hosts are the certifying decks (unique
    per draft: roto ownership); W/L totals the host decks' match
    records. Computed here, not by sheet formulas."""
    import packages as pk

    scry = pk.load_scryfall()
    from auto_tags import seed_theme
    hand_team = load_team_themes()

    def auto_team_theme(S):
        cnt = {}
        for c in S:
            t = seed_theme(c, scry)
            if t:
                cnt[t] = cnt.get(t, 0) + 1
        return ", ".join(sorted(t for t, n in cnt.items() if n >= 2))

    def team_theme(S):
        # a hand label (synced from the sheet, keyed by the card set)
        # overrides the auto seed
        return hand_team.get(team_key(S)) or auto_team_theme(S)

    owners = pk.nonland_owners(pk.maindeck_owners(drafts, cube, decks), scry)
    card_decks = {}
    for card, sig in owners.items():
        for k, p in enumerate(sig):
            if p:
                card_decks.setdefault(card, set()).add((k, p))
    n_known = len({k for ds in card_decks.values() for k, _ in ds})
    # the "often" bar (~>=1/3 of drafts); set to None for the majority
    # bar (n_known // 2 + 1). teams_frac (e.g. 0.33) overrides both,
    # scaling with the number of decked drafts.
    if teams_frac is not None:
        min_sup = max(2, round(n_known * teams_frac))
    else:
        min_sup = TEAMS_MIN_SUP or n_known // 2 + 1

    def support(ds):
        return len({k for k, _ in ds})

    cards_f = sorted(c for c, ds in card_decks.items()
                     if support(ds) >= min_sup)
    idx = {c: i for i, c in enumerate(cards_f)}
    frequent = {}

    def dfs(stack, ds):
        for c in cards_f:
            if idx[c] <= idx[stack[-1]]:
                continue
            nds = ds & card_decks[c]
            if support(nds) >= min_sup:
                frequent[tuple(stack + [c])] = nds
                dfs(stack + [c], nds)

    for c in cards_f:
        dfs([c], card_decks[c])

    def is_maximal(S, ds):
        ss = set(S)
        return not any(support(ds & card_decks[c]) >= min_sup
                       for c in cards_f if c not in ss)

    groups = sorted(frequent.items(),
                    key=lambda kv: (-len(kv[0]), -support(kv[1]), kv[0]))

    def write_tab(title, rows, with_flag):
        ws = wb.create_sheet(title)
        header = ["#"] + (["Maximal"] if with_flag else []) + [
            "Size", "Colors", "Theme",
            f"Drafts (of {n_known} with decks)",
            f"Cards — whole set in one maindeck in ≥{min_sup} drafts"]
        header += [f"{d.name} Host" for d in drafts]
        header += ["Wins", "Losses", "Win Rate"]
        ws.append(header)
        style_header(ws)
        cards_col = 7 if with_flag else 6
        for i, (S, ds, maximal) in enumerate(rows):
            by_draft = dict(sorted(ds))  # k -> player (unique per draft)
            hosts = [by_draft.get(k, "") for k in range(len(drafts))]
            w = l = 0
            for k, p in sorted(by_draft.items()):
                dw, dl = drafts[k].records.get(p, (0, 0))
                w, l = w + dw, l + dl
            wr = w / (w + l) if w + l else None
            row = [i + 1] + (["Y" if maximal else ""] if with_flag else [])
            row += [len(S), pk.combo_color(S, scry), team_theme(S),
                    support(ds), "\n".join(sorted(S)), *hosts, w, l, wr]
            ws.append(row)
            r = ws.max_row
            ws.cell(r, cards_col).alignment = Alignment(wrap_text=True)
            for c in (*range(1, cards_col), *range(cards_col + 1, len(header) + 1)):
                ws.cell(r, c).alignment = CENTER
            ws.cell(r, len(header)).number_format = "0.0%"
        ws.freeze_panes = "A2"
        ws.column_dimensions[get_column_letter(cards_col)].width = 40
        ws.column_dimensions[get_column_letter(cards_col - 2)].width = 18
        for i in range(len(drafts)):
            ws.column_dimensions[get_column_letter(cards_col + 1 + i)].width = 14
        ws.auto_filter.ref = ws.dimensions
        wr_col = get_column_letter(len(header))
        if ws.max_row >= 2:
            ws.conditional_formatting.add(
                f"{wr_col}2:{wr_col}{ws.max_row}",
                ColorScaleRule(
                    start_type="num", start_value=0, start_color="E67C73",
                    mid_type="num", mid_value=0.5, mid_color="FFD666",
                    end_type="num", end_value=1, end_color="57BB8A",
                ),
            )

    flagged = [(S, ds, is_maximal(S, ds)) for S, ds in groups]
    # Teams = the maximal (non-subset) sets only; Teams (Full) keeps every
    # qualifying subset with the Maximal flag for filtering
    write_tab("Teams", [g for g in flagged if g[2]], with_flag=False)
    write_tab("Teams (Full)", flagged, with_flag=True)



def build_archetypes(wb, drafts, cube, decks):
    """Data-driven archetype tab. Clusters emerge from strict support-6
    maximal teams (whole set maindecked together in >=6 of 13 drafts),
    cross-size single-linkage merged (two teams fuse when one sits within
    one card of the other) -> Sacrifice (B/BR) and Discard (R/WR). Each
    cluster is a card table: strict-backbone depth (deepest all-together
    itemset in the cluster that contains the card -> separates core from
    riders), deck-level inclusion rate, and conditional win rate. A deck is
    tagged with a cluster when it maindecks >= min(4, |cluster|-1) of its
    cards; the WR/inclusion pool over those decks. Static values (not in
    COMPUTED_TABS), so it is identical in the formula and values builds."""
    import packages as pk
    from mining import Dataset

    scry = pk.load_scryfall()
    owners = pk.nonland_owners(pk.maindeck_owners(drafts, cube, decks), scry)
    deck_sets = {}
    for c, sig in owners.items():
        for k, p in enumerate(sig):
            if p:
                deck_sets.setdefault((k, p), set()).add(c)
    if not deck_sets:
        return
    rec = {kp: drafts[kp[0]].records.get(kp[1], (0, 0)) for kp in deck_sets}
    md = {c: sum(p is not None for p in sig) for c, sig in owners.items()}

    ds = Dataset.from_owners(owners)
    G = [frozenset(S) for S, _ in
         ds.mine(min_support=6, min_size=4, miss=0, maximal=True, workers=1)]
    parent = {s: s for s in G}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(len(G)):
        for j in range(i + 1, len(G)):
            if len(G[i] & G[j]) >= min(len(G[i]), len(G[j])) - 1:
                parent[find(G[i])] = find(G[j])
    clusters = {}
    for s in G:
        clusters.setdefault(find(s), set()).update(s)
    unions = list(clusters.values())

    def pick(seeds):  # the emergent cluster containing these seed cards
        for u in unions:
            if all(any(s in c for c in u) for s in seeds):
                return set(u)
        return set()

    named = [
        ("Sacrifice", pick(["Yawgmoth", "Mayhem Devil",
                            "Priest of Forgotten Gods"])),
        ("Discard", pick(["Cool but Rude", "Faithless Looting", "Inti"])),
    ]

    from roto.packages import backbone_depth

    def tot(decklist):
        w = l = 0
        for kp in decklist:
            a, b = rec[kp]
            w, l = w + a, l + b
        return w, l

    ws = wb.create_sheet("Archetypes")
    row = 1
    for name, pool in named:
        if not pool:
            continue
        pool = set(pool)
        T = min(4, len(pool) - 1)
        tagged = [kp for kp, cs in deck_sets.items() if len(cs & pool) >= T]
        depth = backbone_depth(owners, pool, min_support=6)
        w, l = tot(tagged)
        wr = w / (w + l) if w + l else None
        head = ws.cell(row, 1, name)
        head.font = Font(bold=True, size=13)
        sub = ws.cell(row, 2,
                      f"{pk.combo_color(pool, scry)}  ·  {len(pool)} cards  ·  "
                      f"{len(tagged)} decks tagged (≥{T} of {len(pool)})  ·  "
                      f"{w}–{l}" + (f"  ·  {wr:.1%}" if wr is not None else ""))
        sub.font = Font(italic=True)
        row += 1
        headers = ["Card", "Backbone Depth", "Maindecked (of 13)",
                   "Inclusion in tagged decks", "Wins", "Losses", "Win Rate"]
        for ci, h in enumerate(headers, 1):
            c = ws.cell(row, ci, h)
            c.font = HEADER_FONT
            c.fill = HEADER_FILL
            c.alignment = Alignment(horizontal="center", wrap_text=True)
        header_row = row
        row += 1
        first_data = row
        ranked = sorted(pool, key=lambda c: (
            -depth[c], -sum(1 for kp in tagged if c in deck_sets[kp])))
        for c in ranked:
            withc = [kp for kp in tagged if c in deck_sets[kp]]
            ww, ll = tot(withc)
            incl = len(withc) / len(tagged) if tagged else 0
            cwr = ww / (ww + ll) if ww + ll else None
            cc = ws.cell(row, 1, c)
            cc.font = CARD_FONT
            fill = color_fill(pk.combo_color([c], scry))
            if fill:
                cc.fill = fill
            ws.cell(row, 2, depth[c])
            ws.cell(row, 3, md.get(c, 0))
            ws.cell(row, 4, incl).number_format = "0%"
            ws.cell(row, 5, ww)
            ws.cell(row, 6, ll)
            ws.cell(row, 7, cwr).number_format = "0.0%"
            for ci in range(2, 8):
                ws.cell(row, ci).alignment = CENTER
            row += 1
        last_data = row - 1
        chart = BarChart()
        chart.type = "bar"
        chart.title = f"{name}: inclusion rate (given deck is {name})"
        chart.add_data(Reference(ws, min_col=4, min_row=header_row,
                                 max_row=last_data), titles_from_data=True)
        chart.set_categories(Reference(ws, min_col=1, min_row=first_data,
                                       max_row=last_data))
        chart.x_axis.numFmt = "0%"
        chart.legend = None
        chart.height = 1.0 + 0.32 * len(ranked)
        chart.width = 14
        ws.add_chart(chart, f"I{header_row}")
        row += 2
    ws.column_dimensions["A"].width = 26
    for col in "BCDEFG":
        ws.column_dimensions[col].width = 15
    ws.freeze_panes = "A1"




def build_workbook(drafts, cube, availability, formulas=True, decks=None,
                   links=None, teams_frac=None):
    """drafts: list of Draft; cube: list of (card, type, color) in cube order;
    availability: card -> number of drafts whose cube list contains it.
    With formulas=True the Pick Summary is computed by in-cell formulas from
    the Draft/Card List sheets; formulas=False writes precomputed values."""
    wb = openpyxl.Workbook()
    card_color = {card: color for card, _, color in cube}

    ws = wb.active
    ws.title = "Card List"
    ws.append(["Card", "Type", "Color", "Drafts Available"])
    for card, ctype, color in cube:
        ws.append([card, ctype, color, availability.get(card, 0)])
        style_card_cell(ws.cell(ws.max_row, 1), color)
        ws.cell(ws.max_row, 3).alignment = CENTER
        ws.cell(ws.max_row, 4).alignment = CENTER
    style_header(ws)
    ws.freeze_panes = "A2"
    ws.column_dimensions["A"].width = 32
    ws.column_dimensions["B"].width = 32

    canonical = {c.casefold(): c for c in card_color}
    for d in drafts:
        ws = wb.create_sheet(d.name)
        ws.append(["Round"] + d.players)
        for i, cards in enumerate(d.rounds):
            ws.append([i + 1] + cards)
            ws.cell(ws.max_row, 1).alignment = CENTER
            for j, card in enumerate(cards):
                if card:
                    name = canonical.get(card.casefold(), card)
                    style_card_cell(ws.cell(ws.max_row, j + 2), card_color.get(name))
        style_header(ws)
        ws.freeze_panes = "B2"
        for i in range(len(d.players)):
            ws.column_dimensions[get_column_letter(i + 2)].width = 26

    ws = wb.create_sheet("Pick Summary")
    header = ["Card", "Type", "Color"]
    for d in drafts:
        header += [f"{d.name} Round", f"{d.name} Pick", f"{d.name} MD"]
    header += ["First Pick", "Last Pick", "Avg Pick", "Avg Round",
               "Drafts Taken", "Maindecked", "Drafts Available"]
    ws.append(header)
    n_d = len(drafts)
    wr_end = get_column_letter(12 + 4 * n_d)  # Win Rates last column
    wr_md_col = lambda i: 16 + 4 * i  # per-draft MD column in Win Rates
    wr_mdcount_col = 10  # Maindecked column in Win Rates

    def sort_key(entry):
        card, _, _ = entry
        picks = [d.picks[card] for d in drafts if card in d.picks]
        avg_round = sum(p.round for p in picks) / len(picks) if picks else 10**6
        avg_pick = sum(p.overall for p in picks) / len(picks) if picks else 10**6
        return (-len(picks), avg_round, avg_pick, card)

    def value_row(card, ctype, color):
        row = [card, ctype, color]
        overalls, rounds, mds = [], [], []
        for d in drafts:
            p = d.picks.get(card)
            md = None
            if p:
                deck = (decks or {}).get((d.name, p.player))
                if deck is not None:
                    md = "Y" if deck.get(card) in MAIN_ZONES else "N"
            row += [p.round, p.overall, md] if p else [None, None, None]
            if p:
                overalls.append(p.overall)
                rounds.append(p.round)
                mds.append(md)
        return row + [
            min(overalls) if overalls else None,
            max(overalls) if overalls else None,
            round1(sum(overalls) / len(overalls)) if overalls else None,
            round1(sum(rounds) / len(rounds)) if rounds else None,
            len(overalls),
            sum(m == "Y" for m in mds),
            availability.get(card, 0),
        ]

    def formula_row(card, r):
        lookup = f"=VLOOKUP($A{r},'Card List'!$A:$D,{{}},FALSE)"
        row = [card, lookup.format(2), lookup.format(3)]
        for i, d in enumerate(drafts):
            n = len(d.players)
            last = 1 + len(d.rounds)
            rng = f"'{d.name}'!$B$2:${get_column_letter(1 + n)}${last}"
            rcol = f"'{d.name}'!$A$2:$A${last}"
            rc = f"{get_column_letter(4 + 3 * i)}{r}"
            seat = f"(SUMPRODUCT(({rng}=$A{r})*COLUMN({rng}))-1)"
            row.append(
                f'=IF(SUMPRODUCT(--({rng}=$A{r}))=0,"",'
                f"SUMPRODUCT(({rng}=$A{r})*{rcol}))"
            )
            # true overall pick: plain snake through the draft's dpa, then
            # two consecutive rounds per traversal (see overall_pick)
            dp = d.dpa
            plain = f"({rc}-1)*{n}+IF(ISODD({rc}),{seat},{n}+1-{seat})"
            if dp is None:
                row.append(f'=IF({rc}="","",{plain})')
            else:
                k = f"INT(({rc}-{dp + 1})/2)"
                # pair k is left-to-right when its parity matches dpa's
                lr = (f"ISODD({k})" if dp % 2 == 1 else f"ISEVEN({k})")
                row.append(
                    f'=IF({rc}="","",IF({rc}<={dp},{plain},'
                    f"{dp * n}+{k}*{2 * n}"
                    f"+2*IF({lr},{seat}-1,{n}-{seat})"
                    f"+1+MOD({rc}-{dp + 1},2)))"
                )
            row.append(
                f"=IFERROR(VLOOKUP($A{r},'Win Rates'!$A:${wr_end},"
                f'{wr_md_col(i)},FALSE),"")'
            )
        picks = ",".join(f"${get_column_letter(5 + 3 * i)}{r}" for i in range(len(drafts)))
        rnds = ",".join(f"${get_column_letter(4 + 3 * i)}{r}" for i in range(len(drafts)))
        return row + [
            f'=IF(COUNT({picks})=0,"",MIN({picks}))',
            f'=IF(COUNT({picks})=0,"",MAX({picks}))',
            f'=IF(COUNT({picks})=0,"",ROUND(AVERAGE({picks}),1))',
            f'=IF(COUNT({rnds})=0,"",ROUND(AVERAGE({rnds}),1))',
            f"=COUNT({picks})",
            f"=IFERROR(VLOOKUP($A{r},'Win Rates'!$A:${wr_end},"
            f"{wr_mdcount_col},FALSE),0)",
            lookup.format(4),
        ]

    for card, ctype, color in sorted(cube, key=sort_key):
        if formulas:
            ws.append(formula_row(card, ws.max_row + 1))
        else:
            ws.append(value_row(card, ctype, color))
        style_card_cell(ws.cell(ws.max_row, 1), color)
        for c in range(3, len(header) + 1):
            ws.cell(ws.max_row, c).alignment = CENTER

    style_header(ws)
    ws.freeze_panes = "B2"
    ws.column_dimensions["A"].width = 32
    ws.column_dimensions["B"].width = 32
    for c in range(4, len(header) + 1):
        ws.column_dimensions[get_column_letter(c)].width = 10
    ws.auto_filter.ref = ws.dimensions

    # green (early) -> red (late) heat scale, normalized per column so the
    # same color means the same relative draft depth: rounds scale to that
    # draft's round count, picks to that draft's total picks
    def heat(col, vmax):
        letter = get_column_letter(col)
        ws.conditional_formatting.add(
            f"{letter}2:{letter}{ws.max_row}",
            ColorScaleRule(
                start_type="num", start_value=1, start_color="57BB8A",
                mid_type="num", mid_value=(1 + vmax) / 2, mid_color="FFD666",
                end_type="num", end_value=vmax, end_color="E67C73",
            ),
        )

    max_rounds = max(len(d.rounds) for d in drafts)
    max_picks = max(len(d.rounds) * len(d.players) for d in drafts)
    for i, d in enumerate(drafts):
        heat(4 + 3 * i, len(d.rounds))
        heat(5 + 3 * i, len(d.rounds) * len(d.players))
    base = 4 + 3 * len(drafts)
    heat(base, max_picks)      # First Pick
    heat(base + 1, max_picks)  # Last Pick
    heat(base + 2, max_picks)  # Avg Pick
    heat(base + 3, max_rounds) # Avg Round

    build_win_rates(wb, drafts, cube, formulas, decks or {})
    build_color_analysis(wb, drafts, formulas, cube, decks or {})
    build_staples(wb, drafts, cube, availability, decks or {})
    build_packages(wb, drafts, cube, decks or {}, teams_frac=teams_frac)
    build_archetypes(wb, drafts, cube, decks or {})

    ws = wb.create_sheet("Deck Links")
    ws.append(["Draft", "Player", "Kind", "URL", "Used"])
    style_header(ws)
    for draft, player, kind, url, used in links or []:
        ws.append([draft, player, kind, url, used])
        ws.cell(ws.max_row, 4).hyperlink = url
        ws.cell(ws.max_row, 5).alignment = CENTER
    ws.freeze_panes = "A2"
    for col, w in zip("ABCDE", (10, 18, 10, 36, 6)):
        ws.column_dimensions[col].width = w

    order = ["Pick Summary", "Color Analysis", "Archetypes",
             "Teams", "Teams (Full)", "Staples", "Card List"]
    order += [d.name for d in drafts]
    order += ["Records", "Decks", "Deck Links", "Win Rates"]
    wb._sheets = [wb[name] for name in order]
    wb.active = 0
    return wb


def build_win_rates(wb, drafts, cube, formulas, decks):
    """Match records per player (Records data tab), submitted decklists
    (Decks data tab), and per-card W/L/win rate + maindeck status attributed
    via who drafted the card (Win Rates tab)."""
    ws = wb.create_sheet("Decks")
    ws.append(["Draft", "Player", "Card", "Zone"])
    style_header(ws)
    for (draft, player), cards in sorted(decks.items()):
        for card, zone in sorted(cards.items()):
            ws.append([draft, player, card, zone])
    ws.freeze_panes = "A2"
    for col, w in zip("ABCD", (10, 18, 32, 8)):
        ws.column_dimensions[col].width = w
    ws = wb.create_sheet("Records")
    for i, d in enumerate(drafts):
        col = 1 + 4 * i
        ws.cell(1, col, f"{d.name} Player")
        ws.cell(1, col + 1, "Wins")
        ws.cell(1, col + 2, "Losses")
        for c in range(col, col + 3):
            ws.cell(1, c).font = HEADER_FONT
            ws.cell(1, c).fill = HEADER_FILL
        for j, p in enumerate(d.players):
            w, l = d.records.get(p, (0, 0))
            ws.cell(2 + j, col, p)
            ws.cell(2 + j, col + 1, w).alignment = CENTER
            ws.cell(2 + j, col + 2, l).alignment = CENTER
        ws.column_dimensions[get_column_letter(col)].width = 18

    def card_record(card):
        w = l = 0
        for d in drafts:
            p = d.picks.get(card)
            if p:
                dw, dl = d.records.get(p.player, (0, 0))
                w, l = w + dw, l + dl
        return w, l

    def sort_key(entry):
        card = entry[0]
        w, l = card_record(card)
        rate = w / (w + l) if w + l else -1
        return (-w, -rate, card)

    # layout: Card/Type/Color, then the 9 summary columns (D..L), then a
    # 4-column block per draft — summary up front so it's readable without
    # scrolling past 13 pods
    ws = wb.create_sheet("Win Rates")
    header = ["Card", "Type", "Color"]
    header += [
        "Wins (Drafted)", "Losses (Drafted)", "Win Rate (Drafted)",
        "Wins (Maindeck)", "Losses (Maindeck)", "Win Rate (Maindeck)",
        "Maindecked", "Decks Known", "Color Group",
    ]
    for d in drafts:
        header += [f"{d.name} Picked By", f"{d.name} W", f"{d.name} L", f"{d.name} MD"]
    ws.append(header)

    n_d = len(drafts)
    FIRST_DRAFT_COL = 13  # per-draft blocks start here (after summary D..L)
    drafted_cards = [
        entry for entry in cube if any(d.picks.get(entry[0]) for d in drafts)
    ]
    for card, ctype, color in sorted(drafted_cards, key=sort_key):
        r = ws.max_row + 1
        if formulas:
            lookup = f"=VLOOKUP($A{r},'Card List'!$A:$D,{{}},FALSE)"
            per_draft = []
            for i, d in enumerate(drafts):
                n = len(d.players)
                last = 1 + len(d.rounds)
                rng = f"'{d.name}'!$B$2:${get_column_letter(1 + n)}${last}"
                hdr = f"'{d.name}'!$B$1:${get_column_letter(1 + n)}$1"
                pc = f"${get_column_letter(FIRST_DRAFT_COL + 4 * i)}{r}"
                rec_a = get_column_letter(1 + 4 * i)
                rec_c = get_column_letter(3 + 4 * i)
                rec = f"Records!${rec_a}$2:${rec_c}${1 + n}"
                has_deck = f'COUNTIFS(Decks!$A:$A,"{d.name}",Decks!$B:$B,{pc})'
                in_main = "+".join(
                    f'COUNTIFS(Decks!$A:$A,"{d.name}",Decks!$B:$B,{pc},'
                    f'Decks!$C:$C,$A{r},Decks!$D:$D,"{z}")'
                    for z in MAIN_ZONES
                )
                per_draft.append(
                    f"=IFERROR(INDEX({hdr},"
                    f"SUMPRODUCT(({rng}=$A{r})*COLUMN({rng}))-1),\"\")"
                )
                per_draft.append(f'=IF({pc}="","",VLOOKUP({pc},{rec},2,FALSE))')
                per_draft.append(f'=IF({pc}="","",VLOOKUP({pc},{rec},3,FALSE))')
                per_draft.append(
                    f'=IF({pc}="","",IF({has_deck}=0,"",'
                    f'IF(({in_main})>0,"Y","N")))'
                )
            wcells = ",".join(f"${get_column_letter(FIRST_DRAFT_COL + 1 + 4 * i)}{r}"
                              for i in range(n_d))
            lcells = ",".join(f"${get_column_letter(FIRST_DRAFT_COL + 2 + 4 * i)}{r}"
                              for i in range(n_d))
            mds = [f"${get_column_letter(FIRST_DRAFT_COL + 3 + 4 * i)}{r}"
                   for i in range(n_d)]
            known = "+".join(f'({m}<>"")' for m in mds)
            ycount = "+".join(f'({m}="Y")' for m in mds)
            wmd_sum = "+".join(
                f'IF({m}="Y",${get_column_letter(FIRST_DRAFT_COL + 1 + 4 * i)}{r},0)'
                for i, m in enumerate(mds)
            )
            lmd_sum = "+".join(
                f'IF({m}="Y",${get_column_letter(FIRST_DRAFT_COL + 2 + 4 * i)}{r},0)'
                for i, m in enumerate(mds)
            )
            wt, lt, wm, lm = f"$D{r}", f"$E{r}", f"$G{r}", f"$H{r}"
            row = [card, lookup.format(2), lookup.format(3)] + [
                f'=IF(COUNT({wcells})=0,"",SUM({wcells}))',
                f'=IF(COUNT({lcells})=0,"",SUM({lcells}))',
                f'=IF(OR({wt}="",({wt}+{lt})=0),"",{wt}/({wt}+{lt}))',
                f"={wmd_sum}",
                f"={lmd_sum}",
                f'=IF(({wm}+{lm})=0,"",{wm}/({wm}+{lm}))',
                f"={ycount}",
                f"={known}",
                f'=IF(LEN($C{r})>1,"Multi",IF($C{r}="","C",$C{r}))',
            ] + per_draft
        else:
            per_draft = []
            w = l = w_md = l_md = md_y = md_known = 0
            for d in drafts:
                p = d.picks.get(card)
                if p:
                    dw, dl = d.records.get(p.player, (0, 0))
                    deck = decks.get((d.name, p.player))
                    if deck is None:
                        md = None
                    else:
                        md = "Y" if deck.get(card) in MAIN_ZONES else "N"
                        md_known += 1
                        if md == "Y":
                            md_y += 1
                            w_md, l_md = w_md + dw, l_md + dl
                    per_draft += [p.player, dw, dl, md]
                    w, l = w + dw, l + dl
                else:
                    per_draft += [None, None, None, None]
            row = [card, ctype, color] + [
                w,
                l,
                w / (w + l) if w + l else None,
                w_md,
                l_md,
                w_md / (w_md + l_md) if w_md + l_md else None,
                md_y,
                md_known,
                "Multi" if len(color or "") > 1 else (color or "C"),
            ] + per_draft
        ws.append(row)
        style_card_cell(ws.cell(r, 1), color)
        for c in range(3, len(header) + 1):
            ws.cell(r, c).alignment = CENTER
        ws.cell(r, 6).number_format = "0.0%"
        ws.cell(r, 9).number_format = "0.0%"

    style_header(ws)
    ws.freeze_panes = "B2"
    ws.column_dimensions["A"].width = 32
    ws.column_dimensions["B"].width = 32
    for i in range(n_d):
        ws.column_dimensions[get_column_letter(FIRST_DRAFT_COL + 4 * i)].width = 16
    ws.auto_filter.ref = ws.dimensions

    # win rates: red (low) -> green (high), fixed 0..1 scale
    for col in (6, 9):
        letter = get_column_letter(col)
        ws.conditional_formatting.add(
            f"{letter}2:{letter}{ws.max_row}",
            ColorScaleRule(
                start_type="num", start_value=0, start_color="E67C73",
                mid_type="num", mid_value=0.5, mid_color="FFD666",
                end_type="num", end_value=1, end_color="57BB8A",
            ),
        )


def main():
    args = sys.argv[1:]
    formulas = "--values" not in args
    md_picks = "--md-picks" in args
    teams_frac = None
    if "--teams-frac" in args:
        i = args.index("--teams-frac")
        teams_frac = float(args[i + 1])
        del args[i:i + 2]
    decks_path_arg = None
    if "--decks" in args:
        i = args.index("--decks")
        decks_path_arg = args[i + 1]
        del args[i:i + 2]
    args = [a for a in args if a not in ("--values", "--md-picks")]
    if len(args) < 2:
        sys.exit(__doc__)
    out, inputs = args[0], args[1:]

    drafts, cube, seen, availability = [], [], set(), {}
    for i, spec in enumerate(inputs):
        name, _, path = spec.rpartition("=")
        if not name:
            name, path = f"Draft {i + 1}", spec
        dpa = DOUBLE_PICK_AFTER
        if "@" in path:
            path, _, dstr = path.rpartition("@")
            dpa = None if dstr in ("none", "None") else int(dstr)
        draft, cube_list = parse_draft(path, name, dpa)
        drafts.append(draft)
        for entry in cube_list:
            availability[entry[0]] = availability.get(entry[0], 0) + 1
            if entry[0] not in seen:
                seen.add(entry[0])
                cube.append(entry)
    partial = {c: n for c, n in availability.items() if n < len(drafts)}
    if partial:
        print(f"note: {len(partial)} cards not in every draft's cube list", file=sys.stderr)

    # canonicalize pick names against the cube list (drafts sheets are hand-typed)
    canonical = {c.casefold(): c for c, _, _ in cube}
    for d in drafts:
        for card in list(d.picks):
            if card in seen:
                continue
            fixed = canonical.get(card.casefold())
            if not fixed:  # hand-typed shorthand, e.g. 'air temple'
                subs = [c for k, c in canonical.items() if card.casefold() in k]
                if len(subs) == 1:
                    fixed = subs[0]
                    print(f"note: {d.name}: pick {card!r} -> {fixed!r}", file=sys.stderr)
            if fixed:
                d.picks[fixed] = d.picks.pop(card)
                # rewrite the grid copy too: the sheet formulas look the
                # canonical name up in the draft tab (Sheets' = is already
                # case-insensitive, but shorthand needs the real text)
                d.rounds = [[fixed if c == card else c for c in row]
                            for row in d.rounds]
            else:
                print(f"warning: {d.name}: pick {card!r} not in any cube list", file=sys.stderr)

    decks_path = (pathlib.Path(decks_path_arg) if decks_path_arg
                  else pathlib.Path(__file__).parent / "decks.tsv")
    decks, links = {}, []
    if md_picks:
        # fallback semantics: every drafted card counts as maindecked
        for d in drafts:
            for card, p in d.picks.items():
                decks.setdefault((d.name, p.player), {})[card] = "main"
    elif decks_path.exists():
        decks, main_sizes, links = load_decks(decks_path, cube)
        # duplicated lands: the grid may hold 'Hallowed Fountain 2' while
        # the sealeddeck pool just says 'Hallowed Fountain' — give the
        # suffixed pick its base card's zone in that player's deck
        for d in drafts:
            for card, p in d.picks.items():
                if not card.endswith(" 2"):
                    continue
                deck = decks.get((d.name, p.player))
                base = card[:-2].strip()
                if deck and base in deck:
                    deck.setdefault(card, deck[base])
        check_deck_coverage(decks, main_sizes, drafts)
    build_workbook(
        drafts, cube, availability, formulas=formulas, decks=decks,
        links=links, teams_frac=teams_frac
    ).save(out)
    total = sum(len(d.picks) for d in drafts)
    print(f"{out}: {len(cube)} cards, {len(drafts)} drafts, {total} picks")


if __name__ == "__main__":
    main()
