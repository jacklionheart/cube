"""Package analysis over the roto drafts' maindecks.

A *package* is a maximal set of cards maindecked in the same deck in every
draft (identical deck-owner signature). Edges connect packages whose
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
from collections import defaultdict
from itertools import combinations

from roto_summary import MAIN_ZONES, load_decks, parse_draft

HERE = pathlib.Path(__file__).parent


def load():
    """Parse the three source drafts and all submitted decks. Pick names
    are canonicalized against the cube list (draft grids are hand-typed),
    mirroring roto_summary.main."""
    drafts, cube = [], None
    for i in range(1, 4):
        d, c = parse_draft(HERE / "sources" / f"draft{i}.xlsx", f"Draft {i}")
        drafts.append(d)
        cube = cube or c
    canonical = {c.casefold(): c for c, _, _ in cube}
    for d in drafts:
        for card in list(d.picks):
            fixed = canonical.get(card.casefold())
            if fixed and fixed != card:
                d.picks[fixed] = d.picks.pop(card)
    decks, _, _ = load_decks(HERE / "decks.tsv", cube)
    return drafts, cube, decks


def maindeck_owners(drafts, cube, decks):
    """card -> tuple of per-draft deck owner, None where the card was not
    maindecked in that draft (not picked, deck unknown, or sideboarded)."""
    owners = {}
    for card, _, _ in cube:
        row = []
        for d in drafts:
            p = d.picks.get(card)
            deck = decks.get((d.name, p.player)) if p else None
            row.append(p.player if deck and deck.get(card) in MAIN_ZONES else None)
        owners[card] = tuple(row)
    return owners


def signature_groups(owners):
    """Maximal packages: cards sharing one full (no-None) owner signature.
    Returns [(signature, cards)] with >= 2 cards, largest first."""
    sigs = defaultdict(list)
    for card, sig in owners.items():
        if None not in sig:
            sigs[sig].append(card)
    groups = [(sig, cards) for sig, cards in sigs.items() if len(cards) >= 2]
    groups.sort(key=lambda g: -len(g[1]))  # stable: ties keep cube order
    return groups


def package_edges(groups, agreement=2):
    """Pairs of packages whose signatures agree in exactly `agreement`
    drafts. Returns [(i, j, [draft numbers agreed])]."""
    edges = []
    for i in range(len(groups)):
        for j in range(i + 1, len(groups)):
            shared = [k + 1 for k, (a, b) in
                      enumerate(zip(groups[i][0], groups[j][0])) if a == b]
            if len(shared) == agreement:
                edges.append((i, j, shared))
    return edges


def components(groups, edges):
    """Connected components over package_edges, most cards first."""
    parent = list(range(len(groups)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i, j, _ in edges:
        parent[find(i)] = find(j)
    comps = defaultdict(list)
    for i in range(len(groups)):
        comps[find(i)].append(i)
    return sorted(comps.values(), key=lambda c: -sum(len(groups[i][1]) for i in c))


def co_maindeck_counts(owners):
    """(cardA, cardB) -> number of drafts in which both sat in the same
    maindeck. Keys are sorted pairs."""
    counts = defaultdict(int)
    n_drafts = len(next(iter(owners.values()))) if owners else 0
    for k in range(n_drafts):
        by_deck = defaultdict(list)
        for card, sig in owners.items():
            if sig[k] is not None:
                by_deck[sig[k]].append(card)
        for cards in by_deck.values():
            for a, b in combinations(sorted(cards), 2):
                counts[(a, b)] += 1
    return counts


def halos(groups, pair_counts, min_shared=2):
    """package index -> cards outside it that co-maindecked with every
    member in >= min_shared drafts."""
    def together(a, b):
        return pair_counts.get((min(a, b), max(a, b)), 0)

    in_pairs = {c for pair in pair_counts for c in pair}
    return {
        gi: sorted(x for x in in_pairs if x not in cards
                   and all(together(x, m) >= min_shared for m in cards))
        for gi, (_, cards) in enumerate(groups)
    }


def loose_components(pair_counts, min_shared=2):
    """Connected components over pairs co-maindecked >= min_shared times.
    Not transitive like signatures — chains fuse into large blobs."""
    pairs = {p: n for p, n in pair_counts.items() if n >= min_shared}
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in pairs:
        parent[find(a)] = find(b)
    comps = defaultdict(set)
    for a, b in pairs:
        comps[find(a)].update((a, b))
    return pairs, sorted(comps.values(), key=len, reverse=True)


def never_drafted(drafts, cube):
    """Cards no one picked in any draft."""
    return sorted(c for c, _, _ in cube
                  if not any(c in d.picks for d in drafts))


def never_maindecked(drafts, cube, decks, min_taken=1):
    """Cards drafted in >= min_taken drafts but maindecked in none."""
    owners = maindeck_owners(drafts, cube, decks)
    return sorted(
        c for c, _, _ in cube
        if sum(c in d.picks for d in drafts) >= min_taken
        and not any(owners[c]))


def late_first_pick(drafts, cube, threshold=350):
    """Drafted cards whose earliest overall pick across drafts is >= threshold."""
    out = []
    for c, _, _ in cube:
        picks = [d.picks[c].overall for d in drafts if c in d.picks]
        if picks and min(picks) >= threshold:
            out.append(c)
    return sorted(out)


WUBRG = "WUBRG"
BASIC_COLORS = [("Plains", "W"), ("Island", "U"), ("Swamp", "B"),
                ("Mountain", "R"), ("Forest", "G")]


def load_scryfall():
    import json
    return json.loads((HERE / "scryfall.json").read_text())


def card_colors(name, scry):
    """Systematic color assignment: the card's mana-cost colors, plus —
    for lands only — the colors of mana it produces, unless it produces
    all five (rainbow utility lands like Edgewall Inn or Spire of
    Industry count as colorless, same as fetches). So Path to the World
    Tree is G (not its WUBRG identity), Everything Pizza and Shattered
    Landscape are colorless, Temple Garden is GW. Produced mana on
    nonlands is ignored (else every Treasure-maker reads 5c)."""
    info = scry[name]
    colors = set(info.get("colors", []))
    if "Land" in info["type_line"]:
        produced = set(info.get("produced_mana", [])) & set(WUBRG)
        if len(produced) < 5:
            colors |= produced
    return colors


def colors_str(cards, scry):
    """WUBRG-ordered union of card_colors over a card set; 'C' if none."""
    u = set()
    for c in cards:
        u |= card_colors(c, scry)
    return "".join(c for c in WUBRG if c in u) or "C"


def deck_sets(owners):
    """(draft index, player) -> set of cards maindecked in that deck."""
    by_deck = defaultdict(set)
    for card, sig in owners.items():
        for k, p in enumerate(sig):
            if p:
                by_deck[(k, p)].add(card)
    return by_deck


def pair_packages(owners, min_core=3):
    """Relaxed packages with k2=1: maximal card sets fully maindecked in
    one deck in 2 of the 3 drafts — i.e. cross-draft deck-pair
    intersections, subset-dominated cores removed. Adding k1=1 on top
    (allow one missing card per deck) admits any single extra card from
    either deck, so the (1,1) maximum size is just core+2; that bound is
    reported rather than enumerating arbitrary fillers.
    Returns [{'core': set, 'decks': ((k, player), (k, player))}]."""
    by_deck = deck_sets(owners)
    results = []
    for a, b in combinations(sorted(by_deck), 2):
        if a[0] == b[0]:
            continue
        core = by_deck[a] & by_deck[b]
        if len(core) >= min_core:
            results.append({"core": core, "decks": (a, b)})
    results.sort(key=lambda r: -len(r["core"]))
    kept = []
    for r in results:
        if not any(r["core"] <= k["core"] for k in kept):
            kept.append(r)
    return kept


def flex_packages(groups, owners):
    """Relaxed packages with k1=1, k2=0: every card set built from a
    strict package's own deck triple where each draft's deck may miss at
    most one card. All-three-deck cores are exactly the signature groups,
    so each entry is a strict package plus per-draft flex buckets: cards
    maindecked in the other two decks of the SAME triple but absent from
    this draft's deck. A maximal (1,0) set = core + one card from each
    nonempty bucket.
    Returns [{'sig', 'cards', 'flex': [bucket per draft]}]."""
    by_deck = deck_sets(owners)
    out = []
    for sig, cards in groups:
        decks = [by_deck[(k, p)] for k, p in enumerate(sig)]
        flex = []
        for i in range(len(decks)):
            others = set.intersection(*(d for j, d in enumerate(decks) if j != i))
            flex.append(sorted(others - decks[i]))
        out.append({"sig": sig, "cards": cards, "flex": flex})
    return out


def null_model(drafts, cube, decks, iters=2000, seed=0):
    """Permutation test: keep every player's picks, replace each maindeck
    with a uniform random same-size subset of that player's picks, and
    recount strict packages. Returns (observed, samples) where each entry
    is (n_packages, total_cards_in_packages, largest_package)."""
    observed_owners = maindeck_owners(drafts, cube, decks)

    def stats(owners):
        groups = signature_groups(owners)
        sizes = [len(cards) for _, cards in groups]
        return (len(sizes), sum(sizes), max(sizes, default=0))

    picks_by_deck = []  # (draft index, player, [cards picked], n maindecked)
    for k, d in enumerate(drafts):
        by_player = defaultdict(list)
        for card, p in d.picks.items():
            by_player[p.player].append(card)
        for player, cards in by_player.items():
            n_main = sum(1 for c in cards if observed_owners[c][k] == player)
            if n_main:
                picks_by_deck.append((k, player, sorted(cards), n_main))

    rng = random.Random(seed)
    n_drafts = len(drafts)
    samples = []
    for _ in range(iters):
        owners = {card: [None] * n_drafts for card, _, _ in cube}
        for k, player, cards, n_main in picks_by_deck:
            for c in rng.sample(cards, n_main):
                owners[c][k] = player
        samples.append(stats({c: tuple(o) for c, o in owners.items()}))
    return stats(observed_owners), samples


def report(groups, edges, comps):
    scry = load_scryfall()
    print(f"{len(groups)} packages, {len(edges)} edges, {len(comps)} components\n")
    for n, comp in enumerate(comps):
        cards_total = sum(len(groups[i][1]) for i in comp)
        print(f"== Component {chr(65 + n)}: {len(comp)} packages, {cards_total} cards")
        for i in comp:
            sig, cards = groups[i]
            print(f"   P{i + 1} [{len(cards)}] {colors_str(cards, scry)} "
                  f"({' / '.join(sig)})")
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
    names = ["packages (size>=2)", "cards in packages", "largest package"]
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
