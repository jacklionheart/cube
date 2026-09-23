"""Show whether transitively merging same-size, one-card-apart groups drifts."""
import team_search as ts, packages as pk
from collections import defaultdict, deque

_,_,_,scry,owners = ts.load_owners()
SIZE, SUP = 6, 8
groups = ts.search(owners, scry, support=SUP, min_size=4, miss=1, restrict=True)
G = [frozenset(S) for S,_ in groups if len(S)==SIZE]

# edges: same size, differ by exactly one card (share SIZE-1 cards)
adj = defaultdict(set); idx = defaultdict(list)
for s in G:
    for c in s: idx[s-frozenset({c})].append(s)
for grp in idx.values():
    for i in range(len(grp)):
        for j in range(i+1,len(grp)):
            adj[grp[i]].add(grp[j]); adj[grp[j]].add(grp[i])

seen=set(); comps=[]
for s in G:
    if s in seen: continue
    comp=set([s]); dq=deque([s]); seen.add(s)
    while dq:
        x=dq.popleft()
        for y in adj[x]:
            if y not in seen: seen.add(y); comp.add(y); dq.append(y)
    comps.append(comp)
big=max(comps,key=len)
print(f"size-{SIZE} groups @>={SUP}/13: {len(G)} groups, {len(comps)} components; "
      f"biggest merges {len(big)} groups into one blob of {len(set().union(*big))} cards\n")

# pick the two groups in the blob that share the FEWEST cards, show the chain
big=list(big)
a=b=None; lo=99
for i in range(len(big)):
    for j in range(i+1,len(big)):
        o=len(big[i]&big[j])
        if o<lo: lo=o; a,b=big[i],big[j]
prev={a:None}; dq=deque([a])
while dq:
    x=dq.popleft()
    if x==b: break
    for y in adj[x]:
        if y not in prev: prev[y]=x; dq.append(y)
path=[]; x=b
while x is not None: path.append(x); x=prev[x]
path.reverse()
print(f"the two most-different groups in that blob share only {lo} cards:")
print(f"  A = {{{', '.join(sorted(a))}}}")
print(f"  B = {{{', '.join(sorted(b))}}}")
print(f"\nyet a chain of {len(path)-1} single-card swaps links them (so the merge fuses them):")
for i,s in enumerate(path):
    t=""
    if i>0:
        t=f"   swap out {sorted(path[i-1]-s)[0]}, in {sorted(s-path[i-1])[0]}"
    print(f"  {{{', '.join(sorted(s))}}}{t}")
