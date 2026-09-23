"""Preview: Discard/Sac/Green cluster tables with DECK-LEVEL tagging.
cluster cards = strict-6 cross-size merge union; depth = strict backbone
depth (support 6) within the cluster; a deck is TAGGED with a cluster if it
maindecks >= T of the cluster's cards. Per-card WR = tagged decks that also
run the card."""
import team_search as ts
from mining import Dataset
from collections import defaultdict, deque

def main():
    drafts, cube, decks, scry, owners = ts.load_owners()
    deck_sets = defaultdict(set)
    for c, sig in owners.items():
        for k, p in enumerate(sig):
            if p: deck_sets[(k, p)].add(c)
    rec = {}
    for (k, p) in deck_sets:
        rec[(k, p)] = drafts[k].records.get(p, (0, 0))

    ds = Dataset.from_owners(owners)
    G = [frozenset(S) for S,_ in ds.mine(min_support=6, min_size=4, miss=0, maximal=True)]
    parent={s:s for s in G}
    def find(x):
        while parent[x]!=x: parent[x]=parent[parent[x]]; x=parent[x]
        return x
    for i in range(len(G)):
        for j in range(i+1,len(G)):
            if len(G[i]&G[j])>=min(len(G[i]),len(G[j]))-1: parent[find(G[i])]=find(G[j])
    clusters=defaultdict(list)
    for s in G: clusters[find(s)].append(s)
    unions = [set().union(*m) for m in clusters.values()]

    def pick(names):  # cluster whose union contains all these seed cards
        for u in unions:
            if all(any(n in c for c in u) for n in names): return u
        return set()
    named = {
        "Discard": pick(["Cool but Rude", "Faithless Looting", "Inti"]),
        "Sac":     pick(["Yawgmoth", "Mayhem Devil", "Priest of Forgotten Gods"]),
        "Green":   pick(["Springheart Nantuko", "Malevolent Rumble"]),
    }

    def depth(card, pool):
        d = Dataset.from_owners(owners, restrict_to=list(pool))
        best = 0
        for S,_ in d.mine(min_support=6, min_size=1, miss=0, maximal=False):
            if card in S and len(S) > best: best = len(S)
        return best

    def wr(decklist):
        w=l=0
        for kp in decklist: dw,dl=rec[kp]; w+=dw; l+=dl
        return w,l

    for name, pool in named.items():
        pool = set(pool)
        tagged_at = {T: [kp for kp,cs in deck_sets.items() if len(cs & pool) >= T]
                     for T in (3,4,5)}
        print(f"\n{'='*66}\n{name}  ({len(pool)} cards)")
        print("  decks tagged at T>= : " + "  ".join(
            f"T{T}:{len(tagged_at[T])}d {wr(tagged_at[T])[0]}-{wr(tagged_at[T])[1]}"
            for T in (3,4,5)))
        T = 3 if len(pool) <= 4 else 4
        tagged = tagged_at[T]
        print(f"  --- per-card table (tag threshold T={T}) ---")
        print(f"  {'card':<24}{'depth':>6}{'md/13':>7}{'w/card':>8}{'W-L':>9}{'WR':>7}")
        dep = {c: depth(c, pool) for c in pool}
        for c in sorted(pool, key=lambda c:-dep[c]):
            withc = [kp for kp in tagged if c in deck_sets[kp]]
            w,l = wr(withc)
            md = sum(1 for sig in [owners[c]] for p in sig if p)
            r = f"{w/(w+l):.0%}" if w+l else "-"
            print(f"  {c.split(',')[0]:<24}{dep[c]:>6}{md:>7}{len(withc):>8}"
                  f"{f'{w}-{l}':>9}{r:>7}")

if __name__ == "__main__":
    main()
