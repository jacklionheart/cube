"""Blue staples hard-assigned to max-weight partner group; avg card WR per group."""
import team_search as ts
import packages as pk

STAPLE_MD = 6

def main():
    drafts, cube, decks, scry, owners = ts.load_owners()
    deck_sets = {}
    for c, sig in owners.items():
        for k, p in enumerate(sig):
            if p: deck_sets.setdefault((k, p), set()).add(c)
    rec = {kp: drafts[kp[0]].records.get(kp[1], (0, 0)) for kp in deck_sets}
    deck_colors = {kp: pk.combo_color([c for c in cs if not pk.is_land(c,scry)], scry)
                   for kp, cs in deck_sets.items()}
    def ent(c): return scry.get(c.replace(" 2","",1)) or scry.get(c) or {}
    def is_blue(c): return "U" in ent(c).get("colors", []) and not pk.is_land(c,scry)
    md = lambda c: sum(p is not None for p in owners[c])

    groups = {"W": [], "R": [], "B": [], "G": []}
    for c in owners:
        if not is_blue(c) or md(c) < STAPLE_MD: continue
        dks = [kp for kp in deck_sets if c in deck_sets[kp]]
        share = {col: sum(1 for kp in dks if col in deck_colors[kp]) / len(dks)
                 for col in "WBRG"}
        dom = max("WRBG", key=lambda k: share[k])  # ties -> W>R>B>G order
        w=l=0
        for kp in dks: a,b=rec[kp]; w+=a; l+=b
        wr = w/(w+l) if w+l else None
        groups[dom].append((c, md(c), wr))

    labels={"W":"UW control","R":"UR prowess","B":"UB flash","G":"UG ramp"}
    print(f"blue staples (md>={STAPLE_MD}) by dominant partner:\n")
    for col in "WRBG":
        cards=groups[col]
        wrs=[wr for _,_,wr in cards if wr is not None]
        avg=sum(wrs)/len(wrs) if wrs else 0
        bar="#"*round(avg*50)
        print(f"U{col} {labels[col]:<12} {len(cards):>2} cards  avgWR {avg:.1%}  {bar}")
        for c,m,wr in sorted(cards,key=lambda x:-(x[2] or 0)):
            print(f"      {c.split(',')[0]:<24} md{m:<3} {wr:.0%}")
        print()

if __name__ == "__main__":
    main()
