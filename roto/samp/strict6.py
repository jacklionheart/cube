import team_search as ts
import packages as pk
from collections import defaultdict
from mining import Dataset

def main():
    drafts, cube, decks, scry, owners = ts.load_owners()
    ds = Dataset.from_owners(owners)
    for sup in (6, 7, 8):
        teams = ds.mine(min_support=sup, min_size=2, miss=0, maximal=True)
        bs = defaultdict(int)
        for S, _ in teams:
            bs[len(S)] += 1
        biggest = max((len(S) for S, _ in teams), default=0)
        print(f"\nstrict (miss=0) maximal teams, support >= {sup}: "
              f"{len(teams)} teams, biggest {biggest}c, by size {dict(sorted(bs.items()))}")
        # show the largest sac-colored teams
        big = sorted((t for t in teams if len(t[0]) >= biggest-1),
                     key=lambda t: -len(t[0]))
        for S, s in big[:8]:
            print(f"   [{s}x {len(S)}c {pk.combo_color(S, scry)}] "
                  + ", ".join(x.split(',')[0] for x in sorted(S)))

if __name__ == "__main__":
    main()
