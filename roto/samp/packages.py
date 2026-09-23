"""Package analysis over the roto drafts' maindecks.

A *package* is a maximal set of at least MIN_PACKAGE_SIZE (3) cards
maindecked in the same deck in every draft (identical deck-owner
signature). Edges connect packages whose
signatures agree in 2 of 3 drafts — packages that traveled together but
split once, i.e. real draft-time choices. Connected components are
archetype super-clusters. *Halos* loosen the definition: cards that shared
a maindeck with every member of a package in >= 2 drafts.

Everything is companion-aware (a sideboard Lurrus counts as maindecked
only when the deck satisfies its requirement — see roto_summary).

CLI:
  python3 packages.py             strict packages, edges, components
  python3 packages.py --loose     per-package halos (>=2/3 co-maindecked)
  python3 packages.py --mermaid   graph as a mermaid diagram
  python3 packages.py --null [--iters N] [--seed S]
                                  permutation test of package counts

The null model tests the DECKBUILD stage only: picks stay exactly as
drafted (correlated by intent), but each player's maindeck is replaced by
a uniform random same-size subset of their own picks. It answers "given
what people picked, are the shared maindeck choices surprising?" — not
"are picks correlated?".
"""

import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from roto import packages as _analysis
from roto import colors as _colors
from roto.packages import (maindeck_owners, package_edges, components, co_maindeck_counts, halos, loose_components, never_drafted, never_maindecked, late_first_pick, theme_str, deck_sets, flex_packages, unique_ensembles)
from roto.colors import WUBRG, is_land, nonland_owners, combo_color

from collections import defaultdict
from itertools import combinations

from roto_summary import MAIN_ZONES, load_decks, parse_draft

HERE = pathlib.Path(__file__).parent


def _signature_groups(owners, min_size):
    return _analysis.signature_groups(owners, min_size, min_shared=MIN_SHARED_DRAFTS)


def _pair_packages(owners, min_core):
    return _analysis.pair_packages(owners, min_core)


def card_colors(name, scry):
    return _colors.card_colors(name, scry, include_flashback=False)


def colors_str(cards, scry):
    return _colors.colors_str(cards, scry, include_flashback=False)


def team_partners(owners):
    return _analysis.team_partners(owners, min_core=MIN_PAIR_CORE)


def straddles(owners, drafts):
    return _analysis.straddles(owners, drafts, min_core=MIN_PAIR_CORE)


def null_model(drafts, cube, decks, iters=2000, seed=0):
    return _analysis.null_model(drafts, cube, decks, iters, seed,
                                min_size=MIN_PACKAGE_SIZE, min_shared=MIN_SHARED_DRAFTS)


def load():
    """Load the configured Samp pods and their submitted decklists."""
    import refresh
    drafts, cube, seen = [], [], set()
    for name in refresh.SOURCES:
        draft, cards = parse_draft(HERE / "sources" / f"{refresh.slugify(name)}.xlsx", name)
        drafts.append(draft)
        for card in cards:
            if card[0] not in seen:
                seen.add(card[0])
                cube.append(card)
    canonical = {c.casefold(): c for c, _, _ in cube}
    for draft in drafts:
        for card in list(draft.picks):
            fixed = canonical.get(card.casefold())
            if fixed and fixed != card:
                draft.picks[fixed] = draft.picks.pop(card)
    decks, _, _ = load_decks(HERE / "decks.tsv", cube)
    return drafts, cube, decks


MIN_PACKAGE_SIZE = 3
MIN_SHARED_DRAFTS = 2  # partial signatures must span at least this many


def signature_groups(owners, min_size=None):
    if min_size is None:
        min_size = MIN_PACKAGE_SIZE
    return _signature_groups(owners, min_size)


WUBRG = "WUBRG"
BASIC_COLORS = [("Plains", "W"), ("Island", "U"), ("Swamp", "B"),
                ("Mountain", "R"), ("Forest", "G")]


def load_scryfall():
    import json
    return json.loads((HERE / "scryfall.json").read_text())


import re as _re


def load_themes():
    """card -> theme, from hand-labeled themes.tsv (Jack's labels,
    captured from the sheet's Maindecked Together Theme column)."""
    path = HERE / "themes.tsv"
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text().splitlines()[1:]:
        if line.strip():
            card, theme = line.split("\t")
            out[card] = theme
    return out


# real 40-card decks across 11 known-deck pods: 5 admits ~950 pairs,
# 12 keeps the ~130 strongest.
MIN_PAIR_CORE = 12


def pair_packages(owners, min_core=None):
    if min_core is None:
        min_core = MIN_PAIR_CORE
    return _pair_packages(owners, min_core)


def report_straddles(owners, drafts):
    themes = load_themes()
    for (k, p), by_draft in sorted(straddles(owners, drafts).items()):
        for k2, plist in sorted(by_draft.items()):
            print(f"\n{drafts[k].name} {p} straddles {len(plist)} decks "
                  f"of {drafts[k2].name}:")
            for pb, core in sorted(plist, key=lambda x: -len(x[1])):
                t = theme_str(core, themes) or "—"
                cards = ", ".join(sorted(core)[:7])
                more = "..." if len(core) > 7 else ""
                print(f"   with {pb:18s} [{len(core)}] ({t}): {cards}{more}")


