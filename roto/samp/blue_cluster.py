"""Soft-color blue cards by co-occurrence. For each U card, the share of
its decks that also play each partner color (W/B/R/G) -> a weight vector,
not a binary label. Reveals UW/UR/UB/UG leans and the 'good in 2 of 3'
overlap cards."""
import team_search as ts
import packages as pk

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

    blue = [c for c in owners if is_blue(c) and md(c) >= 4]
    rows = []
    for c in blue:
        dks = [kp for kp in deck_sets if c in deck_sets[kp]]
        n = len(dks)
        share = {}
        for col in "WBRG":
            share[col] = sum(1 for kp in dks if col in deck_colors[kp]) / n if n else 0
        w=l=0
        for kp in dks: a,b=rec[kp]; w+=a; l+=b
        wr = w/(w+l) if w+l else None
        rows.append((c, n, share, wr))
    # sort by dominant partner then share
    order = {"W":0,"R":1,"B":2,"G":3}
    def dom(s): return max("WRBG", key=lambda k: s[k])
    rows.sort(key=lambda r: (order[dom(r[2])], -max(r[2].values())))
    print(f"{'card':<26}{'md':>3} {'UW':>5}{'UR':>5}{'UB':>5}{'UG':>5}  {'lean':<7}{'WR':>5}")
    for c, n, s, wr in rows:
        lean = "".join(k for k in "WRBG" if s[k] >= 0.5) or dom(s)
        wrs = f"{wr:.0%}" if wr is not None else "-"
        print(f"{c.split(',')[0]:<26}{n:>3} {s['W']:>5.0%}{s['R']:>5.0%}"
              f"{s['B']:>5.0%}{s['G']:>5.0%}  U{lean:<6}{wrs:>5}")

if __name__ == "__main__":
    main()
