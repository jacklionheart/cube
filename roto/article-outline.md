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

## 2. The 25 packages, labeled

- Table: P#, size, suggested archetype label (MY DRAFTS — relabel in your
  own words), members. Order by component then size.

| P# | n | draft label (rewrite) | cards |
|----|---|--------------------|-------|
| P1 | 10 | Boros go-wide | Dog Walker, Forbidden Friendship, Inspiring Overseer, On the Job, Painter's Studio, Rally at the Hornburg, Resolute Reinforcements, Sacred Foundry, Salt Road Packbeast, Shock Brigade |
| P2 | 8 | UR spells velocity | Consider, Demon Bolt, Expressive Iteration, Jwari Disruption, Mystic Sanctuary, Scalding Tarn, Think Twice, Thundering Falls |
| P3 | 6 | 5c Fires ramp | Biomechan Engineer, Courier's Briefcase, Fires of Invention, Hunter's Talent, Path to the World Tree, Writhing Chrysalis |
| P4 | 5 | WU spells / Acuity | Dovin's Acuity, Flooded Strand, Hallowed Fountain, Pyrrhic Strike, Raugrin Triome |
| P5 | 5 | G self-mill value | Eccentric Farmer, Generous Ent, Rise of the Varmints, Satyr Wayfinder, Spider Spawning |
| P6 | 4 | 5c Pizza shell | Cloud of Darkness, Everything Pizza, Evolving Wilds, Marshals' Pathcruiser |
| P7 | 3 | WB aristocrat drain | Bastion of Remembrance, Shattered Landscape, Voice of Victory |
| P8 | 3 | WB nightmare enchants | Hopeless Nightmare, Michiko's Reign of Truth, Shadowy Backstreet |
| P9 | 3 | U tempo-counters | Censor, Quench, Shoreline Looter |
| P10 | 3 | Sacrifice core | Deadly Dispute, Marionette Apprentice, Mayhem Devil |
| P11 | 3 | BG grave payoffs | Broodspinner, Disruptive Stormbrood, Verdant Catacombs |
| P12 | 2 | WB drain bodies | Cat Collector, Ruthless Lawbringer |
| P13 | 2 | Yorion blink flag | Aang the Last Airbender, Yorion |
| P14 | 2 | WU enchant payoff | Citizen's Crowbar, Dance of the Manse |
| P15 | 2 | W tempo-auras | Essence Reliquary, The Princess Takes Flight |
| P16 | 2 | W builders | Builder's Talent, The Birth of Meletis |
| P17 | 2 | Blink fodder | Adagia Windswept Bastion, Pilgrim's Eye |
| P18 | 2 | U oddments | Cryogen Relic, Fear of Isolation |
| P19 | 2 | U counters | Refute, The Modern Age |
| P20 | 2 | U card flow | Hieroglyphic Illumination, Lórien Revealed |
| P21 | 2 | Sac vehicles | Phantom Train, Piggy Bank |
| P22 | 2 | Treasure aggro | Magda the Hoardmaster, Torch the Tower |
| P23 | 2 | Spells satellite | Perilous Landscape, Thunder Magic |
| P24 | 2 | UB tempo pair | Haunt the Network, Polluted Delta |
| P25 | 2 | UR spells lands | Steam Vents, Xander's Lounge |

- Note for prose: sizes are power-law-ish — one 10-card monolith (P1
  stayed intact through *three different drafters*), a few mid cores,
  many pairs. The pairs are mostly *satellites* of bigger things (next
  section shows how).

## 2b. Are the packages real? (the null model)

- The skeptic's question, answered before it's asked (this is the samp
  paragraph, and it's also the best Ben insurance in the piece because it
  *limits* the claim rather than inflating it).
- Method, one sentence: keep everyone's exact picks, replace each
  maindeck with a random same-size subset of that player's own pool,
  re-count packages, 2,000 times (`packages.py --null`).
- Results (observed vs. chance):
  - packages (size ≥2): **25 observed** vs 15.7 ± 2.6 by chance (p ≈ .002)
  - cards inside packages: **81** vs 40.6 ± 6.1 — *never reached once in
    2,000 random worlds* (p < .0005)
  - largest package: **10** vs 5.0 ± 1.0 — chance never built one bigger
    than 9 (p < .0005)
- The honest two-sided reading (use this framing): the *card mass* and
  the *big cores* are unambiguous deckbuilding signal — but a random
  world still produces ~15 "packages," so any individual 2-card pair
  could be coincidence. Big packages: trust. Pairs: hold loosely.
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
  group count (25), edge count (19), component count (8), list sizes
  (24/89/16/38, overlap 29/9), null-model table (25/81/10 vs
  15.7/40.6/5.0). Note: match records don't change packages, but any
  NEW rebuild deck link does — rerun after decks.tsv changes.
- Regenerate everything:
  `python3 refresh.py && python3 packages.py --loose && python3 packages.py --null`.
- No win rates in print. If directional language survives ("this cluster
  kept showing up in winning piles"), keep it to one sentence, sourced to
  "the records," not a number.
