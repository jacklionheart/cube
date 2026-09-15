"""Author and execute notebooks/players.ipynb without jupyter tooling.

Cells are defined below; code cells run top-to-bottom in one namespace
with stdout captured and baked into the notebook as stream outputs.

Usage: python3 notebooks/build_players_nb.py
"""

import contextlib
import io
import json
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

MD = "markdown"
CODE = "code"

CELLS = [
    (MD, """# By-person analysis of the LoL cube rotos

Who drives lanes, who blends, who freelances — player-level views over
the three-draft package data. Vocabulary: a **Lane** is a card core
maindecked by three different people (one per draft) plus its flex
orbit; a **Team** is the 5+ card block two decks from different drafts
agreed on; a deck **merges** when it holds teams with two different
decks of the same other draft.

Regenerate data first if stale: `python3 refresh.py --dry-run`."""),
    (CODE, '''\
import contextlib, io, os, subprocess, sys
sys.path.insert(0, os.path.abspath(".."))
import pandas as pd
from packages import (load, maindeck_owners, signature_groups, deck_sets,
                      team_partners, straddles, load_themes, load_scryfall,
                      card_colors, theme_str)

with contextlib.redirect_stderr(io.StringIO()):  # known junk-card warnings
    drafts, cube, decks = load()
owners = maindeck_owners(drafts, cube, decks)
groups = signature_groups(owners)
by_deck = deck_sets(owners)
partners = team_partners(owners)
merged = straddles(owners, drafts)
themes, scry = load_themes(), load_scryfall()
colors = {c: card_colors(c, scry) for c, _, _ in cube}
def colors_of(cards):
    u = set().union(*(colors[c] for c in cards)) if cards else set()
    return "".join(x for x in "WUBRG" if x in u) or "C"
lanes_of = {}
for gi, (sig, cards) in enumerate(groups):
    for k, p in enumerate(sig):
        lanes_of.setdefault((k, p), []).append(gi)
print(f"{len(drafts)} drafts, {sum(len(d.players) for d in drafts)} players, "
      f"{len(groups)} lanes, "
      f"{sum(len(pl) for bd in partners.values() for pl in bd.values())//2} team pairings")'''),
    (MD, "## Per-player summary — one row per deck: what did each person build, own, and merge?"),
    (CODE, '''\
rows = []
for k, d in enumerate(drafts):
    for p in d.players:
        deck = by_deck[(k, p)]
        w, l = d.records.get(p, (0, 0))
        lanes = [f"P{gi+1} {theme_str(groups[gi][1], themes)}"
                 for gi in lanes_of.get((k, p), [])]
        n_teams = sum(len(pl) for pl in partners[(k, p)].values())
        n_merge = sum(1 for pl in merged.get((k, p), {}).values())
        rows.append({"draft": d.name, "player": p, "cards": len(deck),
                     "colors": colors_of(deck), "lanes": ", ".join(lanes) or "—",
                     "teams": n_teams, "merge cases": n_merge,
                     "record": f"{w}–{l}"})
df = pd.DataFrame(rows)
print(df.to_string(index=False))'''),
    (MD, "## Taxonomy — blenders, mergers, lane-drivers, free agents"),
    (CODE, '''\
all_decks = [(k, p) for k, d in enumerate(drafts) for p in d.players]
blend = [d for d, bd in merged.items() if len(bd) == 2]
single = [d for d, bd in merged.items() if len(bd) == 1]
non = [d for d in all_decks if d not in merged]
drivers = [d for d in non if d in lanes_of]
free = [d for d in non if d not in lanes_of]
for label, ds in [("Both-way blenders", blend), ("Single-side mergers", single),
                  ("Pure lane-drivers", drivers), ("Free agents", free)]:
    names = ", ".join(f"{drafts[k].name[-1]}:{p}" for k, p in sorted(ds))
    print(f"{label:20s} {len(ds):2d}  {names}")'''),
    (MD, "## Multi-lane players — same theme twice (the seam inside one archetype) vs genuinely two archetypes"),
    (CODE, '''\
for (k, p), gis in sorted(lanes_of.items()):
    if len(gis) < 2:
        continue
    ts = [theme_str(groups[gi][1], themes) for gi in gis]
    kind = "SAME theme twice" if len(set(ts)) == 1 else "cross-theme"
    print(f"{drafts[k].name} {p:16s} {' + '.join(ts):24s} ({kind})")'''),
    (MD, "## Merge detail — who merged what, against whom"),
    (CODE, '''\
for (k, p), bd in sorted(merged.items()):
    for k2, plist in sorted(bd.items()):
        parts = ", ".join(
            f"{pb} [{len(core)}"
            + (f" {theme_str(core, themes)}" if theme_str(core, themes) else "")
            + "]"
            for pb, core in sorted(plist, key=lambda x: -len(x[1])))
        print(f"{drafts[k].name} {p:16s} vs {drafts[k2].name}: {parts}")'''),
    (MD, "## The merge report — full decklists with team groupings, as HTML"),
    (CODE, '''\
out = subprocess.run([sys.executable, "report.py"], cwd="..",
                     capture_output=True, text=True)
path = os.path.abspath(os.path.join("..", "out", "merge-report.html"))
print(f"written: {path}")
try:
    from IPython.display import IFrame, display
    display(IFrame(os.path.relpath(path), width="100%", height=600))
except ImportError:
    print("(open in a browser)")'''),
]


def run():
    ns = {}
    nb_cells = []
    old_cwd = os.getcwd()
    for i, (kind, src) in enumerate(CELLS):
        cell = {"id": f"c{i}", "cell_type": kind, "metadata": {},
                "source": src.splitlines(keepends=True)}
        if kind == CODE:
            buf = io.StringIO()
            os.chdir(HERE / "notebooks")
            try:
                with contextlib.redirect_stdout(buf):
                    exec(compile(src, f"<cell {i}>", "exec"), ns)
            finally:
                os.chdir(old_cwd)
            cell["execution_count"] = i
            cell["outputs"] = []
            if buf.getvalue():
                cell["outputs"].append({
                    "output_type": "stream", "name": "stdout",
                    "text": buf.getvalue().splitlines(keepends=True)})
        nb_cells.append(cell)
    nb = {"nbformat": 4, "nbformat_minor": 5,
          "metadata": {"kernelspec": {"name": "python3",
                                      "display_name": "Python 3",
                                      "language": "python"},
                       "language_info": {"name": "python"}},
          "cells": nb_cells}
    dest = HERE / "notebooks" / "players.ipynb"
    dest.write_text(json.dumps(nb, ensure_ascii=False, indent=1))
    print(dest)


if __name__ == "__main__":
    run()
