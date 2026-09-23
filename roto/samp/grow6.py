"""Same-size one-card-difference merge on STRICT support-6 maximal teams.
WR pooled over the union of hosting decks (decks containing the whole team)
across all constituent teams."""
import team_search as ts
import packages as pk
from collections import defaultdict, deque
from mining import Dataset

def main():
    drafts, cube, decks, scry, owners = ts.load_owners()
    card_decks = defaultdict(set)
    for c, sig in owners.items():
        for k, p in enumerate(sig):
            if p:
                card_decks[c].add((k, p))

    def hosts(S):  # decks (k,p) containing the WHOLE team
        S = list(S); common = set(card_decks[S[0]])
        for c in S[1:]: common &= card_decks[c]
        return common

    ds = Dataset.from_owners(owners)
    teams = ds.mine(min_support=6, min_size=4, miss=0, maximal=True)
    G = [frozenset(S) for S, _ in teams]
    print(f"strict support-6 maximal teams (size>=4): {len(G)} "
          f"(by size {dict(sorted({s: sum(len(x)==s for x in G) for s in set(len(x) for x in G)}.items()))})")

    def merge(sets):
        idx = defaultdict(list)
        for s in sets:
            for c in s: idx[s - frozenset({c})].append(s)
        adj = defaultdict(set)
        for grp in idx.values():
            for i in range(len(grp)):
                for j in range(i+1, len(grp)):
                    adj[grp[i]].add(grp[j]); adj[grp[j]].add(grp[i])
        seen, comps = set(), []
        for s in sets:
            if s in seen: continue
            comp={s}; dq=deque([s]); seen.add(s)
            while dq:
                x=dq.popleft()
                for y in adj[x]:
                    if y not in seen: seen.add(y); comp.add(y); dq.append(y)
            comps.append(comp)
        return comps

    # merge WITHIN each size bucket
    by_size = defaultdict(list)
    for s in G: by_size[len(s)].append(s)
    merged = []
    for size, bucket in sorted(by_size.items(), reverse=True):
        for comp in merge(bucket):
            union = set().union(*comp)
            qd = set()
            for S in comp: qd |= hosts(S)
            w=l=0
            for k,p in qd:
                dw,dl = drafts[k].records.get(p,(0,0)); w+=dw; l+=dl
            merged.append((size, len(comp), union, qd, w, l))
    merged.sort(key=lambda m: (-len(m[2]), -m[1]))
    print(f"\nmerged teams (same-size, 1-card-diff union):")
    for size,n,union,qd,w,l in merged:
        if len(union) < 5: continue
        r = f"{w/(w+l):.1%}" if w+l else "-"
        print(f"\n [size {size} x{n} teams -> {len(union)}c | {pk.combo_color(union,scry)}"
              f" | {len(qd)} decks {w}-{l} {r}]")
        print("   " + ", ".join(x.split(',')[0] for x in sorted(union)))

if __name__ == "__main__":
    main()
