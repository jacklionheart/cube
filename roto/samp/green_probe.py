"""Does green split into graveyard vs landfall? Classify green cards by
oracle text, measure each green deck's lean, compare WR."""
import team_search as ts
import packages as pk

def main():
    drafts, cube, decks, scry, owners = ts.load_owners()
    deck_sets = {}
    for c, sig in owners.items():
        for k, p in enumerate(sig):
            if p: deck_sets.setdefault((k, p), set()).add(c)
    rec = {kp: drafts[kp[0]].records.get(kp[1], (0, 0)) for kp in deck_sets}

    def ent(c):
        return scry.get(c.replace(" 2","",1)) or scry.get(c) or {}
    def text(c):
        return (ent(c).get("oracle_text") or "").lower()
    def is_green(c):
        return "G" in ent(c).get("colors", [])

    green = [c for c in owners if is_green(c) and not pk.is_land(c, scry)]
    GY = [c for c in green if any(k in text(c) for k in
          ["graveyard","escape","delve","descend","mill","from your graveyard"])]
    LF = [c for c in green if "landfall" in text(c) or
          "land enters" in text(c) or "lands you control" in text(c) or
          "play an additional land" in text(c)]
    md = lambda c: sum(p is not None for p in owners[c])
    print("GRAVEYARD-flavored green (md>=5):",
          ", ".join(f"{c.split(',')[0]}({md(c)})" for c in sorted(GY,key=md,reverse=True) if md(c)>=5))
    print("\nLANDFALL-flavored green (md>=4):",
          ", ".join(f"{c.split(',')[0]}({md(c)})" for c in sorted(LF,key=md,reverse=True) if md(c)>=4))

    green_decks = [kp for kp in deck_sets if "G" in
                   pk.combo_color([c for c in deck_sets[kp] if not pk.is_land(c,scry)], scry)]
    gyset, lfset = set(GY), set(LF)
    lean = {"graveyard":[], "landfall":[], "tie/neither":[]}
    for kp in green_decks:
        g = len(deck_sets[kp] & gyset); f = len(deck_sets[kp] & lfset)
        lean["graveyard" if g>f else "landfall" if f>g else "tie/neither"].append(kp)
    print(f"\n{len(green_decks)} green decks:")
    for k,decks_ in lean.items():
        w=l=0
        for kp in decks_: a,b=rec[kp]; w+=a; l+=b
        r=f"{w/(w+l):.0%}" if w+l else "-"
        print(f"  {k:<14} {len(decks_):>2} decks  {w}-{l}  {r}")

if __name__ == "__main__":
    main()
