"""Sensitivity of the deck-tag threshold. For each Jaccard-0.6 core, show
the distribution of core-cards-per-deck, the tag count + WR at T=3/4/5, and
the boundary decks (those sitting at 3, 4, or 5 core cards)."""
import team_search as ts
import packages as pk
from collections import defaultdict, Counter

THETA = 0.6

def main():
    drafts, cube, decks, scry, owners = ts.load_owners()
    card_decks = defaultdict(set)
    for c, sig in owners.items():
        for k, p in enumerate(sig):
            if p: card_decks[c].add((k, p))
    rec = {}
    for s in card_decks.values():
        for kp in s: rec[kp]=drafts[kp[0]].records.get(kp[1],(0,0))
    deck_cards = defaultdict(set)
    for c, s in card_decks.items():
        if pk.is_land(c,scry): continue
        for kp in s: deck_cards[kp].add(c)
    cards=[c for c in card_decks if len(card_decks[c])>=4 and not pk.is_land(c,scry)]
    def jac(a,b):
        A,B=card_decks[a],card_decks[b]; u=len(A|B); return len(A&B)/u if u else 0
    parent={c:c for c in cards}
    def find(x):
        while parent[x]!=x: parent[x]=parent[parent[x]]; x=parent[x]
        return x
    for i in range(len(cards)):
        for j in range(i+1,len(cards)):
            if jac(cards[i],cards[j])>=THETA: parent[find(cards[i])]=find(cards[j])
    comp=defaultdict(set)
    for c in cards: comp[find(c)].add(c)
    cores=[s for s in comp.values() if len(s)>=4]

    def wr(dl):
        w=l=0
        for kp in dl: a,b=rec[kp]; w+=a; l+=b
        return w,l,(w/(w+l) if w+l else 0)

    def analyze(name, core):
        cnt={kp:len(deck_cards[kp]&core) for kp in deck_cards}
        dist=Counter(cnt.values())
        print(f"\n### {name}  core={len(core)}  ({pk.combo_color(core,scry)})")
        print("  core-cards-per-deck distribution (n decks):")
        line="   ".join(f"{k}:{dist[k]}" for k in sorted(dist) if k>0)
        print("   "+line)
        for T in (3,4,5):
            tagged=[kp for kp in deck_cards if cnt[kp]>=T]
            w,l,r=wr(tagged)
            print(f"  T>={T}: {len(tagged)} decks  {w}-{l}  {r:.0%}")
        print("  boundary decks (3-5 core cards):")
        for kp in sorted(deck_cards, key=lambda k:-cnt[k]):
            if 3<=cnt[kp]<=5:
                col=pk.combo_color([c for c in deck_cards[kp] if not pk.is_land(c,scry)],scry)
                dw,dl=rec[kp]
                print(f"     {cnt[kp]} core | {col:<5} | {drafts[kp[0]].name[:14]:<14} {kp[1][:14]:<14} {dw}-{dl}")

    for tag,seed in [("Sacrifice","Yawgmoth"),("Discard","Cool but Rude")]:
        core=next((s for s in cores if any(seed in c for c in s)),None)
        if core: analyze(tag,core)

if __name__ == "__main__":
    main()
