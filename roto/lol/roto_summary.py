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
from roto.decks import load_decks
from roto.xlstyle import (COLOR_FILLS, HEADER_FILL, HEADER_FONT, CARD_FONT,
                          CENTER, color_fill, style_card_cell, style_header)


import openpyxl
from openpyxl.chart import BarChart, Reference
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

def parse_draft(path, name):
    return _parse_draft(path, name, dpa=None)


COLOR_GROUPS = ["W", "U", "B", "R", "G", "Multi", "C"]


def build_color_analysis(wb, drafts, formulas):
    """Per-color aggregates over the Win Rates tab, with bar charts."""
    wr = wb["Win Rates"]
    n = wr.max_row
    n_d = len(drafts)
    base = 4 + 4 * n_d
    col = {  # Win Rates column letters
        "wrd": get_column_letter(base + 2), "wrm": get_column_letter(base + 5),
        "md": get_column_letter(base + 6), "grp": get_column_letter(base + 8),
    }
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
                if row[base + 7] != g:
                    continue
                drafted += 1
                if row[base + 5] > 0:
                    md += 1
                if isinstance(row[base + 1], (int, float)):
                    wrd.append(row[base + 1])
                if isinstance(row[base + 4], (int, float)):
                    wrm.append(row[base + 4])
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


def build_md_together(wb, drafts, cube, decks):
    """Maximal groups of cards maindecked together (same deck) in every
    draft. Cards group iff they share the same deck-owner signature across
    all drafts, so pairs/triplets/bigger clusters all fall out at once.
    Pure co-occurrence analysis — computed here, not by sheet formulas.
    Group numbering and order match packages.py (P#: size desc)."""
    import packages as pk

    owners_map = pk.maindeck_owners(drafts, cube, decks)
    groups = pk.signature_groups(owners_map)
    scry = pk.load_scryfall()
    themes = pk.load_themes()

    flex_by_group = pk.flex_packages(groups, owners_map)

    ws = wb.create_sheet("Lanes (all 3 drafts)")
    header = ["Group", "Theme", "Colors", "Core — in all 3 decks",
              "Flex — in 2 of 3 (marked: the deck that skipped it)",
              "All Cards", "Core #", "Flex #", "Total #"]
    header += [f"{d.name} Player" for d in drafts]
    header += ["Wins", "Losses", "Win Rate"]
    ws.append(header)
    style_header(ws)
    for i, (sig, cards) in enumerate(groups):
        w = l = 0
        for d, p in zip(drafts, sig):
            dw, dl = d.records.get(p, (0, 0))
            w, l = w + dw, l + dl
        wr = w / (w + l) if w + l else None
        e = flex_by_group[i]
        flex_lines = []
        for k, bucket in enumerate(e["flex"]):
            flex_lines += [f"{c}  — not in {drafts[k].name}" for c in bucket]
        n_flex = sum(len(b) for b in e["flex"])
        all_cards = list(cards) + [c for b in e["flex"] for c in b]
        ws.append([i + 1, pk.theme_str(all_cards, themes),
                   pk.colors_str(cards, scry),  # colors from core only
                   "\n".join(sorted(cards)), "\n".join(flex_lines),
                   "\n".join(sorted(all_cards)),
                   len(cards), n_flex, len(all_cards),
                   *sig, w, l, wr])
        r = ws.max_row
        for c in (4, 5, 6):
            ws.cell(r, c).alignment = Alignment(wrap_text=True)
        for c in (1, 2, 3, *range(7, len(header) + 1)):
            ws.cell(r, c).alignment = CENTER
        ws.cell(r, len(header)).number_format = "0.0%"
    ws.freeze_panes = "A2"
    ws.column_dimensions["B"].width = 14
    for col in "DEF":
        ws.column_dimensions[col].width = 38
    for i in range(len(drafts)):
        ws.column_dimensions[get_column_letter(10 + i)].width = 16
    ws.auto_filter.ref = ws.dimensions
    wr_col = get_column_letter(len(header))
    ws.conditional_formatting.add(
        f"{wr_col}2:{wr_col}{ws.max_row}",
        ColorScaleRule(
            start_type="num", start_value=0, start_color="E67C73",
            mid_type="num", mid_value=0.5, mid_color="FFD666",
            end_type="num", end_value=1, end_color="57BB8A",
        ),
    )


