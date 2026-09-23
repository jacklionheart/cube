"""Compare simple 'package generator' systems. Goal: produce Sac + Discard
(+ reasonable G/W) and no noise. Each system -> connected components of a
card graph; report components with >=4 cards."""
import team_search as ts
import packages as pk
from collections import defaultdict
from mining import Dataset

def main():
    drafts, cube, decks, scry, owners = ts.load_owners()
    card_decks = defaultdict(set)
    for c, sig in owners.items():
        for k, p in enumerate(sig):
            if p: card_decks[c].add((k, p))
    # restrict to cards maindecked in >=4 decks (drop chaff)
    cards = [c for c in owners if len(card_decks[c]) >= 4 and not pk.is_land(c,scry)]
    D = {c: set(card_decks[c]) for c in cards}  # deck-level (k,p) presence

    def comps(link):
        parent = {c: c for c in cards}
        def find(x):
            while parent[x]!=x: parent[x]=parent[parent[x]]; x=parent[x]
            return x
        for i in range(len(cards)):
            for j in range(i+1, len(cards)):
                a,b = cards[i], cards[j]
                if link(a,b): parent[find(a)]=find(b)
        cl = defaultdict(set)
        for c in cards: cl[find(c)].add(c)
        return sorted((s for s in cl.values() if len(s)>=4), key=lambda s:-len(s))

    def show(name, components):
        print(f"\n## {name}: {len(components)} components (>=4 cards)")
        for s in components[:8]:
            cards_s = sorted(s)
            head = ", ".join(x.split(',')[0] for x in cards_s[:10])
            more = f" +{len(s)-10}" if len(s)>10 else ""
            print(f"  [{pk.combo_color(s,scry)} {len(s)}] {head}{more}")

    # co-occurrence counts (draft-level)
    def co(a,b): return len(D[a]&D[b])
    def jac(a,b):
        u=len(D[a]|D[b]); return (len(D[a]&D[b])/u) if u else 0
    def allconf(a,b):
        m=max(len(D[a]),len(D[b])); return (len(D[a]&D[b])/m) if m else 0

    # System 0: current (strict maximal size>=4 @6 + single-linkage merge)
    ds = Dataset.from_owners(owners)
    G=[frozenset(s) for s,_ in ds.mine(min_support=6,min_size=4,miss=0,maximal=True,workers=1)]
    par={s:s for s in G}
    def f2(x):
        while par[x]!=x: par[x]=par[par[x]]; x=par[x]
        return x
    for i in range(len(G)):
        for j in range(i+1,len(G)):
            if len(G[i]&G[j])>=min(len(G[i]),len(G[j]))-1: par[f2(G[i])]=f2(G[j])
    cur=defaultdict(set)
    for s in G: cur[f2(s)]|=set(s)
    show("SYSTEM 0  strict-maximal(>=4@6)+merge (current)",
         sorted((s for s in cur.values() if len(s)>=4), key=lambda s:-len(s)))

    for T in (6,7):
        show(f"co-occurrence >= {T} decks", comps(lambda a,b: co(a,b)>=T))
    for th in (0.5,0.6):
        show(f"Jaccard >= {th}", comps(lambda a,b: jac(a,b)>=th))
    for th in (0.6,0.7):
        show(f"all-confidence >= {th}", comps(lambda a,b: allconf(a,b)>=th))

if __name__ == "__main__":
    main()
