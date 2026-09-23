import team_search as ts
from collections import defaultdict

def main():
    drafts, cube, decks, scry, owners = ts.load_owners()
    card_decks = defaultdict(set)
    by_draft = defaultdict(list)
    deck_sets = defaultdict(set)
    for c, sig in owners.items():
        for k, p in enumerate(sig):
            if p:
                card_decks[c].add((k, p)); deck_sets[(k, p)].add(c)
    for (k, p), s in deck_sets.items():
        by_draft[k].append(s)

    def strict(U):
        U = list(U); common = set(card_decks[U[0]])
        for c in U[1:]: common &= card_decks[c]
        return len({k for (k, p) in common})

    def allbut1(U):  # >=t drafts with a deck missing <=1 of U
        need = len(U) - 1
        return sum(1 for k, ds in by_draft.items()
                   if any(len(d & U) >= need for d in ds))

    S = frozenset({"Bloodghast", "Bone Shards", "Forsaken Miner",
                   "Overlord of the Balemurk", "Sephiroth, Fabled SOLDIER",
                   "Yawgmoth, Thran Physician"})
    print(f"Team S (size 6): all-but-1 support = {allbut1(S)}, "
          f"strict = {strict(S)}\n")
    print(f"{'omitted card':<26} {'5-subset all-but-1':>18} {'5-subset strict':>16}")
    for omit in sorted(S):
        sub = S - {omit}
        tag = "  <- core (omits Overlord)" if omit.startswith("Overlord") else ""
        print(f"{omit.split(',')[0]:<26} {allbut1(sub):>18} {strict(sub):>16}{tag}")
    print("\n# of the 6 five-subsets clearing 8:")
    print("   under all-but-1:",
          sum(1 for o in S if allbut1(S - {o}) >= 8))
    print("   under strict   :",
          sum(1 for o in S if strict(S - {o}) >= 8))

if __name__ == "__main__":
    main()
