"""Empirical comparison of team-formation policies over s4 size-6 @>=8 teams.

Baseline: all-but-1 maximal teams, same-size transitive union merge.
Policies vary a per-card 'load-bearing' floor: a card may be the hole
(absent from the hosting deck) in at most `m` of a team's supporting
drafts. m=None disables the floor (pure union blob).

WR for a merged team is pooled over the union of hosting decks across all
constituent teams (a deck qualifies if it hosted any constituent), each
deck counted once.
"""
import team_search as ts
import packages as pk
from collections import defaultdict, deque


def build(owners, drafts):
    deck_sets = defaultdict(set)
    for c, sig in owners.items():
        for k, p in enumerate(sig):
            if p:
                deck_sets[(k, p)].add(c)
    by_draft = defaultdict(list)
    for (k, p), s in deck_sets.items():
        by_draft[k].append((p, s))
    return deck_sets, by_draft


def hosting_decks(S, by_draft):
    """(k,p) decks that host S under all-but-1 (overlap >= |S|-1)."""
    need = len(S) - 1
    out = set()
    for k, decks in by_draft.items():
        for p, d in decks:
            if len(d & S) >= need:
                out.add((k, p))
    return out


def min_present(S, by_draft):
    """support (#drafts hosting S) and the worst per-card presence:
    #hosting-drafts where some hosting deck actually contains the card."""
    need = len(S) - 1
    Hd = defaultdict(list)  # draft -> hosting deck sets
    for k, decks in by_draft.items():
        hs = [d for p, d in decks if len(d & S) >= need]
        if hs:
            Hd[k] = hs
    s = len(Hd)
    worst = s
    for c in S:
        pc = sum(1 for hs in Hd.values() if any(c in d for d in hs))
        worst = min(worst, pc)
    return s, worst


def merge_same_size(sets):
    """transitive union of same-size sets differing by one card -> components"""
    idx = defaultdict(list)
    for s in sets:
        for c in s:
            idx[s - frozenset({c})].append(s)
    adj = defaultdict(set)
    for grp in idx.values():
        for i in range(len(grp)):
            for j in range(i + 1, len(grp)):
                adj[grp[i]].add(grp[j])
                adj[grp[j]].add(grp[i])
    seen, comps = set(), []
    for s in sets:
        if s in seen:
            continue
        comp = {s}
        dq = deque([s])
        seen.add(s)
        while dq:
            x = dq.popleft()
            for y in adj[x]:
                if y not in seen:
                    seen.add(y)
                    comp.add(y)
                    dq.append(y)
        comps.append(comp)
    return comps


def wr(decks, drafts):
    w = l = 0
    for k, p in decks:
        dw, dl = drafts[k].records.get(p, (0, 0))
        w, l = w + dw, l + dl
    return w, l


def main():
    drafts, cube, decks, scry, owners = ts.load_owners()
    _, by_draft = build(owners, drafts)
    base = ts.search(owners, scry, support=8, min_size=4, miss=1, restrict=True)
    G6 = [frozenset(S) for S, _ in base if len(S) == 6]
    pres = {S: min_present(S, by_draft) for S in G6}

    for m in (None, 2, 1, 0):
        if m is None:
            keep = G6
            tag = "none (pure union blob)"
        else:
            keep = [S for S in G6 if pres[S][1] >= pres[S][0] - m]
            tag = f"card may be the hole in <= {m} supporting drafts"
        comps = merge_same_size(keep)
        comps = [c for c in comps if len(set().union(*c)) >= 4]
        comps.sort(key=lambda c: -len(set().union(*c)))
        print(f"\n{'='*70}\nPOLICY: {tag}")
        print(f"  {len(keep)}/{len(G6)} size-6 teams survive -> "
              f"{len(comps)} merged teams (size>=4)")
        for comp in comps[:6]:
            union = set().union(*comp)
            qdecks = set()
            for S in comp:
                qdecks |= hosting_decks(S, by_draft)
            w, l = wr(qdecks, drafts)
            r = f"{w/(w+l):.1%}" if w + l else "-"
            print(f"  [{len(comp)} teams -> {len(union)} cards | "
                  f"{pk.combo_color(union, scry)} | {len(qdecks)} decks "
                  f"{w}-{l} {r}]")
            print("     " + ", ".join(sorted(union)))


if __name__ == "__main__":
    main()
