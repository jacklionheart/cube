"""Tolerant clustering: all-but-1 base + strict-backbone validation + cross-size merge.
Goal (1): does adding tolerance let HIGHER support recover the strict-6 clusters?
  base    = all-but-1 (miss=1) maximal teams at support S, size>=4
  validate= keep team iff every card sits in a strict (N-1)-subset with
            strict support >= B  (kills hole-riders like Overlord)
  merge   = cross-size single-linkage (overlap >= min(|A|,|B|)-1)
"""
import team_search as ts
import packages as pk
from mining import Dataset
from collections import defaultdict
from itertools import combinations

def main():
    drafts, cube, decks, scry, owners = ts.load_owners()
    card_decks = defaultdict(set)
    for c, sig in owners.items():
        for k, p in enumerate(sig):
            if p: card_decks[c].add((k, p))
    def strict(U):
        U=list(U); common=set(card_decks[U[0]])
        for c in U[1:]:
            common &= card_decks[c]
            if not common: return 0
        return len({k for (k,p) in common})
    def hosts_allbut1(S):  # decks with >= |S|-1 of S
        need=len(S)-1; out=set()
        cd={c:card_decks[c] for c in S}
        alld=set().union(*cd.values())
        for kp in alld:
            if sum(kp in cd[c] for c in S) >= need: out.add(kp)
        return out

    def pipeline(S_sup, B):
        base = ts.search(owners, scry, support=S_sup, min_size=4, miss=1, restrict=True)
        G=[frozenset(s) for s,_ in base]
        def ok(T):
            cov=set()
            for sub in combinations(T, len(T)-1):
                if strict(sub) >= B: cov|=set(sub)
            return cov==set(T)
        V=[T for T in G if ok(T)]
        parent={s:s for s in V}
        def find(x):
            while parent[x]!=x: parent[x]=parent[parent[x]]; x=parent[x]
            return x
        for i in range(len(V)):
            for j in range(i+1,len(V)):
                if len(V[i]&V[j])>=min(len(V[i]),len(V[j]))-1: parent[find(V[i])]=find(V[j])
        cl=defaultdict(list)
        for s in V: cl[find(s)].append(s)
        out=[]
        for members in cl.values():
            u=set().union(*members)
            if len(u)<5: continue
            qd=set()
            for T in members: qd|=hosts_allbut1(T)
            w=l=0
            for k,p in qd:
                dw,dl=drafts[k].records.get(p,(0,0)); w+=dw; l+=dl
            out.append((u,len(members),qd,w,l))
        out.sort(key=lambda r:-len(r[0]))
        return len(G),len(V),out

    for S_sup in (6,7,8):
        for B in (4,5):
            nbase,nvalid,cl=pipeline(S_sup,B)
            print(f"\n=== base all-but-1 support>={S_sup}, backbone strict>={B} "
                  f"| {nbase} base -> {nvalid} valid -> {len(cl)} clusters(>=5c) ===")
            for u,n,qd,w,l in cl:
                r=f"{w/(w+l):.0%}" if w+l else "-"
                over = "  *** HAS OVERLORD" if "Overlord of the Balemurk" in u else ""
                print(f"  [{n}t {len(u)}c {pk.combo_color(u,scry)} {len(qd)}d {r}] "
                      + ", ".join(x.split(',')[0] for x in sorted(u)) + over)

if __name__ == "__main__":
    main()