def build_package_tabs(wb, drafts, cube, decks):
    """Two relaxed-package views alongside Maindecked Together (the strict
    all-cards/all-drafts definition). 'Packages 2 of 3': maximal sets fully
    maindecked together in 2 of 3 drafts (cross-draft deck-pair
    intersections; +2 slack cards fit if one miss per deck is allowed).
    'Packages ±1 Card': each strict package plus per-draft flex buckets —
    cards in the other two decks of the same triple, absent from this
    draft's deck. Computed here, not by sheet formulas."""
    import packages as pk

    owners = pk.maindeck_owners(drafts, cube, decks)
    groups = pk.signature_groups(owners)
    scry = pk.load_scryfall()
    themes = pk.load_themes()

    ws = wb.create_sheet("Teams (2 of 3)")
    header = ["#", "Size", "Theme", "Colors", "Cards", "Deck A", "Deck B",
              "Contains Lane Core"]
    ws.append(header)
    style_header(ws)
    strict = [(i + 1, set(cards)) for i, (_, cards) in enumerate(groups)]
    for n, e in enumerate(pk.pair_packages(owners)):
        (ka, pa), (kb, pb) = e["decks"]
        contains = ", ".join(f"P{i}" for i, s in strict if s <= e["core"])
        ws.append([n + 1, len(e["core"]), pk.theme_str(e["core"], themes),
                   pk.colors_str(e["core"], scry),
                   "\n".join(sorted(e["core"])),
                   f"{drafts[ka].name}: {pa}", f"{drafts[kb].name}: {pb}",
                   contains])
        r = ws.max_row
        ws.cell(r, 5).alignment = Alignment(wrap_text=True)
        for c in (1, 2, 3, 4):
            ws.cell(r, c).alignment = CENTER
    ws.freeze_panes = "A2"
    for col, w in zip("ABCDEFGH", (5, 6, 14, 9, 42, 20, 20, 16)):
        ws.column_dimensions[col].width = w
    ws.auto_filter.ref = ws.dimensions