def report(groups, edges, comps):
    scry = load_scryfall()
    print(f"{len(groups)} packages, {len(edges)} edges, {len(comps)} components\n")
    for n, comp in enumerate(comps):
        cards_total = sum(len(groups[i][1]) for i in comp)
        print(f"== Component {chr(65 + n)}: {len(comp)} packages, {cards_total} cards")
        for i in comp:
            sig, cards = groups[i]
            print(f"   P{i + 1} [{len(cards)}] {colors_str(cards, scry)} "
                  f"({' / '.join(p or '—' for p in sig)})")
            print(f"      {', '.join(sorted(cards))}")
        for i, j, shared in edges:
            if i in comp:
                print(f"   P{i + 1} -- P{j + 1}  (same deck in draft {shared})")
        print()


def report_halos(groups, pair_counts):
    pairs, comps2 = loose_components(pair_counts)
    n3 = sum(1 for n in pairs.values() if n == 3)
    print(f"LOOSE (>=2/3 co-maindecked): {len(pairs)} pairs "
          f"({n3} in all 3); naive components fuse into "
          f"{len(comps2[0])}-card blob -> use per-package halos instead\n")
    for gi, halo in halos(groups, pair_counts).items():
        if halo:
            cards = sorted(groups[gi][1])
            print(f"P{gi + 1} [{len(cards)}] {', '.join(cards[:3])}"
                  f"{'...' if len(cards) > 3 else ''}")
            print(f"   halo (+{len(halo)}): {', '.join(halo)}")


def report_mermaid(groups, edges, comps):
    print("```mermaid\ngraph TD")
    for n, comp in enumerate(comps):
        print(f"  subgraph {chr(65 + n)}")
        for i in comp:
            first = sorted(groups[i][1])[0].split(",")[0]
            print(f'    P{i + 1}["P{i + 1}: {first} +{len(groups[i][1]) - 1}"]')
        print("  end")
    for i, j, _ in edges:
        print(f"  P{i + 1} --- P{j + 1}")
    print("```")


def report_null(drafts, cube, decks, iters, seed):
    observed, samples = null_model(drafts, cube, decks, iters=iters, seed=seed)
    names = [f"packages (size>={MIN_PACKAGE_SIZE})", "cards in packages",
             "largest package"]
    print(f"NULL MODEL: {iters} random re-deckbuilds of the drafted pools "
          f"(seed {seed})")
    print("stat                 observed   null mean    sd   p95  max   p(null>=obs)")
    for idx, name in enumerate(names):
        vals = sorted(s[idx] for s in samples)
        mean = sum(vals) / len(vals)
        sd = (sum((v - mean) ** 2 for v in vals) / len(vals)) ** 0.5
        p95 = vals[int(0.95 * len(vals))]
        ge = sum(v >= observed[idx] for v in vals)
        p = f"{ge / len(vals):.4f}" if ge else f"< {1 / len(vals):.4f}"
        print(f"{name:<22s} {observed[idx]:>5d} {mean:>11.2f} {sd:>5.2f} "
              f"{p95:>5d} {max(vals):>4d}   {p}")


def main():
    drafts, cube, decks = load()
    owners = maindeck_owners(drafts, cube, decks)
    groups = signature_groups(owners)
    edges = package_edges(groups)
    comps = components(groups, edges)

    if "--null" in sys.argv:
        args = sys.argv
        iters = int(args[args.index("--iters") + 1]) if "--iters" in args else 2000
        seed = int(args[args.index("--seed") + 1]) if "--seed" in args else 0
        print(f"observed: {len(groups)} packages, {len(edges)} edges, "
              f"{len(comps)} components\n")
        report_null(drafts, cube, decks, iters, seed)
        return

    if "--straddles" in sys.argv:
        report_straddles(owners, drafts)
        return

    if "--relax" in sys.argv:
        i = sys.argv.index("--relax")
        k1, k2 = int(sys.argv[i + 1]), int(sys.argv[i + 2])
        if k2 == 0 and k1 == 0:
            report(groups, edges, comps)
        elif k2 == 0:
            for e in flex_packages(groups, owners):
                mx = len(e["cards"]) + sum(1 for f in e["flex"] if f)
                print(f"[{len(e['cards'])}->max {mx}] ({' / '.join(e['sig'])})")
                print(f"   core: {', '.join(sorted(e['cards']))}")
                for k, f in enumerate(e["flex"]):
                    if f:
                        print(f"   flex D{k + 1} (absent there): {', '.join(f)}")
        else:
            extra = " (+2 free slots under k1=1)" if k1 else ""
            for e in pair_packages(owners):
                (ka, pa), (kb, pb) = e["decks"]
                print(f"[{len(e['core'])}{extra}] D{ka + 1} {pa} & D{kb + 1} {pb}")
                print(f"   {', '.join(sorted(e['core']))}")
        return

    report(groups, edges, comps)
    if "--loose" in sys.argv:
        report_halos(groups, co_maindeck_counts(owners))
    if "--mermaid" in sys.argv:
        report_mermaid(groups, edges, comps)


if __name__ == "__main__":
    main()
