# Outline: "What Three Rotos Taught Us About the LoL Cube's Packages"

> Working notes / skeleton — all prose to be rewritten in Jack's voice.
> Data sources: Maindecked Together tab (strict packages), `packages.py`
> (graph + halos), Pick Summary (cut lists). Win-rate data was used only to
> decide what deserved attention and in what order; no records or
> percentages appear in the article.

## Audience calibration (not in article)

- **Ben (Mister Metronome)** — allergic to bucket-scores that "solve" a
  format. Every section must read as *map, not verdict*: "here are the
  seams drafters found" never "here is the tier list." The package graph
  is naturally Ben-shaped: edges are literally documented *choices* (a
  package that went two ways), which is the opposite of a score.
- **Ethan (lordtupperware)** — the steward; asked "what was never picked"
  as a cut heuristic. Give him four differently-shaped lists and show how
  the *differences between the lists* are more informative than any one
  list. He drafted in D2 (and is inside several packages himself — P3, P6,
  P13, P16, P17); worth a wink.
- **samp (Rough Drafts)** — will want to run this on his own rotos (he
  already keeps pod spreadsheets; Ep. 33 covers roto-ing his cube). The
  gift is the *method*: precise definitions (signature, edge, halo) he can
  reimplement, plus the honest gotchas (pod size, snake math, companions,
  pools that omit basics). Frame as "questions this lets you ask," not
  "conclusions it hands you."

---

## 1. Setup — what this data is and isn't

