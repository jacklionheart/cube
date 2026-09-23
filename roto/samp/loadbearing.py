import team_search as ts
from collections import defaultdict, deque
drafts,cube,decks,scry,owners = ts.load_owners()
deck_sets = defaultdict(set)
for c,sig in owners.items():
    for k,p in enumerate(sig):
        if p: deck_sets[(k,p)].add(c)
by_draft = defaultdict(list)
for (k,p),s in deck_sets.items(): by_draft[k].append(s)

def hosting(S):
    need=len(S)-1
    H={}
    for k,ds in by_draft.items():
        hs=[d for d in ds if len(d&S)>=need]
        if hs: H[k]=hs
    return H
def min_present(S):
    H=hosting(S); s=len(H)
    worst=s; who=None
    for c in S:
        pc=sum(1 for k,hs in H.items() if any(c in d for d in hs))
        if pc<worst: worst=pc; who=c
    return s, worst, who

groups = ts.search(owners, scry, support=8, min_size=4, miss=1, restrict=True)
G6 = [frozenset(S) for S,_ in groups if len(S)==6]

def component(sets):
    idx=defaultdict(list)
    for s in sets:
        for c in s: idx[s-frozenset({c})].append(s)
    adj=defaultdict(set)
    for grp in idx.values():
        for i in range(len(grp)):
            for j in range(i+1,len(grp)): adj[grp[i]].add(grp[j]); adj[grp[j]].add(grp[i])
    seen=set(); comps=[]
    for s in sets:
        if s in seen: continue
        comp={s}; dq=deque([s]); seen.add(s)
        while dq:
            x=dq.popleft()
            for y in adj[x]:
                if y not in seen: seen.add(y); comp.add(y); dq.append(y)
        comps.append(comp)
    return max(comps,key=len) if comps else set()

for miss in (1,2):
    survivors=[S for S in G6 if min_present(S)[1] >= len(hosting(S))-miss]
    big=component(survivors)
    union=set().union(*big) if big else set()
    print(f"\n### per-card floor: hole allowed in <= {miss} of a team's supporting drafts")
    print(f"  size-6 teams surviving: {len(survivors)}/{len(G6)}")
    print(f"  biggest merged component: {len(big)} teams, union = {len(union)} cards")
    print("  union:", ", ".join(sorted(union)))
