"""Driver for team/itemset searches over roto maindecks (see mining.py).

Loads the s4 sources by default, builds the nonland maindeck-owner map,
and runs a search. Kept as a real module (not a heredoc) so the parallel
miner's worker processes can import it under spawn.

Examples:
    python3 team_search.py                     # all-but-1, size>=4, >=6/13
    python3 team_search.py --miss 0 --min-size 3 --support 6
    python3 team_search.py --miss 1 --min-size 4 --support 6 --no-restrict
"""

import argparse
import pathlib

import packages as pk
import refresh
from mining import Dataset
from roto_summary import parse_draft


HERE = pathlib.Path(__file__).resolve().parent


def load_owners(sources=None):
    sources = sources or refresh.SOURCES
    drafts, cube, seen = [], [], set()
    for n in sources:
        d, c = parse_draft(HERE / "sources" / f"{refresh.slugify(n)}.xlsx", n)
        drafts.append(d)
        for e in c:
            if e[0] not in seen:
                seen.add(e[0])
                cube.append(e)
    decks, _, _ = pk.load_decks(HERE / "decks.tsv", cube)
    scry = pk.load_scryfall()
    owners = pk.nonland_owners(pk.maindeck_owners(drafts, cube, decks), scry)
    return drafts, cube, decks, scry, owners


def team_universe(owners, support):
    """Cards that belong to at least one strict whole-set team (size>=2)
    at the given draft-support — a natural, fast candidate vocabulary for
    relaxed searches."""
    ds = Dataset.from_owners(owners, min_card_support=support)
    strict = ds.mine(min_support=support, min_size=2, miss=0)
    return {c for S, _ in strict for c in S}, strict


def search(owners, scry, support=6, min_size=4, miss=1, restrict=True,
           max_size=None, min_allconf=0.0):
    restrict_to = None
    if restrict:
        restrict_to, _ = team_universe(owners, support)
    ds = Dataset.from_owners(owners, restrict_to=restrict_to)
    groups = ds.mine(min_support=support, min_size=min_size, miss=miss,
                     max_size=max_size, min_allconf=min_allconf)
    return groups


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--support", type=int, default=6)
    ap.add_argument("--min-size", type=int, default=4)
    ap.add_argument("--miss", type=int, default=1)
    ap.add_argument("--max-size", type=int, default=None)
    ap.add_argument("--no-restrict", action="store_true")
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--allconf", type=float, default=0.0)
    ap.add_argument("--families", action="store_true",
                    help="merge card-sharing groups and report families")
    ap.add_argument("--swap-merge", action="store_true",
                    help="cluster same-size teams that differ by one card")
    a = ap.parse_args()

    import time
    _, _, _, scry, owners = load_owners()
    t = time.time()
    groups = search(owners, scry, support=a.support, min_size=a.min_size,
                    miss=a.miss, restrict=not a.no_restrict,
                    max_size=a.max_size, min_allconf=a.allconf)
    dt = time.time() - t
    from collections import Counter
    by_size = dict(sorted(Counter(len(S) for S, _ in groups).items()))
    print(f"all-but-{a.miss}, size>={a.min_size}, support>={a.support}/"
          f"{len(owners[next(iter(owners))]) if owners else 0}: "
          f"{len(groups)} maximal groups in {dt:.1f}s")
    print("by size:", by_size)

    if a.families:
        parent = {}

        def find(x):
            parent.setdefault(x, x)
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for S, _ in groups:
            it = iter(S)
            a0 = next(it)
            for c in it:
                parent[find(a0)] = find(c)
        from collections import defaultdict
        fam = defaultdict(set)
        for S, _ in groups:
            fam[find(next(iter(S)))] |= set(S)
        fams = sorted(fam.values(), key=lambda s: -len(s))
        print(f"card-connected families: {len(fams)} "
              f"(sizes {[len(f) for f in fams]})")
        for f in fams:
            print(f"  {pk.combo_color(f, scry)} {len(f)}: "
                  + ", ".join(sorted(f)))
        return

    if a.swap_merge:
        # cluster teams of equal size differing by exactly one card
        # (symmetric difference == 2); transitive -> core+flex clusters
        sets = [frozenset(S) for S, _ in groups]
        supp = {frozenset(S): sup for S, sup in groups}
        by_size = {}
        for s in sets:
            by_size.setdefault(len(s), []).append(s)
        parent = {s: s for s in sets}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for size, bucket in by_size.items():
            # index by (size-1)-subsets: two size-k sets differ by one card
            # iff they share a common (k-1)-subset
            idx = {}
            for s in bucket:
                for c in s:
                    key = s - {c}
                    idx.setdefault(key, []).append(s)
            for key, members in idx.items():
                for m in members[1:]:
                    parent[find(members[0])] = find(m)
        from collections import defaultdict
        clusters = defaultdict(list)
        for s in sets:
            clusters[find(s)].append(s)
        cl = sorted(clusters.values(),
                    key=lambda g: (-max(len(s) for s in g),
                                   -max(supp[s] for s in g)))
        print(f"{len(cl)} swap-merged clusters "
              f"(from {len(sets)} teams)")
        for members in cl[:a.limit or 20]:
            core = set.intersection(*[set(m) for m in members])
            union = set().union(*[set(m) for m in members])
            flex = union - core
            best = max(supp[m] for m in members)
            print(f"  [{best} {len(members)} teams, size {len(members[0])}, "
                  f"{pk.combo_color(union, scry)}] core: "
                  + ", ".join(sorted(core))
                  + (f"  +flex{{{', '.join(sorted(flex))}}}" if flex else ""))
        return

    for S, sup in groups[:a.limit]:
        print(f"  [{sup} {len(S)}c {pk.combo_color(S, scry)}] "
              + ", ".join(sorted(S)))


if __name__ == "__main__":
    main()
