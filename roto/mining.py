"""Frequent-itemset mining over roto maindecks — reusable and parallel.

A *transaction* is one deck's card set, tagged with the draft it came
from. Support is counted at the DRAFT level: a draft contributes 1 if any
of its decks satisfies the membership predicate. Two predicates, both
anti-monotone under adding a card (so depth-first search prunes):

  strict      a deck must contain the whole set S.
  all-but-m   a deck must contain >= |S| - m of S (the `miss` budget;
              the missing cards may differ from deck to deck).

Cards are bit-indexed, so a deck is an int mask and overlap is one
popcount (int.bit_count, Py3.10+). The top-level DFS roots (each keyed
by the set's smallest card) are farmed across processes.

Typical use:
    ds = Dataset.from_owners(nonland_owners, restrict_to=team_cards)
    groups = ds.mine(min_support=6, min_size=4, miss=1)   # -> [(frozenset, support)]

Design keeps the single-machine case fast without hyperscale machinery;
the Dataset is a plain, picklable bundle of int lists so workers share it
via a pool initializer rather than re-pickling per task.
"""

from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass


@dataclass
class Dataset:
    n_drafts: int
    draft_decks: list          # per draft: list of deck bitmasks (vocab bits)
    vocab: list                # bit index -> card name
    card_support: list         # bit index -> # drafts the card is maindecked

    # ---- construction ------------------------------------------------
    @classmethod
    def from_owners(cls, owners, restrict_to=None, min_card_support=1):
        """owners: card -> tuple(per-draft player-or-None) for the cards to
        consider (already land-filtered by the caller, e.g. via
        packages.nonland_owners). restrict_to: optional iterable of card
        names to limit the vocabulary. min_card_support: drop cards
        maindecked in fewer than this many drafts."""
        n = len(next(iter(owners.values()))) if owners else 0
        allow = set(restrict_to) if restrict_to is not None else None
        counts = {c: sum(p is not None for p in sig)
                  for c, sig in owners.items()}
        vocab = sorted(
            (c for c, sig in owners.items()
             if counts[c] >= min_card_support
             and (allow is None or c in allow)),
            key=lambda c: (-counts[c], c))
        bit = {c: i for i, c in enumerate(vocab)}
        decks = {}
        for c in vocab:
            b = 1 << bit[c]
            for k, p in enumerate(owners[c]):
                if p is not None:
                    key = (k, p)
                    decks[key] = decks.get(key, 0) | b
        draft_decks = [[] for _ in range(n)]
        for (k, _p), m in decks.items():
            draft_decks[k].append(m)
        return cls(n, draft_decks, vocab, [counts[c] for c in vocab])

    # ---- mining ------------------------------------------------------
    def mine(self, min_support, min_size=1, miss=0, max_size=None,
             min_allconf=0.0, maximal=True, workers=None):
        """Return [(frozenset(cards), support)] for every set that clears
        `min_support` at the given `miss` budget. `min_allconf` (0..1)
        additionally requires all-confidence = support(S) / max_i
        support({i}) >= threshold — null-invariant, prunes sets that are
        frequent only because a staple co-occurs; it's anti-monotone, so
        it's pushed into the search. maximal=True keeps only sets not
        contained in a larger qualifying set."""
        V = len(self.vocab)
        if V == 0:
            return []
        args = (self.draft_decks, V, min_support, miss, min_size, max_size,
                self.card_support, min_allconf)
        roots = list(range(V))
        if workers is None:
            workers = max(1, (os.cpu_count() or 2) - 1)
        # spawn-based pools need the entry module importable; fall back to
        # sequential when run from a heredoc / -c / REPL.
        import __main__
        mf = getattr(__main__, "__file__", None)
        if mf is None or not os.path.exists(mf):
            workers = 1
        workers = min(workers, len(roots)) or 1

        results = []
        if workers == 1:
            _init(*args)
            for r in roots:
                results.extend(_dfs_root(r))
        else:
            with ProcessPoolExecutor(max_workers=workers,
                                     initializer=_init,
                                     initargs=args) as ex:
                for chunk in ex.map(_dfs_root, roots, chunksize=1):
                    results.extend(chunk)

        out = [(frozenset(self.vocab[i] for i in _bits(m)), s)
               for m, s in results]
        if maximal:
            out = _maximal(out)
        out.sort(key=lambda t: (-len(t[0]), -t[1], sorted(t[0])))
        return out


