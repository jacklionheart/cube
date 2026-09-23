"""Green graveyard/landfall as OVERLAPPING membership (a deck can be both;
minimize the 'neither' bucket)."""
import team_search as ts
import packages as pk

def main():
    drafts, cube, decks, scry, owners = ts.load_owners()
    deck_sets = {}
    for c, sig in owners.items():
        for k, p in enumerate(sig):
            if p: deck_sets.setdefault((k, p), set()).add(c)
    rec = {kp: drafts[kp[0]].records.get(kp[1], (0, 0)) for kp in deck_sets}
    def ent(c): return scry.get(c.replace(" 2","",1)) or scry.get(c) or {}
    def text(c): return (ent(c).get("oracle_text") or "").lower()
    def is_green(c): return "G" in ent(c).get("colors", []) and not pk.is_land(c,scry)
    green = [c for c in owners if is_green(c)]
    GY = {c for c in green if any(k in text(c) for k in
          ["graveyard","escape","delve","descend","mill","from your graveyard"])}
    LF = {c for c in green if any(k in text(c) for k in
          ["landfall","land enters","lands you control","play an additional land"])}
    gdecks = [kp for kp in deck_sets if "G" in
              pk.combo_color([c for c in deck_sets[kp] if not pk.is_land(c,scry)], scry)]
    def wr(ds):
        w=l=0
        for kp in ds: a,b=rec[kp]; w+=a; l+=b
        return f"{len(ds)}d {w}-{l} {w/(w+l):.0%}" if w+l else f"{len(ds)}d -"
    for thr in (1, 2):
        gy=[kp for kp in gdecks if len(deck_sets[kp]&GY)>=thr]
        lf=[kp for kp in gdecks if len(deck_sets[kp]&LF)>=thr]
        both=[kp for kp in gdecks if kp in set(gy)&set(lf)]
        gonly=[kp for kp in gy if kp not in set(lf)]
        lonly=[kp for kp in lf if kp not in set(gy)]
        neither=[kp for kp in gdecks if kp not in set(gy)|set(lf)]
        print(f"\n=== threshold >= {thr} card(s) to be tagged (overlap allowed) ===")
        print(f"  graveyard (any):     {wr(gy)}")
        print(f"  landfall  (any):     {wr(lf)}")
        print(f"  both:                {wr(both)}")
        print(f"  graveyard-only:      {wr(gonly)}")
        print(f"  landfall-only:       {wr(lonly)}")
        print(f"  neither:             {wr(neither)}  <- want ~0")

if __name__ == "__main__":
    main()
