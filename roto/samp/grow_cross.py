"""Cross-size transitive merge on strict support-6 maximal teams.
Merge two teams if they overlap in >= min(|A|,|B|)-1 cards (one is within
one card of sitting inside the other). Single-linkage -> archetype clusters."""
import team_search as ts
import packages as pk
from collections import defaultdict, deque
from mining import Dataset

def main():
    drafts, cube, decks, scry, owners = ts.load_owners()
    card_decks = defaultdict(set)
    for c, sig in owners.items():
        for k, p in enumerate(sig):
            if p: card_decks[c].add((k, p))
    def hosts(S):
        S=list(S); common=set(card_decks[S[0]])
        for c in S[1:]: common &= card_decks[c]
        return common

    ds = Dataset.from_owners(owners)
    G = [frozenset(S) for S,_ in ds.mine(min_support=6, min_size=4, miss=0, maximal=True)]

    parent = {s: s for s in G}
    def find(x):
        while parent[x]!=x: parent[x]=parent[parent[x]]; x=parent[x]
        return x
    for i in range(len(G)):
        for j in range(i+1, len(G)):
            A,B = G[i],G[j]
            if len(A & B) >= min(len(A),len(B))-1:
                parent[find(A)] = find(B)
    clusters = defaultdict(list)
    for s in G: clusters[find(s)].append(s)

    rows=[]
    for members in clusters.values():
        union=set().union(*members)
        qd=set()
        for S in members: qd |= hosts(S)
        w=l=0
        for k,p in qd:
            dw,dl=drafts[k].records.get(p,(0,0)); w+=dw; l+=dl
        rows.append((union, len(members), qd, w, l))
    rows.sort(key=lambda r:-len(r[0]))
    print(f"{len(G)} strict-6 teams -> {len(rows)} cross-size clusters\n")
    for union,n,qd,w,l in rows:
        r=f"{w/(w+l):.1%}" if w+l else "-"
        print(f"[{n} teams -> {len(union)}c | {pk.combo_color(union,scry)} | "
              f"{len(qd)} decks {w}-{l} {r}]")
        print("   " + ", ".join(x.split(',')[0] for x in sorted(union)))

if __name__ == "__main__":
    main()
