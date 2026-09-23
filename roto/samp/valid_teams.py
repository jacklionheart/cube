"""User's confirmed rule, all sizes:
  base teams = all-but-1 maximal teams at support >= t (size >= 4)
  VALID iff every card x in S lies in some (N-1)-subset of S whose WHOLE
  set is strictly maindecked together in >= t drafts.
Report survivors by size, at strict-subset thresholds 8/7/6 (base t=8)."""
import team_search as ts
import packages as pk
from collections import defaultdict
from itertools import combinations

def main():
    drafts, cube, decks, scry, owners = ts.load_owners()
    card_decks = defaultdict(set)
    for c, sig in owners.items():
        for k, p in enumerate(sig):
            if p:
                card_decks[c].add((k, p))

    def strict(U):
        U = list(U)
        common = set(card_decks[U[0]])
        for c in U[1:]:
            common &= card_decks[c]
            if not common:
                return 0
        return len({k for (k, p) in common})

    base = ts.search(owners, scry, support=8, min_size=4, miss=1, restrict=True)
    print(f"all-but-1 maximal base teams (size>=4, >=8/13): {len(base)}")
    by_size = defaultdict(int)
    for S, _ in base:
        by_size[len(S)] += 1
    print("  by size:", dict(sorted(by_size.items())))

    def valid(S, thr):
        N = len(S)
        covered = set()
        for sub in combinations(S, N - 1):
            if strict(sub) >= thr:
                covered |= set(sub)
        return covered == set(S)

    for thr in (8, 7, 6, 5):
        surv = [frozenset(S) for S, _ in base if valid(S, thr)]
        bs = defaultdict(int)
        for S in surv:
            bs[len(S)] += 1
        print(f"\nstrict (N-1)-subset threshold >= {thr}: "
              f"{len(surv)} valid teams  by size {dict(sorted(bs.items()))}")
        for S in sorted(surv, key=lambda s: (-len(s), sorted(s)))[:12]:
            print(f"   [{len(S)}c {pk.combo_color(S, scry)}] "
                  + ", ".join(x.split(',')[0] for x in sorted(S)))

if __name__ == "__main__":
    main()
