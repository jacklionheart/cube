"""Cube-independent owner signatures, package graphs, and null models.

Inputs are owner maps or parsed drafts and decks. Support and size
thresholds are arguments; source locations and cube identity stay outside.
"""
import random
from collections import defaultdict
from itertools import combinations
from .decks import MAIN_ZONES
from .mining import Dataset

def maindeck_owners(drafts, cube, decks):
    """card -> tuple of per-draft deck owner, None where the card was not
    maindecked in that draft (not picked, deck unknown, or sideboarded)."""
    owners = {}
    for card, _, _ in cube:
        row = []
        for d in drafts:
            p = d.picks.get(card)
            deck = decks.get((d.name, p.player)) if p else None
            row.append(p.player if deck and deck.get(card) in MAIN_ZONES else None)
        owners[card] = tuple(row)
    return owners


def package_edges(groups, agreement=2):
    """Pairs of packages whose signatures agree in exactly `agreement`
    drafts. Returns [(i, j, [draft numbers agreed])]."""
    edges = []
    for i in range(len(groups)):
        for j in range(i + 1, len(groups)):
            shared = [k + 1 for k, (a, b) in
                      enumerate(zip(groups[i][0], groups[j][0])) if a is not None and a == b]
            if len(shared) == agreement:
                edges.append((i, j, shared))
    return edges


