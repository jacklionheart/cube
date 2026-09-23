"""Jaccard-component cores + core/penumbra table.
core = connected component (Jaccard>=THETA); deck set = decks running >=TAG
core cards; table lists every nonland card those decks play, core flagged,
sorted by inclusion, with each card's WR over the deck set."""
import team_search as ts
import packages as pk
from collections import defaultdict

THETA = 0.6
TAG = 4

def main():
    drafts, cube, decks, scry, owners = ts.load_owners()
    card_decks = defaultdict(set)
    for c, sig in owners.items():
        for k, p in enumerate(sig):
            if p: card_decks[c].add((k, p))
    rec = {}
    for s in card_decks.values():
        for kp in s: rec[kp] = drafts[kp[0]].records.get(kp[1], (0,0))
    deck_cards = defaultdict(set)
    for c, s in card_decks.items():
        if pk.is_land(c, scry): continue
        for kp in s: deck_cards[kp].add(c)
    cards = [c for c in card_decks if len(card_decks[c])>=4 and not pk.is_land(c,scry)]

    def jac(a,b):
        A,B=card_decks[a],card_decks[b]; u=len(A|B)
        return len(A&B)/u if u else 0
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
        return w,l,(w/(w+l) if w+l else None)

    def table(name, core):
        deckset=[kp for kp in deck_cards if len(deck_cards[kp]&core)>=TAG]
        w,l,r=wr(deckset)
        print(f"\n### {name}  [{pk.combo_color(core,scry)}]  core={len(core)}  "
              f"deckset={len(deckset)}  {w}-{l} {r:.0%}")
        rows=[]
        allcards=set().union(*[deck_cards[kp] for kp in deckset]) if deckset else set()
        for c in allcards:
            withc=[kp for kp in deckset if c in deck_cards[kp]]
            incl=len(withc)/len(deckset)
            cw,cl,cr=wr(withc)
            rows.append((c, c in core, incl, cr, cw, cl))
        rows.sort(key=lambda t:(-t[1], -t[2]))
        print(f"  {'card':<26}{'core':>5}{'incl':>6}{'WR':>6}  W-L")
        for c,core_f,incl,cr,cw,cl in rows:
            if not core_f and incl<0.30: continue
            crs=f"{cr:.0%}" if cr is not None else "-"
            print(f"  {c.split(',')[0]:<26}{'✓' if core_f else '':>5}{incl:>6.0%}{crs:>6}  {cw}-{cl}")

    for tag,seed in [("Sacrifice","Yawgmoth"),("Discard","Cool but Rude")]:
        core=next((s for s in cores if any(seed in c for c in s)), None)
        if core: table(tag, core)

if __name__ == "__main__":
    main()
