"""Preview 5 blog groups: Sacrifice, Discard (archetype card-packages),
Green, White, Blue (colors). Table per group: card, backbone depth (support
6, within the group's card pool), inclusion rate among tagged decks, WR."""
import team_search as ts
import packages as pk
from mining import Dataset
from collections import defaultdict

def main():
    drafts, cube, decks, scry, owners = ts.load_owners()
    deck_sets = defaultdict(set)
    for c, sig in owners.items():
        for k, p in enumerate(sig):
            if p: deck_sets[(k, p)].add(c)
    rec = {kp: drafts[kp[0]].records.get(kp[1], (0, 0)) for kp in deck_sets}
    md = {c: sum(p is not None for p in owners[c]) for c in owners}

    # archetype clusters via strict-6 cross-size merge
    ds = Dataset.from_owners(owners)
    G = [frozenset(S) for S,_ in ds.mine(min_support=6, min_size=4, miss=0, maximal=True)]
    parent={s:s for s in G}
    def find(x):
        while parent[x]!=x: parent[x]=parent[parent[x]]; x=parent[x]
        return x
    for i in range(len(G)):
        for j in range(i+1,len(G)):
            if len(G[i]&G[j])>=min(len(G[i]),len(G[j]))-1: parent[find(G[i])]=find(G[j])
    cl=defaultdict(list)
    for s in G: cl[find(s)].append(s)
    unions=[set().union(*m) for m in cl.values()]
    def pick(seeds):
        for u in unions:
            if all(any(s in c for c in u) for s in seeds): return set(u)
        return set()
    sac = pick(["Yawgmoth","Mayhem Devil","Priest of Forgotten Gods"])
    dis = pick(["Cool but Rude","Faithless Looting","Inti"])

    def deck_color(kp):
        return pk.combo_color([c for c in deck_sets[kp] if not pk.is_land(c,scry)], scry)
    def color_pool(letter):
        cards=[c for c in owners if not pk.is_land(c,scry) and md[c]>=5
               and letter in (scry.get(c.replace(" 2","",1)) or scry.get(c) or {}).get("colors",[])]
        return set(cards)

    groups = [
        ("Sacrifice", sac, [kp for kp,cs in deck_sets.items() if len(cs&sac)>=4]),
        ("Discard",   dis, [kp for kp,cs in deck_sets.items() if len(cs&dis)>=4]),
        ("Green", color_pool("G"), [kp for kp in deck_sets if "G" in deck_color(kp)]),
        ("White", color_pool("W"), [kp for kp in deck_sets if "W" in deck_color(kp)]),
        ("Blue",  color_pool("U"), [kp for kp in deck_sets if "U" in deck_color(kp)]),
    ]
    def wr(dl):
        w=l=0
        for kp in dl: a,b=rec[kp]; w+=a; l+=b
        return w,l
    for name,pool,tagged in groups:
        pool=set(pool)
        dpool=Dataset.from_owners(owners, restrict_to=list(pool))
        depth={c:0 for c in pool}
        for S,_ in dpool.mine(min_support=6,min_size=1,miss=0,maximal=False):
            for c in S:
                if len(S)>depth[c]: depth[c]=len(S)
        w,l=wr(tagged)
        r=f"{w/(w+l):.0%}" if w+l else "-"
        print(f"\n{'='*64}\n{name}: {len(pool)} cards, {len(tagged)} tagged decks, {w}-{l} {r}")
        print(f"  {'card':<24}{'depth':>6}{'incl':>7}{'WR':>7}")
        rows=sorted(pool,key=lambda c:(-depth[c],-len([1 for kp in tagged if c in deck_sets[kp]])))
        for c in rows[:16]:
            withc=[kp for kp in tagged if c in deck_sets[kp]]
            incl=len(withc)/len(tagged) if tagged else 0
            ww,ll=wr(withc)
            wrr=f"{ww/(ww+ll):.0%}" if ww+ll else "-"
            print(f"  {c.split(',')[0]:<24}{depth[c]:>6}{incl:>6.0%}{wrr:>7}")
        if len(pool)>16: print(f"  ... +{len(pool)-16} more")

if __name__ == "__main__":
    main()
