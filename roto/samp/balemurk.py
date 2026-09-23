import team_search as ts, packages as pk
from collections import defaultdict, deque
drafts,cube,decks,scry,owners = ts.load_owners()
# per-card: which drafts maindeck it, and per-deck sets
card_drafts = {c: {k for k,p in enumerate(sig) if p} for c,sig in owners.items()}
deck_sets = defaultdict(set)
for c,sig in owners.items():
    for k,p in enumerate(sig):
        if p: deck_sets[(k,p)].add(c)
by_draft = defaultdict(list)
for (k,p),s in deck_sets.items(): by_draft[k].append(s)

groups = ts.search(owners, scry, support=8, min_size=4, miss=1, restrict=True)
G6 = [frozenset(S) for S,_ in groups if len(S)==6]
# big component
idx=defaultdict(list)
for s in G6:
    for c in s: idx[s-frozenset({c})].append(s)
adj=defaultdict(set)
for grp in idx.values():
    for i in range(len(grp)):
        for j in range(i+1,len(grp)): adj[grp[i]].add(grp[j]); adj[grp[j]].add(grp[i])
seen=set(); comps=[]
for s in G6:
    if s in seen: continue
    comp={s}; dq=deque([s]); seen.add(s)
    while dq:
        x=dq.popleft()
        for y in adj[x]:
            if y not in seen: seen.add(y); comp.add(y); dq.append(y)
    comps.append(comp)
big=max(comps,key=len)

def support_drafts(S):
    need=len(S)-1
    return {k for k,ds in by_draft.items() if any(len(d&S)>=need for d in ds)}

for card in ["Overlord of the Balemurk","Cut Down","Thoughtseize"]:
    print(f"\n=== {card} ===")
    print(f"  maindecked in {len(card_drafts.get(card,set()))}/13 drafts overall")
    holders=[S for S in big if card in S]
    print(f"  in {len(holders)} of the component's size-6 teams")
    if holders:
        S=holders[0]
        sd=support_drafts(S)
        present=sum(1 for k in sd if any(card in d and len(d&S)>=len(S)-1 for d in by_draft[k]))
        print(f"  e.g. team {{{', '.join(sorted(S))}}}")
        print(f"       supported in {len(sd)} drafts; {card} actually present in {present} of them"
              f"  (the hole in {len(sd)-present})")