# ---- worker globals + kernels (module-level so they pickle) ----------
_W = {}


def _init(draft_decks, V, min_support, miss, min_size, max_size,
          card_support, min_allconf):
    _W.update(dd=draft_decks, V=V, ms=min_support, miss=miss,
              minsz=min_size, maxsz=max_size, cs=card_support,
              ac=min_allconf)


def _support(mask, need, dd):
    cnt = 0
    for decks in dd:
        for dm in decks:
            if (dm & mask).bit_count() >= need:
                cnt += 1
                break
    return cnt


def _dfs_root(root):
    dd, V = _W["dd"], _W["V"]
    ms, miss = _W["ms"], _W["miss"]
    minsz, maxsz = _W["minsz"], _W["maxsz"]
    cs, ac = _W["cs"], _W["ac"]
    found = []

    def rec(mask, size, last, cmax):
        for i in range(last + 1, V):
            nm = mask | (1 << i)
            nsize = size + 1
            sup = _support(nm, max(1, nsize - miss), dd)
            if sup < ms:                       # anti-monotone: prune
                continue
            nmax = cmax if cs[i] <= cmax else cs[i]
            if ac and sup / nmax < ac:         # all-confidence also anti-mono
                continue
            if nsize >= minsz:
                found.append((nm, sup))
            if maxsz is None or nsize < maxsz:
                rec(nm, nsize, i, nmax)

    rec(1 << root, 1, root, cs[root])
    return found


def _bits(mask):
    while mask:
        low = mask & -mask
        yield low.bit_length() - 1
        mask ^= low


def swap_clusters(groups, min_core=3):
    """Collapse equal-size itemsets that differ by exactly one card into
    core+flex shells. Two size-k sets are neighbours iff they share a
    (k-1)-subset; neighbours are union-found greedily, but a merge is
    refused when it would drop the cluster's running core (intersection)
    below `min_core` — that bounds the transitive drift that otherwise
    walks single swaps across unrelated decks. groups: [(frozenset,
    support)]. Returns [{core, flex, members, support, size}] sorted by
    size then support, largest first."""
    from collections import defaultdict

    clusters = []
    by_size = defaultdict(list)
    for S, sup in groups:
        by_size[len(S)].append((frozenset(S), sup))

    for size, items in by_size.items():
        parent, core, members, best = {}, {}, {}, {}
        for S, sup in items:
            parent[S] = S
            core[S] = set(S)
            members[S] = [S]
            best[S] = sup

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        neigh = defaultdict(list)
        for S, _ in items:
            for c in S:
                neigh[S - frozenset({c})].append(S)
        for key, grp in neigh.items():
            for S in grp[1:]:
                a, b = find(grp[0]), find(S)
                if a == b:
                    continue
                merged = core[a] & core[b]
                if len(merged) >= min_core:
                    parent[b] = a
                    core[a] = merged
                    members[a] += members[b]
                    best[a] = max(best[a], best[b])

        for S, _ in items:
            if find(S) == S and parent[S] == S:  # representative
                pass
        seen = set()
        for S, _ in items:
            r = find(S)
            if r in seen:
                continue
            seen.add(r)
            union = set().union(*members[r])
            clusters.append({
                "core": core[r], "flex": union - core[r],
                "members": members[r], "support": best[r], "size": size,
            })
    clusters.sort(key=lambda c: (-c["size"], -c["support"]))
    return clusters


def _maximal(items):
    items = sorted(items, key=lambda t: -len(t[0]))
    kept = []
    for s, sup in items:
        if not any(s < k for k, _ in kept):
            kept.append((s, sup))
    return kept