def build_workbook(drafts, cube, availability, formulas=True, decks=None, links=None):
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
    wr_end = get_column_letter(4 + 4 * n_d + 8)  # Win Rates last column
    wr_md_col = lambda i: 7 + 4 * i  # per-draft MD column in Win Rates
    wr_mdcount_col = 4 + 4 * n_d + 6  # Maindecked column in Win Rates

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
            round(sum(overalls) / len(overalls), 1) if overalls else None,
            round(sum(rounds) / len(rounds), 1) if rounds else None,
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
            seat = f"SUMPRODUCT(({rng}=$A{r})*COLUMN({rng}))-1"
            row.append(
                f'=IF(SUMPRODUCT(--({rng}=$A{r}))=0,"",'
                f"SUMPRODUCT(({rng}=$A{r})*{rcol}))"
            )
            row.append(
                f'=IF({rc}="","",({rc}-1)*{n}'
                f"+IF(ISODD({rc}),{seat},{n}+1-({seat})))"
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
    build_color_analysis(wb, drafts, formulas)
    build_md_together(wb, drafts, cube, decks or {})
    build_package_tabs(wb, drafts, cube, decks or {})

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

    order = ["Pick Summary", "Color Analysis", "Lanes (all 3 drafts)",
             "Teams (2 of 3)", "Card List"]
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

    ws = wb.create_sheet("Win Rates")
    header = ["Card", "Type", "Color"]
    for d in drafts:
        header += [f"{d.name} Picked By", f"{d.name} W", f"{d.name} L", f"{d.name} MD"]
    header += [
        "Wins (Drafted)", "Losses (Drafted)", "Win Rate (Drafted)",
        "Wins (Maindeck)", "Losses (Maindeck)", "Win Rate (Maindeck)",
        "Maindecked", "Decks Known", "Color Group",
    ]
    ws.append(header)

    n_d = len(drafts)
    base = 4 + 4 * n_d  # first totals column (Wins (Drafted))
    drafted_cards = [
        entry for entry in cube if any(d.picks.get(entry[0]) for d in drafts)
    ]
    for card, ctype, color in sorted(drafted_cards, key=sort_key):
        r = ws.max_row + 1
        if formulas:
            lookup = f"=VLOOKUP($A{r},'Card List'!$A:$D,{{}},FALSE)"
            row = [card, lookup.format(2), lookup.format(3)]
            for i, d in enumerate(drafts):
                n = len(d.players)
                last = 1 + len(d.rounds)
                rng = f"'{d.name}'!$B$2:${get_column_letter(1 + n)}${last}"
                hdr = f"'{d.name}'!$B$1:${get_column_letter(1 + n)}$1"
                pc = f"${get_column_letter(4 + 4 * i)}{r}"
                rec_a = get_column_letter(1 + 4 * i)
                rec_c = get_column_letter(3 + 4 * i)
                rec = f"Records!${rec_a}$2:${rec_c}${1 + n}"
                has_deck = f'COUNTIFS(Decks!$A:$A,"{d.name}",Decks!$B:$B,{pc})'
                in_main = "+".join(
                    f'COUNTIFS(Decks!$A:$A,"{d.name}",Decks!$B:$B,{pc},'
                    f'Decks!$C:$C,$A{r},Decks!$D:$D,"{z}")'
                    for z in MAIN_ZONES
                )
                row.append(
                    f"=IFERROR(INDEX({hdr},"
                    f"SUMPRODUCT(({rng}=$A{r})*COLUMN({rng}))-1),\"\")"
                )
                row.append(f'=IF({pc}="","",VLOOKUP({pc},{rec},2,FALSE))')
                row.append(f'=IF({pc}="","",VLOOKUP({pc},{rec},3,FALSE))')
                row.append(
                    f'=IF({pc}="","",IF({has_deck}=0,"",'
                    f'IF(({in_main})>0,"Y","N")))'
                )
            wcells = ",".join(f"${get_column_letter(5 + 4 * i)}{r}" for i in range(n_d))
            lcells = ",".join(f"${get_column_letter(6 + 4 * i)}{r}" for i in range(n_d))
            mds = [f"${get_column_letter(7 + 4 * i)}{r}" for i in range(n_d)]
            known = "+".join(f'({m}<>"")' for m in mds)
            ycount = "+".join(f'({m}="Y")' for m in mds)
            wmd_sum = "+".join(
                f'IF({m}="Y",${get_column_letter(5 + 4 * i)}{r},0)' for i, m in enumerate(mds)
            )
            lmd_sum = "+".join(
                f'IF({m}="Y",${get_column_letter(6 + 4 * i)}{r},0)' for i, m in enumerate(mds)
            )
            wt, lt = f"${get_column_letter(base)}{r}", f"${get_column_letter(base + 1)}{r}"
            wm, lm = f"${get_column_letter(base + 3)}{r}", f"${get_column_letter(base + 4)}{r}"
            row += [
                f'=IF(COUNT({wcells})=0,"",SUM({wcells}))',
                f'=IF(COUNT({lcells})=0,"",SUM({lcells}))',
                f'=IF(OR({wt}="",({wt}+{lt})=0),"",{wt}/({wt}+{lt}))',
                f"={wmd_sum}",
                f"={lmd_sum}",
                f'=IF(({wm}+{lm})=0,"",{wm}/({wm}+{lm}))',
                f"={ycount}",
                f"={known}",
                f'=IF(LEN($C{r})>1,"Multi",IF($C{r}="","C",$C{r}))',
            ]
        else:
            row = [card, ctype, color]
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
                    row += [p.player, dw, dl, md]
                    w, l = w + dw, l + dl
                else:
                    row += [None, None, None, None]
            row += [
                w,
                l,
                w / (w + l) if w + l else None,
                w_md,
                l_md,
                w_md / (w_md + l_md) if w_md + l_md else None,
                md_y,
                md_known,
                "Multi" if len(color or "") > 1 else (color or "C"),
            ]
        ws.append(row)
        style_card_cell(ws.cell(r, 1), color)
        for c in range(3, len(header) + 1):
            ws.cell(r, c).alignment = CENTER
        ws.cell(r, base + 2).number_format = "0.0%"
        ws.cell(r, base + 5).number_format = "0.0%"

    style_header(ws)
    ws.freeze_panes = "B2"
    ws.column_dimensions["A"].width = 32
    ws.column_dimensions["B"].width = 32
    for i in range(n_d):
        ws.column_dimensions[get_column_letter(4 + 4 * i)].width = 16
    ws.auto_filter.ref = ws.dimensions

    # win rates: red (low) -> green (high), fixed 0..1 scale
    for col in (base + 2, base + 5):
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
    args = [a for a in args if a != "--values"]
    if len(args) < 2:
        sys.exit(__doc__)
    out, inputs = args[0], args[1:]

    drafts, cube, seen, availability = [], [], set(), {}
    for i, path in enumerate(inputs):
        draft, cube_list = parse_draft(path, f"Draft {i + 1}")
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
            if fixed:
                d.picks[fixed] = d.picks.pop(card)
            else:
                print(f"warning: {d.name}: pick {card!r} not in any cube list", file=sys.stderr)

    decks_path = pathlib.Path(__file__).parent / "decks.tsv"
    decks, links = {}, []
    if decks_path.exists():
        decks, main_sizes, links = load_decks(decks_path, cube)
        check_deck_coverage(decks, main_sizes, drafts)
    build_workbook(
        drafts, cube, availability, formulas=formulas, decks=decks, links=links
    ).save(out)
    total = sum(len(d.picks) for d in drafts)
    print(f"{out}: {len(cube)} cards, {len(drafts)} drafts, {total} picks")


if __name__ == "__main__":
    main()
