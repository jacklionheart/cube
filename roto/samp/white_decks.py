"""Base white decks: distribution of category card-counts, and WR by how
much a deck leans into each category (split at median count)."""
import team_search as ts
import packages as pk
import statistics as st

AGGRO_SEED = {
    "Mother of Runes","Luminarch Aspirant","Practiced Offense","Glimmer Lens",
    "Stoneforge Mystic","Staff of the Storyteller","Adeline, Resplendent Cathar",
    "Intrepid Adversary","Warden of the Inner Sky","Giver of Runes",
    "Voice of Victory","Phelia, Exuberant Shepherd","Witch Enchanter",
    "Novice Inspector","Thraben Inspector","Sanguine Evangelist",
}
CATS = ["Removal","Aggro","Tokens","Draws"]

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
    def tags(c):
        t=text(c); out=set()
        if any(k in t for k in ["destroy target","exile target","exile it",
            "exile up to","exile that","destroy all","exile all","damage to any",
            "put target","fight","tap target creature","-1/-1"]):
            out.add("Removal")
        if c in AGGRO_SEED: out.add("Aggro")
        if "token" in t and "create" in t: out.add("Tokens")
        if any(k in t for k in ["draw a card","draw two","draw three","draws a card","draw x"]):
            out.add("Draws")
        return out
    card_tags = {c: tags(c) for c in owners if is_white(c)}

    wdecks = [kp for kp in deck_sets if "W" in
              pk.combo_color([c for c in deck_sets[kp] if not pk.is_land(c,scry)], scry)]
    counts = {cat: {} for cat in CATS}
    for kp in wdecks:
        for cat in CATS:
            counts[cat][kp] = sum(1 for c in deck_sets[kp] if cat in card_tags.get(c,()))
    def wr(ds):
        w=l=0
        for kp in ds: a,b=rec[kp]; w+=a; l+=b
        return (w,l,w/(w+l) if w+l else None)
    print(f"{len(wdecks)} base white decks\n")
    print(f"{'category':<10}{'avg/deck':>9}{'range':>8}   split at median:  {'few (WR)':>16}{'many (WR)':>16}")
    for cat in CATS:
        vals=[counts[cat][kp] for kp in wdecks]
        med=st.median(vals)
        few=[kp for kp in wdecks if counts[cat][kp] < med] or [kp for kp in wdecks if counts[cat][kp]<=med]
        many=[kp for kp in wdecks if counts[cat][kp] > med]
        fw=wr(few); mw=wr(many)
        fs=f"{len(few)}d {fw[2]:.0%}" if fw[2] is not None else "-"
        ms=f"{len(many)}d {mw[2]:.0%}" if mw[2] is not None else "-"
        print(f"{cat:<10}{sum(vals)/len(vals):>9.1f}{f'{min(vals)}-{max(vals)}':>8}   median={med:<4}   {fs:>16}{ms:>16}")

if __name__ == "__main__":
    main()
