"""Cube-independent draft template parsing and pick-order arithmetic.

Pass dpa=None for plain snake, or the round after which picks double.
Source paths and draft names are always supplied by the caller.
"""
import math
import sys
from dataclasses import dataclass, field
import openpyxl

DRAFT_SHEET = "Draft"
CUBE_SHEET = "Cube"
MATCHES_SHEET = "Matches"
FIRST_ROUND_ROW = 4
PLAYER_HEADER_ROW = 3
FIRST_PLAYER_COL = 3  # column C

def round1(x):
    """One-decimal rounding with Sheets' ROUND semantics (half away from
    zero) — Python's round() is half-even and disagrees on .X5 averages."""
    return math.floor(x * 10 + 0.5) / 10


def overall_pick(rnd, seat, n, dpa=None):
    """True overall pick number for grid position (round, 1-based seat)."""
    if dpa is None or rnd <= dpa:
        return (rnd - 1) * n + (seat if rnd % 2 == 1 else n + 1 - seat)
    k = (rnd - dpa - 1) // 2  # pair of rounds per traversal
    # pair k runs left-to-right when its parity matches dpa's
    pair_lr = (dpa % 2 == 1) == (k % 2 == 1)
    idx = (seat - 1) if pair_lr else (n - seat)
    return dpa * n + k * 2 * n + 2 * idx + 1 + (rnd - dpa - 1 - 2 * k)


@dataclass
class Pick:
    round: int
    overall: int
    player: str


@dataclass
class Draft:
    name: str
    players: list
    dpa: int = None  # double-pick-after round (None = plain)
    rounds: list = field(default_factory=list)  # list of rows of card names
    picks: dict = field(default_factory=dict)  # card -> Pick
    records: dict = field(default_factory=dict)  # player -> [match wins, losses]


def parse_draft(path, name, dpa=None):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb[DRAFT_SHEET]

    players = []
    col = FIRST_PLAYER_COL
    while True:
        v = ws.cell(PLAYER_HEADER_ROW, col).value
        if v is None or str(v).strip() == "":
            break
        players.append(str(v).strip())
        col += 1

    draft = Draft(name=name, players=players, dpa=dpa)
    n = len(players)
    row = FIRST_ROUND_ROW
    while ws.cell(row, 1).value is not None:
        rnd = int(ws.cell(row, 1).value)
        cards = [ws.cell(row, FIRST_PLAYER_COL + i).value for i in range(n)]
        cards = [str(c).strip() if c is not None else None for c in cards]
        draft.rounds.append(cards)
        seats = range(n) if dpa is not None or rnd % 2 else range(n - 1, -1, -1)
        for seat0 in seats:
            card = cards[seat0]
            if card:
                overall = overall_pick(rnd, seat0 + 1, n, dpa)
                if card in draft.picks:
                    print(f"warning: {name}: {card!r} picked twice", file=sys.stderr)
                draft.picks[card] = Pick(rnd, overall, players[seat0])
        row += 1

    draft.records = {p: [0, 0] for p in players}
    for mrow in wb[MATCHES_SHEET].iter_rows(min_row=3, values_only=True):
        p1, p2, m1, m2 = mrow[1], mrow[5], mrow[6], mrow[7]
        if not p1 or not p2 or m1 is None or m2 is None:
            continue
        r1 = draft.records.setdefault(str(p1).strip(), [0, 0])
        r2 = draft.records.setdefault(str(p2).strip(), [0, 0])
        r1[0] += int(m1)
        r1[1] += int(m2)
        r2[0] += int(m2)
        r2[1] += int(m1)

    cube = []
    cws = wb[CUBE_SHEET]
    for r in range(2, cws.max_row + 1):
        card = cws.cell(r, 2).value
        if card is None or str(card).strip() == "":
            continue
        cube.append(
            (str(card).strip(), cws.cell(r, 3).value or "", cws.cell(r, 4).value or "")
        )
    wb.close()
    return draft, cube
