import team_search as ts
from mining import Dataset
from collections import defaultdict, deque

def main():
    drafts, cube, decks, scry, owners = ts.load_owners()
    card_decks = defaultdict(set)
    for c, sig in owners.items():
        for k, p in enumerate(sig):
            if p: card_decks[c].add((k, p))
    ds = Dataset.from_owners(owners)
    G = [frozenset(S) for S,_ in ds.mine(min_support=6, min_size=4, miss=0, maximal=True)]
    # find sac cluster via cross-size merge
    parent={s:s for s in G}
    def find(x):
        while parent[x]!=x: parent[x]=parent[parent[x]]; x=parent[x]
        return x
    for i in range(len(G)):
        for j in range(i+1,len(G)):
            if len(G[i]&G[j])>=min(len(G[i]),len(G[j]))-1: parent[find(G[i])]=find(G[j])
    clusters=defaultdict(list)
    for s in G: clusters[find(s)].append(s)
    sac=max(clusters.values(), key=lambda m:len(set().union(*m)))
    union=set().union(*sac)
    print(f"sac cluster union ({len(union)}c): "
          + ", ".join(x.split(',')[0] for x in sorted(union)))
    print(f"\n{len(sac)} constituent maximal teams (size>=5 shown), "
          f"'-' = card absent from THIS team, [+X] = card THIS team has that the size-7 lacks:")
    size7 = max(sac, key=len)
    for S in sorted(sac, key=lambda s:-len(s)):
        if len(S) < 5: continue
        missing = [c.split(',')[0] for c in sorted(union - S)]
        extra = sorted(S - size7)
        tag = "  [carries: " + ", ".join(x.split(',')[0] for x in extra) + "]" if extra else "  [subset of size-7]"
        print(f"  {len(S)}c  -{{{', '.join(missing)}}}{tag}")
    # verify no subset relationships
    subset_pairs = sum(1 for A in sac for B in sac if A<B)
    print(f"\nsubset pairs among constituents: {subset_pairs} (0 confirms all maximal)")

if __name__ == "__main__":
    main()
