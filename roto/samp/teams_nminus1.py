"""B corrected: (N-1)-subset load-bearing rule vs A (presence floor).

B: card x in size-N team S is load-bearing iff some (N-1)-subset of S
   that CONTAINS x has STRICT support >= t (all N-1 cards maindecked in
   one deck in >= t drafts). Keep S iff every card is load-bearing, i.e.
   the strictly-qualifying (N-1)-subsets cover all N cards. If only the
   core S\{x} qualifies, x is dead weight -> drop S.
"""
import team_search as ts
import packages as pk
from collections import defaultdict, deque

T = 8


def main():
    drafts, cube, decks, scry, owners = ts.load_owners()
    card_decks = defaultdict(set)
    by_draft = defaultdict(list)
    deck_sets = defaultdict(set)
    for c, sig in owners.items():
        for k, p in enumerate(sig):
            if p:
                card_decks[c].add((k, p))
                deck_sets[(k, p)].add(c)
    for (k, p), s in deck_sets.items():
        by_draft[k].append((p, s))

    def strict_support(U):
        U = list(U)
        common = set(card_decks[U[0]])
        for c in U[1:]:
            common &= card_decks[c]
            if not common:
                return 0
        return len({k for (k, p) in common})

    def A_worst(S):
        need = len(S) - 1
        Hd = {}
        for k, dks in by_draft.items():
            hs = [d for p, d in dks if len(d & S) >= need]
            if hs:
                Hd[k] = hs
        s = len(Hd)
        return s, min(sum(1 for hs in Hd.values() if any(c in d for d in hs))
                      for c in S)

    def B_covered(S, thr):
        """set of cards covered by some strictly-qualifying (N-1)-subset"""
        covered = set()
        for omit in S:
            sub = S - {omit}
            if strict_support(sub) >= thr:
                covered |= sub
        return covered

    base = ts.search(owners, scry, support=T, min_size=4, miss=1, restrict=True)
    G6 = [frozenset(S) for S, _ in base if len(S) == 6]

    def merge(sets):
        idx = defaultdict(list)
        for s in sets:
            for c in s:
                idx[s - frozenset({c})].append(s)
        adj = defaultdict(set)
        for grp in idx.values():
            for i in range(len(grp)):
                for j in range(i + 1, len(grp)):
                    adj[grp[i]].add(grp[j]); adj[grp[j]].add(grp[i])
        seen, comps = set(), []
        for s in sets:
            if s in seen:
                continue
            comp = {s}; dq = deque([s]); seen.add(s)
            while dq:
                x = dq.popleft()
                for y in adj[x]:
                    if y not in seen:
                        seen.add(y); comp.add(y); dq.append(y)
            comps.append(comp)
        return comps

    Aw = {S: A_worst(S) for S in G6}

    def report(name, keep):
        comps = [c for c in merge(keep) if len(set().union(*c)) >= 4]
        comps.sort(key=lambda c: -len(set().union(*c)))
        big = set().union(*comps[0]) if comps else set()
        print(f"\n{name}")
        print(f"   {len(keep):3d}/{len(G6)} teams survive | {len(comps)} merged"
              f" | biggest={len(big)} cards")
        if big:
            print("     " + ", ".join(sorted(big)))

    report("A: hole <= 1 (present >= support-1)",
           [S for S in G6 if Aw[S][1] >= Aw[S][0] - 1])
    report("A: hole <= 2 (present >= support-2)",
           [S for S in G6 if Aw[S][1] >= Aw[S][0] - 2])
    for thr in (8, 7, 6):
        report(f"B: every card in a strict (N-1)-subset >= {thr}",
               [S for S in G6 if B_covered(S, thr) == S])

    print("\n--- probe cards: does a strict 5-subset containing them clear t? ---")
    for card in ["Overlord of the Balemurk", "Cut Down", "Thoughtseize",
                 "Mayhem Devil"]:
        best = 0
        for S in G6:
            if card in S:
                for omit in S:
                    if omit != card:
                        best = max(best, strict_support(S - {omit}))
        print(f"  {card}: best strict (N-1)-subset containing it = {best}")


if __name__ == "__main__":
    main()
