# Presenting Magic data analysis: lessons from three leading practitioners

Studied for the lane report. Sources: [A Bitterblossom (catscandal)](https://abitterblossom.wordpress.com/tag/mtg/),
[Sierkovitz's heuristics article](https://mtgazone.com/data-based-heuristics-for-mtg-arena-drafts/) and
[MKM meta report](https://mtgazone.com/mkm-limited-meta-report/) (his X feed is the same
style compressed), and [Frank Karsten's mana base methodology](https://gist.github.com/teryror/881d60e08480a56043895d3bbb83c374).

## Frank Karsten — the methodology is a feature

1. **State the method before the numbers.** He opens with what was computed,
   how (hypergeometric/simulation), and which evidence supports which claim.
   Readers trust the tables because the machinery is visible.
2. **Tables are lookup tools, not data dumps.** Rows/columns are organized
   around the reader's decision ("my curve, my colors"), never around how the
   data was generated.
3. **Numbers become named thresholds.** "~90% consistency" becomes "you need
   14 sources." A rule of thumb is the deliverable; the table is its receipt.
4. **Caveats are conversational and specific.** "Based on an outdated mulligan
   rule"; "I take this as indication" — honesty about where extrapolation
   starts, embedded in the flow rather than a disclaimers section.
5. **Map numbers onto archetype categories** (aggro/midrange/control) so every
   reader knows which row is *theirs*.

## Sierkovitz — the chart states its finding

1. **Figure titles/captions are findings, not variable names.** "Frequency of
   wheeling dual taplands by pack number" — you learn something from the
   caption alone. Every figure carries "Source: 17Lands.com."
2. **Fixed argument chain:** observation → chart → universal principle →
   strategic application → conditional limitations. The limitation step is
   never skipped ("the size of this effect depends on the card's color").
3. **Cross-validation before claiming a heuristic** — the same trend shown in
   multiple sets before it's called a rule. (Our analog: a pattern seen in
   all three pods, or explicitly flagged as one-pod.)
4. **Anchor stats to playable objects** — card names are links; the reader
   can always get from a number back to the card.
5. **Tier the audience** — comparisons between *neighboring* skill tiers, not
   just "the best vs everyone," so every reader has a next step.

## catscandal — the essay has a voice and a framework

1. **Provocative, personal framing** ("Izzet Doesn't Suck, You Do") — the
   analysis is an argument, not a report. Voice does the work of getting
   skeptics to look at data.
2. **Personal stakes as evidence** — trophy rates, self-set challenges
   (the Niv-Mizzet Challenge) give the data narrative tension.
3. **Named concepts that outlive the article** ("Dynamic Splash Range").
   Naming the framework is half its value. (We already do this: Lanes,
   Flex, Teams, Bangers — surface the glossary.)
4. **Scaffolded complexity** — explicitly "not overwhelming you"; principles
   first, receipts second.
5. **Revisit metrics over time** (Balance Revisited, yearly) — analysis as a
   series, not a one-off. (Our analog: rerun after each future roto.)

## What we applied to the lane report

- Karsten: a "How this works" methodology block (definitions, companion
  adjudication, the null-model receipt, n=3 caveats) and per-chart source
  attribution.
- Sierkovitz: chart titles rewritten as computed findings; card names link
  to Scryfall throughout; limitations kept adjacent to claims.
- catscandal: the Lanes/Flex/Bangers glossary surfaced as the named
  framework up top; prose voice left open for Jack (the essay argument and
  personal stakes are his to write).

## Still open for Jack's prose pass (voice-level, not structural)

- An argumentative thesis title in catscandal's register.
- "The rule:" pull-lines after each section (Karsten's move) — best written
  in your voice once you decide what each section's rule actually is.
- Cross-pod validation language: which patterns appeared in all three pods
  (rule-grade) vs one pod (anecdote-grade).