def components(groups, edges):
    """Connected components over package_edges, most cards first."""
    parent = list(range(len(groups)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i, j, _ in edges:
        parent[find(i)] = find(j)
    comps = defaultdict(list)
    for i in range(len(groups)):
        comps[find(i)].append(i)
    return sorted(comps.values(), key=lambda c: -sum(len(groups[i][1]) for i in c))


def co_maindeck_counts(owners):
    """(cardA, cardB) -> number of drafts in which both sat in the same
    maindeck. Keys are sorted pairs."""
    counts = defaultdict(int)
    n_drafts = len(next(iter(owners.values()))) if owners else 0
    for k in range(n_drafts):
        by_deck = defaultdict(list)
        for card, sig in owners.items():
            if sig[k] is not None:
                by_deck[sig[k]].append(card)
        for cards in by_deck.values():
            for a, b in combinations(sorted(cards), 2):
                counts[(a, b)] += 1
    return counts


def halos(groups, pair_counts, min_shared=2):
    """package index -> cards outside it that co-maindecked with every
    member in >= min_shared drafts."""
    def together(a, b):
        return pair_counts.get((min(a, b), max(a, b)), 0)

    in_pairs = {c for pair in pair_counts for c in pair}
    return {
        gi: sorted(x for x in in_pairs if x not in cards
                   and all(together(x, m) >= min_shared for m in cards))
        for gi, (_, cards) in enumerate(groups)
    }


def loose_components(pair_counts, min_shared=2):
    """Connected components over pairs co-maindecked >= min_shared times.
    Not transitive like signatures — chains fuse into large blobs."""
    pairs = {p: n for p, n in pair_counts.items() if n >= min_shared}
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in pairs:
        parent[find(a)] = find(b)
    comps = defaultdict(set)
    for a, b in pairs:
        comps[find(a)].update((a, b))
    return pairs, sorted(comps.values(), key=len, reverse=True)


def never_drafted(drafts, cube):
    """Cards no one picked in any draft."""
    return sorted(c for c, _, _ in cube
                  if not any(c in d.picks for d in drafts))


def never_maindecked(drafts, cube, decks, min_taken=1):
    """Cards drafted in >= min_taken drafts but maindecked in none."""
    owners = maindeck_owners(drafts, cube, decks)
    return sorted(
        c for c, _, _ in cube
        if sum(c in d.picks for d in drafts) >= min_taken
        and not any(owners[c]))


def late_first_pick(drafts, cube, threshold=350):
    """Drafted cards whose earliest overall pick across drafts is >= threshold."""
    out = []
    for c, _, _ in cube:
        picks = [d.picks[c].overall for d in drafts if c in d.picks]
        if picks and min(picks) >= threshold:
            out.append(c)
    return sorted(out)


def theme_str(cards, themes):
    """Unique themes represented in a card set, alphabetical by card."""
    seen = []
    for c in sorted(cards):
        t = themes.get(c)
        if t and t not in seen:
            seen.append(t)
    return ", ".join(seen)


def deck_sets(owners):
    """(draft index, player) -> set of cards maindecked in that deck."""
    by_deck = defaultdict(set)
    for card, sig in owners.items():
        for k, p in enumerate(sig):
            if p:
                by_deck[(k, p)].add(card)
    return by_deck


def flex_packages(groups, owners):
    """Relaxed packages with k1=1, k2=0: every card set built from a
    strict package's own deck triple where each draft's deck may miss at
    most one card. All-three-deck cores are exactly the signature groups,
    so each entry is a strict package plus per-draft flex buckets: cards
    maindecked in the other two decks of the SAME triple but absent from
    this draft's deck. A maximal (1,0) set = core + one card from each
    nonempty bucket.
    Returns [{'sig', 'cards', 'flex': [bucket per draft]}]."""
    by_deck = deck_sets(owners)
    out = []
    for sig, cards in groups:
        live = [k for k, p in enumerate(sig) if p is not None]
        decks = {k: by_deck[(k, sig[k])] for k in live}
        flex = [[] for _ in sig]
        if len(live) >= 3:  # "all but one" needs at least two others
            for i in live:
                others = set.intersection(
                    *(decks[j] for j in live if j != i))
                flex[i] = sorted(others - decks[i])
        out.append({"sig": sig, "cards": cards, "flex": flex})
    return out


def signature_groups(owners, min_size=3, *, min_shared=None):
    """Group exact signatures; None requires presence in every draft."""
    sigs = defaultdict(list)
    for card, sig in owners.items():
        live = sum(p is not None for p in sig)
        if live >= (len(sig) if min_shared is None else min_shared):
            sigs[sig].append(card)
    groups = [(sig, cards) for sig, cards in sigs.items() if len(cards) >= min_size]
    groups.sort(key=lambda g: (-len(g[1]), -sum(p is not None for p in g[0])))
    return groups


def pair_packages(owners, min_core=5):
    """Relaxed packages with k2=1: maximal card sets fully maindecked in
    one deck in 2 of the 3 drafts — i.e. cross-draft deck-pair
    intersections, subset-dominated cores removed. Adding k1=1 on top
    (allow one missing card per deck) admits any single extra card from
    either deck, so the (1,1) maximum size is just core+2; that bound is
    reported rather than enumerating arbitrary fillers.
    Returns [{'core': set, 'decks': ((k, player), (k, player))}]."""
    by_deck = deck_sets(owners)
    results = []
    for a, b in combinations(sorted(by_deck), 2):
        if a[0] == b[0]:
            continue
        core = by_deck[a] & by_deck[b]
        if len(core) >= min_core:
            results.append({"core": core, "decks": (a, b)})
    results.sort(key=lambda r: -len(r["core"]))
    kept = []
    for r in results:
        if not any(r["core"] <= k["core"] for k in kept):
            kept.append(r)
    return kept


def team_partners(owners, min_core=5):
    """Every deck's teams, keyed by the other draft:
    {(k, player): {k2: [(partner, core)]}}, unfiltered."""
    partners = defaultdict(lambda: defaultdict(list))
    for e in pair_packages(owners, min_core):
        (ka, pa), (kb, pb) = e["decks"]
        partners[(ka, pa)][kb].append((pb, e["core"]))
        partners[(kb, pb)][ka].append((pa, e["core"]))
    return partners


def straddles(owners, drafts=None, *, min_core=5):
    """Decks whose 2-of-3 cores pair them with two or more different
    decks of the same other draft — one drafter merging what another
    draft's table split. Returns {(k, player): {k2: [(partner, core)]}}
    keeping only same-draft partner lists of length >= 2."""
    return {
        deck: {k2: plist for k2, plist in by_draft.items() if len(plist) >= 2}
        for deck, by_draft in team_partners(owners, min_core).items()
        if any(len(plist) >= 2 for plist in by_draft.values())
    }


def unique_ensembles(owners):
    """deck -> the largest subset of its maindeck in which no two cards
    were ever co-maindecked in any other deck (exact maximum independent
    set over cross-deck pair conflicts; pairs bind, so no larger subset
    can recur if no pair does)."""
    by_deck = deck_sets(owners)
    pair_decks = defaultdict(list)
    for dk, cards in by_deck.items():
        for a, b in combinations(sorted(cards), 2):
            pair_decks[(a, b)].append(dk)
    out = {}
    for dk, deck_cards in by_deck.items():
        cards = sorted(deck_cards)
        idx = {c: i for i, c in enumerate(cards)}
        n = len(cards)
        adj = [0] * n
        for a, b in combinations(cards, 2):
            if any(d != dk for d in pair_decks.get((a, b), [])):
                adj[idx[a]] |= 1 << idx[b]
                adj[idx[b]] |= 1 << idx[a]
        best = [0, 0]

        def bb(avail, cur, size):
            if size + bin(avail).count("1") <= best[0]:
                return
            if not avail:
                best[0], best[1] = size, cur
                return
            v = max((i for i in range(n) if avail >> i & 1),
                    key=lambda i: bin(adj[i] & avail).count("1"))
            bb(avail & ~(1 << v) & ~adj[v], cur | (1 << v), size + 1)
            bb(avail & ~(1 << v), cur, size)

        bb((1 << n) - 1, 0, 0)
        out[dk] = [cards[i] for i in range(n) if best[1] >> i & 1]
    return out


def null_model(drafts, cube, decks, iters=2000, seed=0, *, min_size=3, min_shared=None):
    """Permutation test: keep every player's picks, replace each maindeck
    with a uniform random same-size subset of that player's picks, and
    recount strict packages. Returns (observed, samples) where each entry
    is (n_packages, total_cards_in_packages, largest_package)."""
    observed_owners = maindeck_owners(drafts, cube, decks)

    def stats(owners):
        groups = signature_groups(owners, min_size, min_shared=min_shared)
        sizes = [len(cards) for _, cards in groups]
        return (len(sizes), sum(sizes), max(sizes, default=0))

    picks_by_deck = []  # (draft index, player, [cards picked], n maindecked)
    for k, d in enumerate(drafts):
        by_player = defaultdict(list)
        for card, p in d.picks.items():
            by_player[p.player].append(card)
        for player, cards in by_player.items():
            n_main = sum(1 for c in cards if observed_owners[c][k] == player)
            if n_main:
                picks_by_deck.append((k, player, sorted(cards), n_main))

    rng = random.Random(seed)
    n_drafts = len(drafts)
    samples = []
    for _ in range(iters):
        owners = {card: [None] * n_drafts for card, _, _ in cube}
        for k, player, cards, n_main in picks_by_deck:
            for c in rng.sample(cards, n_main):
                owners[c][k] = player
        samples.append(stats({c: tuple(o) for c, o in owners.items()}))
    return stats(observed_owners), samples



def jaccard_components(owners, theta=0.6, *, min_support=4, min_size=4):
    """Connected components using Jaccard similarity of deck-owner sets."""
    card_decks = {}
    for c, sig in owners.items():
        for k, p in enumerate(sig):
            if p:
                card_decks.setdefault(c, set()).add((k, p))
    cards = [c for c in card_decks
             if len(card_decks[c]) >= min_support]
    parent = {c: c for c in cards}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(len(cards)):
        A = card_decks[cards[i]]
        for j in range(i + 1, len(cards)):
            B = card_decks[cards[j]]
            u = len(A | B)
            if u and len(A & B) / u >= theta:
                parent[find(cards[i])] = find(cards[j])
    out = {}
    for c in cards:
        out.setdefault(find(c), set()).add(c)
    return [s for s in out.values() if len(s) >= min_size]


def backbone_depth(owners, pool, *, min_support=6):
    d = Dataset.from_owners(owners, restrict_to=list(pool))
    depth = {c: 0 for c in pool}
    for S, _ in d.mine(min_support=min_support, min_size=1, miss=0,
                       maximal=False, workers=1):
        for c in S:
            if len(S) > depth[c]:
                depth[c] = len(S)
    return depth
