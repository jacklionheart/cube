# Mining recurring "teams" from rotisserie drafts — state of the art & recommendations

**Problem recap.** We have `D` ≈ 13–37 drafts; each draft has ~10 decks; each deck is a set of
~25 nonland cards from a vocabulary of `W` ≈ 550–1000 cards. A "team" is a card set `S` that
recurs across drafts. Support is counted **at the draft level**: a draft contributes 1 to
`support(S)` iff *any* of its decks satisfies the membership predicate. We want (1) strict
frequent sets, (2) **all‑but‑m / error‑tolerant** frequent sets (the key deliverable),
(3) maximal/closed condensation to "hide subsets" in the UI, and (4) interestingness ranking
that survives heavy overlap and ubiquitous staples.

This scale is *tiny* by data‑mining standards (≤ ~370 decks, ≤ 1000 bits/deck ≈ 16 × `uint64`
words). The binding constraint is not raw throughput but the combinatorial blow‑up of the
all‑but‑m search and the redundancy of the output. Everything below is chosen for
exactness‑where‑possible, simplicity, and a single machine.

---

## 1. Recommendations (what to actually build)

- **Strict frequent itemsets.** Hand‑roll a **vertical bitset Eclat/DFS** over draft‑support.
  At our scale a Python + NumPy (`uint64` deck matrix, `np.bitwise_and`, `np.bitwise_count`)
  implementation is exact and effectively instant. If you'd rather not hand‑roll, use
  **mlxtend `fpgrowth`** or **PAMI** on a per‑deck table, then re‑aggregate to draft support.
  *Caveat:* off‑the‑shelf miners count transaction (deck) support, not our draft‑level support,
  so you must either feed them one "transaction" per deck and re‑fold to drafts in a
  post‑pass, or just hand‑roll (recommended — the predicate is non‑standard).

- **All‑but‑m (the important one).** Keep your **bitset DFS with an absolute, fixed `m`** and
  the per‑deck predicate `popcount(deck & S) ≥ |S| − m`. This is exactly Yang–Fayyad–Bradley's
  **"weak" error‑tolerant itemset** (per‑row error bound), and it **is anti‑monotone** — your
  pruning is *sound* (proof in §3). Make it fast with **incremental per‑deck intersection
  counts** driven by **vertical tid‑lists** (per card: which decks contain it), plus item
  ordering and top‑level subtree parallelism. Add a **column‑density post‑filter** (each card in
  `S` must actually appear in a decent fraction of the witnessing decks/drafts) to kill
  degenerate "padded" sets — this is not anti‑monotone, so apply it *after* enumeration, not as a
  pruning rule.

- **Maximal vs closed for "hide subsets".** For the UI goal, **maximal is the right default**:
  it reports only the largest recurring team and suppresses every subset. Closed keeps a set
  whenever a subset has *strictly higher* support (lossless for exact supports) — more sets,
  more noise for a "biggest team" view. Because we allow errors and sets overlap heavily,
  don't chase a formal "closed‑ETI"; instead **post‑process with tolerant maximality**:
  drop `S` if some reported `S′ ⊇ S` has `support(S′) ≥ support(S) − slack` (or is Jaccard‑near).
  This mirrors AC‑Close / δ‑tolerance‑closed thinking without the machinery.

- **Ranking.** Do **not** rank by raw support. Use a **null‑invariant** measure as the primary
  score — **all‑confidence** (= `bond`/`h‑confidence`), `allconf(S) = support(S) / maxᵢ support({i})`.
  It directly penalizes any set that owes its support to one ubiquitous staple, and it is itself
  **downward‑closed**, so you can even push a min‑all‑confidence threshold *into* the search
  (hyperclique‑style). Report **lift** and **cosine/Kulczynski + imbalance ratio** as secondary
  columns. Rationale and references in §5.

**One‑paragraph build plan.** Represent decks as a `(n_decks × n_words) uint64` matrix and cards
as vertical bitsets over decks. DFS by ascending card index (prefix‑closed, no duplicates),
maintain per‑deck running intersection counts, fold decks→drafts to get draft support, prune on
`support < minsup` (valid for strict and for absolute‑`m` all‑but‑m). Enforce `|S| > m` (see §3
edge case). Then: tolerant‑maximal filter → column‑density filter → rank by all‑confidence, show
lift/cosine. Parallelize by handing each top‑level starting card to a worker.