- 3 rotisserie drafts, 28 players, every deck recovered (27 sealeddeck
  links + 1 OCR'd screenshot), every pick tracked.
- Key definition (THE conceptual move of the piece): a **package** =
  a maximal set of cards that were maindecked *in the same deck* in
  **all three** drafts. Not "cards I think go together" — cards the
  table repeatedly proved go together.
- Metric behind section: Maindecked Together tab; companion-aware
  maindeck definition (footnote: a sideboard Lurrus only counts if the
  deck actually satisfies MV≤2 — one of our three Lurrus decks didn't).
- Honesty paragraph (Ben): n=3, one community's metagame, roto ≠ blind
  draft (full information + singleton). This is archaeology, not physics.

## 2. The 11 packages, themed (min size 3; Jack's labels)

- Definition update: packages now require >= 3 cards — every surviving
  package carries one of Jack's hand-applied themes (Tokens, Spells,
  Ramp, Graveyard, Sacrifice, Rectangles, Discard). Numbering unified:
  sheet Group # = P#, size-desc.

| P# | n | theme | colors | anchor cards |
|----|---|-------|--------|--------------|
| P1 | 10 | Tokens | WR | Dog Walker, Inspiring Overseer, Resolute Reinforcements… |
| P2 | 8 | Spells | UR | Consider, Expressive Iteration, Think Twice… |
| P3 | 6 | Ramp | URG | Fires of Invention, Path to the World Tree… |
| P4 | 5 | Spells | WUR | Dovin's Acuity, Pyrrhic Strike… |
| P5 | 5 | Graveyard | G | Spider Spawning, Satyr Wayfinder… |
| P6 | 4 | Ramp | BG | Cloud of Darkness, Everything Pizza… |
| P7 | 3 | Sacrifice | WB | Bastion of Remembrance, Voice of Victory… |
| P8 | 3 | Rectangles | WB | Hopeless Nightmare, Michiko's Reign of Truth… |
| P9 | 3 | Discard | U | Censor, Quench, Shoreline Looter |
| P10 | 3 | Sacrifice | BR | Deadly Dispute, Mayhem Devil… |
| P11 | 3 | Graveyard | BG | Broodspinner, Verdant Catacombs… |

- The dropped size-2 pairs aren't deleted knowledge: they reappear as
  flex/halo members and inside the 2-of-3 view (sheet tabs). Note for
  prose: theme pairs recur across color anchors (Spells in UR and WUR,
  Ramp in URG and BG, Sacrifice in WB and BR, Graveyard mono-G and BG)
  — the cube's themes are color-flexible, which is itself a finding.

## 2b. Are the packages real? (the null model)

- The skeptic's question, answered before it's asked (this is the samp
  paragraph, and it's also the best Ben insurance in the piece because it
  *limits* the claim rather than inflating it).
- Method, one sentence: keep everyone's exact picks, replace each
  maindeck with a random same-size subset of that player's own pool,
  re-count packages, 2,000 times (`packages.py --null`).
- Results at min size 3 (observed vs. chance, 2,000 permutations):
  - packages: **11 observed** vs 5.6 ± 1.5 (p < .0005; chance max 10)
  - cards inside packages: **53** vs 20.4 ± 5.3 (p < .0005; chance max 38)
  - largest package: **10** vs 5.0 ± 1.1 (p < .0005; chance max 9)
- With the size-3 floor, ALL THREE stats are outside anything chance
  produced in 2,000 worlds — raising the floor removed the coincidence-
  range tail that 2-card pairs had. (At size ≥2 the count stat was only
  p ≈ .002; that's now a methods footnote, not a caveat.)
- Scope caveat (state it): this tests the deckbuild stage only — picks
  stay as drafted, so it asks "given what people picked, are the shared
  maindecks surprising?", not "are picks correlated?"

## 3. The package graph — where drafters faced choices

- Definition: edge between two packages when their deck-owner signatures
  agree in **exactly 2 of 3** drafts = "traveled together twice, split
  once." An edge is a documented fork in the road. 19 edges, 8 connected
  components.
- Metric behind section: `packages.py` (components + edge draft-lists).
- Component map (labels are MY DRAFTS):
  - **A — the White nexus** (8 packages, 18 cards): Yorion blink
    (P13+P17), W builders (P16), W tempo-auras (P15), WB drain (P7+P12),
    WB/WU enchantments (P8+P14). White is the cube's connective tissue:
    one supercluster with many exits. Richest section for Ben-style
    "options and directions" prose.
  - **B — the Spells fork** (P2 UR + P4 WU + P23): the featured example.
    Flooey and j_mazz kept the whole spells pile together in D1–D2; in
    D3 it *split* — llich took the UR half, ColdBrewNate the WU half.
    Same core, two archetype destinations. (This is the G17/G13 overlap.)
  - **C — the Blue tempo web** (P9, P19, P20, P24, P25): five small
    packages, densely connected, no fixed home — mono-U/UX shells get
    reassembled differently every draft.
  - **D — the Boros monolith** (P1 alone): no edges. Ten cards, three
    different drafters, identical core. The most "solved" package —
    worth naming that tension for Ben explicitly.
  - **E — 5c Fires/Pizza** (P3+P6), **F — BG graveyard** (P5+P11),
    **G — Sacrifice/Treasure** (P10, P21, P22), **H — U oddments** (P18).
- Optional visual: mermaid graph via `packages.py --mermaid`.

## 4. Loosening the definition — halos (2-of-3 co-maindecking)

- Definition: a package's **halo** = cards that shared a maindeck with
  *every* member of that package in ≥2 of 3 drafts. (Naive 2-of-3
  components fuse into a 274-card blob — worth one sentence for samp on
  *why*: the relation isn't transitive, so you localize instead.)
- Metric behind section: `packages.py --loose`.
- Best exhibits:
  - P13 (Aang + Yorion) carries a **+21 halo** — the entire blink shell
    (Adagia, Pilgrim's Eye, Organ Hoarder, Stockpiling Celebrant,
    Keruga…). The strict pair is the *flag*; the halo is the *deck*.
  - P10 (sac core) halo pulls in Blood Crypt, Bloodtithe Harvester,
    Eaten Alive, Phantom Train, Piggy Bank — bridges components G↔each
    other.
  - P22 (Magda/Torch) halo reveals the equipment/treasure subtheme
    (Experimental Synthesizer, Makeshift Munitions, Katana).
- Framing: strict = "always true," halo = "usually true." Two dials the
  reader can turn; neither is a tier.

## 5. The cut-list question (Ethan's section)

Four ways to generate "underloved cards," each with different biases.
Metrics behind section: Pick Summary columns (Drafts Taken, Maindecked,
First Pick).

- **List A — never drafted at all** (24 cards): Ethan's original ask.
  Composition skews: green filler (Sagu Wildling, Might of the Masses,
  Ram Through), cycling taplands (Scattered Groves, Sheltered Thicket),
  vanilla bodies (Colossal Dreadmaw, Durable Coilbug), narrow build-
  arounds (Wilderness Reclamation, Happily Ever After).
- **List B — drafted but never maindecked** (89; 44 taken once / 29
  twice / 16 thrice): the "speculative picks" list. Includes Obosh —
  drafted as a companion bet that never paid.
- **List C — taken in ALL THREE drafts, never maindecked** (16:
  Agatha's Champion, Vampire Nighthawk, Éomer, Star of Extinction…):
  the most interesting list — cards drafters *repeatedly want* and
  decks repeatedly reject. Arguably stronger cut evidence than List A
  (A-cards were merely ignored; C-cards were tried and failed), OR
  evidence they're one support-card away from working. Both readings —
  leave the fork open.
- **List D — never picked before overall pick 350** (38): "nobody
  prioritized." 29 overlap with B, but the **9 that don't** are the
  counter-list: picked dead last AND maindecked anyway — Rise of the
  Varmints, Fell Stinger, Foreboding Landscape. Late ≠ cuttable;
  sometimes late = wheelable glue. This is the caveat that keeps List D
  honest.
- Caveats paragraph (the Ben insurance, but genuinely true):
  - n=3 with one player pool; taste cascades (one drafter's pet theme
    dies with their absence).
  - Lands/fixing read as "unloved" in pick-order data but are
    infrastructure (List A's taplands, List D's Shire/Lush Portico).
  - Cutting an underdrafted archetype's support can be backwards — the
    fix for "nobody drafts X" might be *more* X, not less.
  - A cube's job includes trap-shaped and dream-shaped cards; zero
    maindecks ≠ zero value.

## 6. For the tinkerers (samp's section / appendix)

- The reproducible kit: everything regenerates from the three source
  sheets + a TSV of deck links (`refresh.py`; ~/src/cube/roto).
- Precise definitions worth stealing: owner-signature packages;
  2-of-3-agreement edges; halos; companion adjudication (requirement-
  checked, not name-checked); the pod-size normalization trap (9 vs 10
  players makes raw overall picks incomparable — normalize per draft).
- The importable toolkit (`packages.py`): `maindeck_owners`,
  `co_maindeck_counts`, `signature_groups`, `package_edges`, `halos`,
  cut-list generators, and `null_model(iters, seed)` — all pure-stdlib,
  seedable, and reusable on any roto in the LoL template (samp's pods
  export the same shape).
- Open questions this data can answer that we didn't touch (invitation,
  not conclusion):
  - Do packages form earlier or later in the draft over successive
    rotos (learning effects)?
  - Seat-position effects on package access in snake order?
  - Which cards are "package-free" — maindecked 3× with *no* stable
    partners (the true generic goodstuff)?
  - Cross-community comparison: same cube, samp's pods vs ours — do the
    same packages emerge?

## Production notes

- Numbers to re-verify at publish time (data still accruing matches):
  package count (11, min size 3), edges (3 — all same-theme: the two
  Spells packages, two Ramp, two Graveyard), cut-list sizes
  (24/89/16/38, overlap 29/9), null table (11/53/10 vs 5.6/20.4/5.0,
  all p<.0005). §3's rich choice-graph narrative was written at min
  size 2 — at size 3 the forks live mostly in the 2-of-3 and flex
  views, so either present the graph over those or rework §3 around
  the three same-theme edges. Match records don't change packages, but
  any NEW rebuild deck link does — rerun after decks.tsv changes.
- Regenerate everything:
  `python3 refresh.py && python3 packages.py --loose && python3 packages.py --null`.
- No win rates in print. If directional language survives ("this cluster
  kept showing up in winning piles"), keep it to one sentence, sourced to
  "the records," not a number.
