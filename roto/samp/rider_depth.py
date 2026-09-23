"""Per-card strict backbone depth in the BR sac pool (no merging).
For each card: the largest STRICT itemset (all maindecked together) within
the pool that contains it, at support >= B. Riders have shallow backbones."""
import team_search as ts
from mining import Dataset

POOL = ["Bitterblossom","Bloodghast","Bone Shards","Chthonian Nightmare",
        "Forsaken Miner","Jadar, Ghoulcaller of Nephalia","Lord Skitter, Sewer King",
        "Marionette Apprentice","Mayhem Devil","Priest of Forgotten Gods",
        "Sephiroth, Fabled SOLDIER","The Meathook Massacre","Warren Soultrader",
        "Yawgmoth, Thran Physician",
        # candidate riders:
        "Overlord of the Balemurk","Cut Down","Thoughtseize"]

def main():
    drafts, cube, decks, scry, owners = ts.load_owners()
    pool = [c for c in POOL if c in owners]
    missing = [c for c in POOL if c not in owners]
    if missing:
        print("not in owners:", missing)
    ds = Dataset.from_owners(owners, restrict_to=pool)
    supp = {c: sum(p is not None for p in owners[c]) for c in pool}
    for B in (6, 5):
        teams = ds.mine(min_support=B, min_size=1, miss=0, maximal=False)
        depth = {c: 0 for c in pool}
        example = {c: None for c in pool}
        for S, s in teams:
            for c in S:
                if len(S) > depth[c]:
                    depth[c] = len(S); example[c] = S
        print(f"\n=== strict backbone depth at support >= {B} "
              f"(deepest all-together itemset in the pool) ===")
        for c in sorted(pool, key=lambda c: (-depth[c], -supp[c])):
            ex = example[c]
            exs = ", ".join(x.split(',')[0] for x in sorted(ex)) if ex else "-"
            print(f"  {depth[c]:>2}c  {c.split(',')[0]:<22} (maindecked {supp[c]:>2}/13)  "
                  f"e.g. {{{exs}}}")

if __name__ == "__main__":
    main()