---

## 2. Candidate algorithms & libraries — comparison

| Algorithm / library | Exact? | Speed on **dense** data | Maximal | Closed | Error‑tolerant | Python availability | Verdict for us |
|---|---|---|---|---|---|---|---|
| **Apriori** (BFS, candidate‑gen) | ✔ | Poor (candidate blow‑up, many DB scans) | via post‑filter | no | no | mlxtend, efficient‑apriori, PAMI | Fine as a reference; too slow/clunky on dense decks |
| **Eclat** (vertical tid‑lists/bitsets, DFS) | ✔ | Good; bitsets shine when dense | post‑filter | no | adaptable | PAMI, SPMF(pyspmf), Borgelt `pyfim` | **Our strict engine** (hand‑roll) |
| **dEclat / diffsets** | ✔ | Very good on dense (diffsets shrink) | — | (dCharm) | no (needs counts, not just tids) | SPMF | Nice for *strict*; diffsets don't directly help all‑but‑m (we need counts) |
| **FP‑growth** | ✔ | Very good; no candidate gen | (fpmax) | (fpclose) | no | mlxtend `fpgrowth`, PAMI, SPMF | Great drop‑in for strict if not hand‑rolling |
| **LCM (Uno)** | ✔ | **Best‑in‑class** closed (FIMI'04 winner), linear in #closed | ✔ | ✔ | no | SPMF, Uno's C, PAMI (impl of family) | Use if you want gold‑standard closed/maximal |
| **CHARM / dCharm** | ✔ | Very good closed on dense | — | ✔ | no | SPMF | Good closed alternative to LCM |
| **GenMax** | ✔ | Best exact **maximal** on dense (progressive focusing) | ✔ | — | no | SPMF | Reference for maximal; mlxtend `fpmax` is easier |
| **MAFIA** | ✔ (or approx mode) | Excellent on long/dense patterns | ✔ | — | no | SPMF | Strong on very long itemsets |
| **ETI "weak" DFS (ours)** | ✔ (per‑row def) | Good; bitset popcounts | via filter | tolerant filter | ✔ (abs. `m`) | hand‑roll | **Our all‑but‑m engine** |
| **AC‑Close** (core‑pattern recovery) | approx | Good | — | approx‑closed | ✔ | not packaged (paper/impl only) | Ideas worth borrowing for dedup |
| **δ‑tolerance closed (Cheng/Ke/Ng)** | approx | Good | — | approx‑closed | ✔ | not packaged | Concept for tolerant closure |
| **Tiling / Boolean matrix factorization** | approx (opt.) | Good, but different objective | n/a | n/a | ✔ (noise‑absorbing) | `scikit‑mine`, research code | Overkill; changes the problem to matrix cover |
| **mlxtend** | ✔ | OK (pandas one‑hot) | fpmax | fpclose | no | ✅ mature | Easiest strict/closed/maximal for a demo |
| **PAMI** | ✔ | Good, many variants | ✔ | ✔ | some FT variants | ✅ 100+ algos, maintained (JMLR'24) | Best "batteries‑included" lib; check its FT algos |
| **SPMF (via pyspmf)** | ✔ | Excellent (Java, Eclat/LCM/Charm/GenMax) | ✔ | ✔ | some | ✅ wrapper | Widest algorithm coverage; JVM dependency |
| **efficient‑apriori** | ✔ | OK | no | no | no | ✅ pure‑python | Only if you want zero deps + strict |
| **orange3‑associate** | ✔ | OK (FP‑growth) | no | no | no | ✅ | Fine for quick strict association rules |

**Why bitset‑DFS / vertical beats Apriori on our data:** decks are *dense* relative to vocabulary
in the regions that matter (staples co‑occur), so candidate‑generation approaches (Apriori)
explode; vertical bitset intersection with hardware popcount is branch‑free and cache‑friendly,
and diffsets (dEclat) or running counts keep the per‑node cost near O(#decks). At 370 decks × 16
words this is nanoseconds per node.

---

## 3. Error‑tolerant / fault‑tolerant itemsets (deepest section)

### 3.1 Landscape of definitions

- **Weak vs strong ETI — Yang, Fayyad, Bradley, KDD 2001** ("Efficient discovery of
  error‑tolerant frequent itemsets in high dimensions"). Given a 0/1 matrix and tolerance `ε`:
  - **Strong ETI:** a set of columns `S` plus a set of rows `R` (`|R| ≥ minsup`) such that the
    **overall density** of the `R × S` submatrix is `≥ 1 − ε` (errors pooled globally). This is a
    dense‑submatrix / tile objective and is **NOT anti‑monotone** — you can't safely prune.
  - **Weak ETI:** `S` with a supporting row‑set `R` (`|R| ≥ minsup`) where **every row in `R`**
    individually contains `≥ (1 − ε)·|S|` of `S`'s items (per‑row error bound). This **is**
    anti‑monotone in the strong sense used for pruning, which is why their efficient algorithm
    targets it. **Our all‑but‑m predicate is exactly a weak ETI with an absolute error budget
    `m` instead of a fractional `ε`.**

- **Fault‑tolerant support — Pei, Tung, Han, DMKD 2001** ("Fault‑tolerant frequent pattern
  mining: problems and challenges"). Adds an **item‑level (column) constraint** on top of the
  per‑row tolerance: each item of `S` must be present in at least a fraction of the FT‑supporting
  transactions. This kills the "an item is in the set but is missing from almost everyone"
  degeneracy that a pure per‑row bound allows. The item‑level constraint is **not anti‑monotone**;
  practical miners (Max‑FTP, bit‑vector FT approaches, FTApriori/FP‑style) handle it with extra
  bookkeeping or post‑filtering.

- **Approximate/relaxed & tolerant‑closed.** **AC‑Close** (Cheng, Ke, Ng) recovers
  representative "core patterns" so noise‑fragmented approximate itemsets don't explode into
  near‑duplicates; **δ‑tolerance closed itemsets** (same authors, ICDM'06) formalize a tolerant
  closure to condense approximate output. **Tiling** (Geerts, Goethals, Mielikäinen, DS'04) and
  **Boolean Matrix Factorization** (Miettinen et al.) attack the same noise but reframe it as
  covering the matrix with dense rectangles / low‑rank Boolean factors — a different objective
  (global reconstruction) that we don't need.

### 3.2 Is our bitset‑DFS anti‑monotone? — **Yes, verified (for fixed absolute `m`).**

Let deck `d ⊆ V`, and say `d` *satisfies* `S` iff `|d ∩ S| ≥ |S| − m`.
`support(S) = #{ drafts D : ∃ d ∈ D with d satisfies S }`.

**Claim.** For any card `x ∉ S`, if `d` satisfies `S ∪ {x}` then `d` satisfies `S`.
*Proof.* `|d ∩ (S ∪ {x})| = |d ∩ S| + 𝟙[x ∈ d]`. If `d` satisfies `S ∪ {x}` then
`|d ∩ S| + 𝟙[x ∈ d] ≥ |S| + 1 − m`, so `|d ∩ S| ≥ |S| + 1 − m − 𝟙[x ∈ d] ≥ |S| − m`. ∎

The *same* witnessing deck therefore witnesses `S`, so every draft supporting `S ∪ {x}` also
supports `S`, giving **`support(S ∪ {x}) ≤ support(S)`**. Hence pruning a branch when
`support(S) < minsup` is sound: no superset can recover. **Your belief is correct.**

**The load‑bearing condition is that `m` is an absolute constant.** If instead you used a
*proportional* budget (threshold `⌈(1 − ε)|S|⌉`, i.e. `m` grows with `|S|`), the threshold rises
by `< 1` per added item while the intersection can rise by `1`, so a deck that *failed* `S` can
*pass* `S ∪ {x}` — **anti‑monotonicity breaks** (this is the well‑known reason strong/proportional
FT support is neither monotone nor anti‑monotone, per Pei–Tung–Han). Keep `m` absolute if you want
free pruning.

**Edge cases to handle:**
1. **Degenerate small sets.** If `|S| ≤ m`, the threshold `|S| − m ≤ 0` and *every* deck
   satisfies, so `support(S) = D` (all drafts). At `|S| = m + 1` a deck passes if it contains
   *any one* of the items. So enforce a **minimum reported size `|S| > m`** (better: `|S| ≥ m + k`
   for some `k`) — error tolerance is only meaningful for larger teams. Note this also means the
   anti‑monotone prune does nothing until `|S| > m`; seed the DFS accordingly.
2. **Column degeneracy (weak‑ETI's blind spot).** The per‑deck bound never forces any *particular*
   card to appear. A card can be "in the team" yet missing from nearly every witnessing deck.
   Add the **item‑level density post‑filter** from Pei–Tung–Han (each card of `S` present in
   ≥ some fraction of witnessing decks, or of supporting drafts). It's not anti‑monotone → apply
   after enumeration.
3. **Double‑counting within a draft** is already handled correctly: draft support is an OR over
   its decks, and different decks/drafts may miss different items — the proof is per‑deck, so this
   is fine.

### 3.3 Making the all‑but‑m search fast (single machine)

- **Vertical tid‑lists + incremental counts.** Precompute, per card `x`, a **bitset `T[x]` over
  decks** (which decks contain `x`). Maintain a length‑`n_decks` vector `c` of running
  intersection counts. Extending `S → S ∪ {x}` updates `c += bit(T[x])` in O(#decks); a deck
  satisfies iff `c_d ≥ |S| − m`. Fold decks→drafts (precomputed deck→draft map) to get draft
  support. This is the all‑but‑m analogue of Eclat: you carry counts instead of intersecting
  tid‑lists, because you need the *degree* of overlap, not just membership.
- **Why diffsets/dEclat don't transfer directly.** Diffsets accelerate *exact* strict mining by
  storing tid *differences*; but all‑but‑m needs per‑deck counts (a deck can be "in" via different
  missing items), so a pure set‑difference doesn't capture the count. The incremental‑count trick
  above recovers the same O(#decks)/node cost. Use diffsets only for the strict engine.
- **Ordering heuristics.** DFS by fixed card order to stay prefix‑closed (no duplicate sets).
  For pruning to bite sooner, try **ascending card frequency** (rare cards first shrink supports
  fast); benchmark against descending — on dense data the winner depends on how staples cluster.
- **Popcount vectorization.** Represent decks as `(n_decks × n_words) uint64`; a candidate `S` is
  a `n_words` bitset; `np.bitwise_count(decks & S).sum(axis=1)` gives all per‑deck counts in one
  vectorized shot (NumPy ≥ 2.0 has `bitwise_count`; else a 16‑bit popcount LUT). At our size the
  entire matrix fits in L2.
- **Parallelism across cores.** The DFS subtrees rooted at each top‑level starting card are
  **independent → embarrassingly parallel**. Because pure‑Python is GIL‑bound, either (a) use
  `multiprocessing` with one subtree per task, or (b) push the hot popcount loop into
  **Numba/Cython with `nogil`** and use a thread pool. Given the data volume, a single core is
  likely already sub‑second; parallelism matters only if `m` and vocabulary are pushed hard.
- **GPU / BMF is overkill.** Hundreds of rows and ≤16 words per row never justify a GPU or a
  Boolean‑factorization pipeline; those pay off at 10⁵–10⁸ rows or when the goal is matrix
  reconstruction rather than exact set enumeration.

---

## 4. "Hide subsets": maximal vs closed (and the error‑tolerant wrinkle)

- **Closed** = no superset has equal support; a **lossless** condensation (you can recover every
  frequent set *and its exact support*). **Maximal** = no frequent superset; **smaller** output
  but you lose subset supports.
- For a UI that says "show me the biggest recurring team and hide its pieces," **maximal** is the
  natural fit. Closed will still surface a subset `S` whenever some card added to `S` drops the
  support even by one draft — exactly the "staple pieces" you want hidden.
- **Under error tolerance, closure is genuinely subtler:** many near‑identical ETIs share the same
  support because errors absorb the differences, so a formal closed‑ETI is ambiguous and tends to
  fragment (the motivation for AC‑Close and δ‑tolerance‑closed). Rather than implement tolerant
  closure, use the **tolerant‑maximal post‑filter** from §1: sort ETIs by size desc, and drop `S`
  if a kept `S′ ⊇ S` has `support(S′) ≥ support(S) − slack` (optionally also require high Jaccard
  so you don't hide a genuinely distinct smaller team). Simple, controllable, matches the UI goal.

---

## 5. Interestingness / ranking for overlapping, staple‑heavy sets

Raw support is misleading here: the format's ubiquitous staples co‑occur in almost every deck, so
any set of staples scores high without being "interesting." The fix is **null‑invariant** measures
(invariant to the number of decks that contain *none* of the items), the property Tan–Kumar–
Srivastava (KDD'02) and Wu–Chen–Han identify as essential for co‑occurrence patterns.

- **all‑confidence / bond / h‑confidence** (Omiecinski 2003; Xiong–Tan–Kumar hyperclique):
  `allconf(S) = support(S) / maxᵢ support({i})`. It's the minimum confidence of any rule from `S`,
  so a set containing one near‑universal staple is heavily penalized. **It is downward‑closed**,
  so a `min_allconf` threshold is both a *ranking* and an additional *pruning* constraint you can
  push into the search (mine **hyperclique patterns** directly). **Primary recommendation.**
- **cosine (IS) and Kulczynski + Imbalance Ratio** — also null‑invariant; Wu–Chen–Han recommend
  Kulczynski paired with imbalance ratio to distinguish balanced co‑occurrence from skewed ones.
  Good secondary sort keys for overlapping teams of unequal card popularity.
- **lift / leverage** — not null‑invariant (sensitive to deck count), but familiar and useful as a
  displayed column; don't use lift as the sole rank on tiny `D`.
- For sets of size > 2, all‑confidence and cosine generalize naturally (max/geo‑mean of singleton
  supports in the denominator). Tan–Kumar–Srivastava's property framework (symmetry, inversion,
  null‑invariance) is the checklist for picking among the ~20 measures.

**Practical stack:** filter with `min_support` (draft‑level) → filter/rank with `all‑confidence`
→ break ties / secondary sort with cosine or Kulczynski+IR → display lift for interpretability.

---

## 6. Library verdicts (our scale)

- **Hand‑rolled NumPy bitset‑DFS** — recommended for both engines. The predicate (draft‑level OR,
  absolute‑`m` weak ETI) is non‑standard, the data is tiny, and rolling it yourself gives exact
  control over support semantics, the column‑density filter, and all‑confidence pushdown.
- **PAMI** (JMLR 2024, actively maintained, 100+ algos incl. closed/maximal and some
  fault‑tolerant variants) — best "batteries‑included" library; good for cross‑checking your
  strict output and for closed/maximal if you don't hand‑roll.
- **SPMF via pyspmf** — widest algorithm coverage (Eclat, dEclat, FP‑growth, LCM, CHARM, GenMax,
  MAFIA). Reach for it if you want a gold‑standard LCM/CHARM closed run; JVM dependency.
- **mlxtend** — easiest for a quick strict/closed/maximal demo (`fpgrowth`/`fpclose`/`fpmax`) on a
  one‑hot DataFrame, but pandas one‑hot and transaction‑level support make it awkward for our
  draft‑level semantics.
- **efficient‑apriori / orange3‑associate** — zero/low‑dependency strict mining only; fine for a
  sanity baseline, no maximal/closed/FT.
- **AC‑Close / δ‑tolerance‑closed / tiling / BMF** — no maintained Python package we'd adopt;
  borrow the *ideas* (core‑pattern dedup, tolerant closure) for the post‑filter, don't build the
  pipeline.

---

## References

**Error‑ / fault‑tolerant itemsets**
- C. Yang, U. Fayyad, P. S. Bradley. *Efficient discovery of error‑tolerant frequent itemsets in high dimensions.* KDD 2001. https://dl.acm.org/doi/10.1145/502512.502539
- J. Pei, A. K. H. Tung, J. Han. *Fault‑tolerant frequent pattern mining: problems and challenges.* DMKD workshop 2001. (survey overview: https://arxiv.org/pdf/1610.05116 )
- G. Poernomo, V. Gopalkrishnan et al. *On mining approximate and exact fault‑tolerant frequent itemsets.* Knowl. Inf. Syst. 2017. https://link.springer.com/article/10.1007/s10115-017-1079-4
- *Max‑FTP: Mining Maximal Fault‑Tolerant Frequent Patterns.* https://link.springer.com/content/pdf/10.1007/978-3-540-73390-4_26.pdf
- *An efficient pattern‑growth approach for mining fault‑tolerant frequent itemsets.* PMC7126664. https://pmc.ncbi.nlm.nih.gov/articles/PMC7126664/
- H. Cheng, Y. Ke, W. Ng. *AC‑Close: Efficiently Mining Approximate Closed Itemsets by Core Pattern Recovery.* ICDM 2006. https://www.researchgate.net/publication/220765303
- H. Cheng, Y. Ke, W. Ng. *δ‑Tolerance Closed Frequent Itemsets.* ICDM 2006.

**Exact strict / closed / maximal miners**
- M. J. Zaki, K. Gouda. *Fast Vertical Mining Using Diffsets (dEclat/dCharm).* KDD 2003. http://www.cs.rpi.edu/~zaki/PaperDir/SIGKDD03-diffsets.pdf
- T. Uno, M. Kiyomi, H. Arimura. *LCM ver.2: Efficient Mining of Frequent/Closed/Maximal Itemsets.* FIMI 2004. https://ceur-ws.org/Vol-126/uno.pdf  · ver.3: http://research.nii.ac.jp/~uno/papers/05lcm3.pdf  · code: https://research.nii.ac.jp/~uno/codes.htm
- M. J. Zaki, C.-J. Hsiao. *CHARM: An Efficient Algorithm for Closed Itemset Mining.* http://www.philippe-fournier-viger.com/spmf/Charm02.pdf
- K. Gouda, M. J. Zaki. *GenMax: Mining Maximal Frequent Itemsets.* DMKD 2005. https://link.springer.com/article/10.1007/s10618-005-0002-x
- Burdick, Calimlim, Gehrke. *MAFIA: A Maximal Frequent Itemset Algorithm.* https://www.semanticscholar.org/paper/35aa519a94130bf8d3778af96a37836c45a9e1b7

**Interestingness / null‑invariant measures**
- P.-N. Tan, V. Kumar, J. Srivastava. *Selecting the Right Interestingness Measure for Association Patterns.* KDD 2002. https://dmr.cs.umn.edu/Papers/P2002_1.pdf
- L. Geng, H. Hamilton. *Interestingness Measures for Data Mining: A Survey.* ACM Comput. Surv. 2006. https://dl.acm.org/doi/10.1145/1132960.1132963
- E. Omiecinski. *Alternative Interest Measures for Mining Associations (any‑confidence, all‑confidence, bond).* IEEE TKDE 2003.
- H. Xiong, P.-N. Tan, V. Kumar. *Hyperclique Pattern Discovery (h‑confidence).* DMKD 2006. https://www-users.cse.umn.edu/~kumar001/papers/clique_dmkd.pdf
- E. Cohen et al. *Finding Interesting Associations without Support Pruning.* http://ilpubs.stanford.edu:8090/485/1/2000-9.pdf

**Dense / tiles / Boolean matrix factorization**
- F. Geerts, B. Goethals, T. Mielikäinen. *Tiling Databases.* Discovery Science 2004.
- P. Miettinen et al. *MDL4BMF: Minimum Description Length for Boolean Matrix Factorization.* ACM TKDD 2014. https://dl.acm.org/doi/10.1145/2601437 · BMF tutorial: https://people.mpi-inf.mpg.de/~pmiettin/bmf_tutorial/material.html

**Python libraries**
- PAMI (JMLR 2024): https://www.jmlr.org/papers/volume25/22-1026/22-1026.pdf · repo topic: https://github.com/topics/frequent-pattern-mining
- mlxtend `fpgrowth`/`fpmax`: https://rasbt.github.io/mlxtend/user_guide/frequent_patterns/fpmax/
- SPMF (Fournier‑Viger): https://www.philippe-fournier-viger.com/spmf/  (pyspmf wrapper) · Eclat/dEclat page: https://www.philippe-fournier-viger.com/spmf/Eclat_dEclat.php
