"""White card-level functional tagging (multi-tag): Removal / Aggro /
Makes Tokens / Draws Cards. R/T/D auto from oracle text; Aggro seeded from
a hand list. Shows per-card tags+WR and per-category avg card WR."""
import team_search as ts
import packages as pk

AGGRO_SEED = {
    "Mother of Runes","Luminarch Aspirant","Practiced Offense","Glimmer Lens",
    "Stoneforge Mystic","Staff of the Storyteller","Adeline, Resplendent Cathar",
    "Intrepid Adversary","Warden of the Inner Sky","Giver of Runes",
    "Voice of Victory","Phelia, Exuberant Shepherd","Witch Enchanter",
    "Novice Inspector","Thraben Inspector","Sanguine Evangelist",
}

def main():
    drafts, cube, decks, scry, owners = ts.load_owners()
    deck_sets = {}
    for c, sig in owners.items():
        for k, p in enumerate(sig):
            if p: deck_sets.setdefault((k, p), set()).add(c)
    rec = {kp: drafts[kp[0]].records.get(kp[1], (0, 0)) for kp in deck_sets}
    def ent(c): return scry.get(c.replace(" 2","",1)) or scry.get(c) or {}
    def text(c): return (ent(c).get("oracle_text") or "").lower()
    def is_white(c): return "W" in ent(c).get("colors", []) and not pk.is_land(c,scry)
    md = lambda c: sum(p is not None for p in owners[c])

    def tags(c):
        t=text(c); out=[]
        if any(k in t for k in ["destroy target","exile target","exile it",
            "exile up to","exile that","destroy all","exile all","damage to any",
            "put target","fight","tap target creature","-1/-1","onto their owner"]):
            out.append("Removal")
        if c in AGGRO_SEED: out.append("Aggro")
        if "token" in t and "create" in t: out.append("Tokens")
        if "draw a card" in t or "draw two" in t or "draw three" in t or \
           "draws a card" in t or "draw x" in t: out.append("Draws")
        return out

    white = sorted([c for c in owners if is_white(c) and md(c)>=4], key=lambda c:-md(c))
    def wr(c):
        w=l=0
        for kp in deck_sets:
            if c in deck_sets[kp]: a,b=rec[kp]; w+=a; l+=b
        return (w,l,w/(w+l) if w+l else None)

    cat = {"Removal":[], "Aggro":[], "Tokens":[], "Draws":[], "(untagged)":[]}
    print(f"{'card':<28}{'md':>3}  tags")
    for c in white:
        ts_=tags(c); w,l,r=wr(c)
        for t in (ts_ or ["(untagged)"]): cat[t].append(r)
        rs=f"{r:.0%}" if r is not None else "-"
        print(f"{c.split(',')[0]:<28}{md(c):>3}  {rs:>4}  {', '.join(ts_) or '-'}")
    print(f"\n{'category':<14}{'cards':>6}{'avg WR':>8}")
    for t,rs in cat.items():
        vals=[x for x in rs if x is not None]
        avg=f"{sum(vals)/len(vals):.1%}" if vals else "-"
        print(f"{t:<14}{len(rs):>6}{avg:>8}")

if __name__ == "__main__":
    main()
