"""A (presence floor) vs B (load-bearing strict-subset) on size-6 @>=8 teams."""
import team_search as ts
import packages as pk
from collections import defaultdict, deque

T = 8  # threshold


def main():
    drafts, cube, decks, scry, owners = ts.load_owners()
    # per-card deck membership (k,p)
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

    def strict_pair(x, y):
        return len({k for (k, p) in card_decks[x] & card_decks[y]})

    def A_worst(S):  # (support, worst per-card presence in team-hosting drafts)
        need = len(S) - 1
        Hd = {}
        for k, decks in by_draft.items():
            hs = [d for p, d in decks if len(d & S) >= need]
            if hs:
                Hd[k] = hs
        s = len(Hd)
        return s, min(sum(1 for hs in Hd.values() if any(c in d for d in hs))
                      for c in S)

    def B_worst(S):  # worst card's best strict-pair partner within S
        return min(max(strict_pair(x, y) for y in S if y != x) for x in S)

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
    Bw = {S: B_worst(S) for S in G6}

    policies = [
        ("A: present in >= support-1", lambda S: Aw[S][1] >= Aw[S][0] - 1),
        ("A: present in >= support-2", lambda S: Aw[S][1] >= Aw[S][0] - 2),
        ("B: every card strict-pairs >=8 with a teammate", lambda S: Bw[S] >= 8),
        ("B: every card strict-pairs >=7 with a teammate", lambda S: Bw[S] >= 7),
        ("B: every card strict-pairs >=6 with a teammate", lambda S: Bw[S] >= 6),
    ]
    for name, ok in policies:
        keep = [S for S in G6 if ok(S)]
        comps = [c for c in merge(keep) if len(set().union(*c)) >= 4]
        comps.sort(key=lambda c: -len(set().union(*c)))
        big = set().union(*comps[0]) if comps else set()
        print(f"\n{name}")
        print(f"   {len(keep):3d}/{len(G6)} teams survive | {len(comps)} merged | "
              f"biggest={len(big)} cards ({pk.combo_color(big, scry) if big else '-'})")
        if big:
            print("     " + ", ".join(sorted(big)))

    print("\n--- mechanism for the surprising cards (in their example team) ---")
    probes = {
        "Overlord of the Balemurk":
            frozenset({"Bloodghast", "Bone Shards", "Forsaken Miner",
                       "Overlord of the Balemurk", "Sephiroth, Fabled SOLDIER",
                       "Yawgmoth, Thran Physician"}),
        "Cut Down":
            frozenset({"Bone Shards", "Cut Down", "Forsaken Miner",
                       "Sephiroth, Fabled SOLDIER", "The Meathook Massacre",
                       "Warren Soultrader"}),
        "Thoughtseize":
            frozenset({"Forsaken Miner", "Sephiroth, Fabled SOLDIER",
                       "The Meathook Massacre", "Thoughtseize",
                       "Warren Soultrader", "Yawgmoth, Thran Physician"}),
    }
    for card, S in probes.items():
        s, _ = A_worst(S)
        need = len(S) - 1
        Hd = {k: [d for p, d in by_draft[k] if len(d & S) >= need]
              for k in by_draft}
        Hd = {k: v for k, v in Hd.items() if v}
        Apres = sum(1 for hs in Hd.values() if any(card in d for d in hs))
        best_y = max((y for y in S if y != card),
                     key=lambda y: strict_pair(card, y))
        print(f"  {card}: A-presence {Apres}/{s} in team-hosting drafts | "
              f"B best strict pair = {strict_pair(card, best_y)} (with "
              f"{best_y.split(',')[0]})")


if __name__ == "__main__":
    main()
