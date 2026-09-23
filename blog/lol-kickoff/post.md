# Rotisserie Drafting the Lords of Limited Cube

% Jack Heart · September 2026

I recently had the good fortune to play in some initial
🍗 <a href="https://docs.google.com/spreadsheets/d/1i5IK8JKOeZpKZpV27YbqIFVNEkOQZq1rXRJQq-IBwCw/">rotisserie drafts</a> 🍗 of the
<a href="https://www.cubecobra.com/cube/list/0efda005-7243-457e-9d11-875e37d1b768">Lords of Limited cube</a>.
Thanks to Ethan and Ben of
<a href="https://www.lordsoflimited.com">Lords of Limited</a>, and Greg from their Discord, for envisioning,
designing, and administering the cube. We drafted 3 pods (of 9, 9, and 10) simultaneously, and here I explore those drafts by
asking which cards were <a href="https://docs.google.com/spreadsheets/d/1_w-YcYynXZgzObp13fPUB1q8XNxN6IH7gFkyHgH8E8w/">maindecked together</a> in all 3 pods. First, let's define a
**package**:

<div class='defn'><div class='dlabel'>Definition</div>
<div class='deq'><span class='dterm'>package</span>
<span class='dsym'>≔</span>
<span class='dbody'>a set of 2 or more non-land cards that were all drafted and maindecked together by the same drafter in all 3 pods</span></div></div>

Packages are a pattern in how drafters built decks during this first run of the cube. Packages can be large: those of size 3 or more offer a fingerprint of a strategic lane used in all the pods. They can also be small: packages of size 2 present cards that play well together but could be used in more different strategies in the different pods.

We will not be looking at win rate data today. This analysis is just asking what the common patterns were in how people built decks, not which ones were most successful. There are many reasons this would not be fruitful, such as small sample size and an evolving metagame and cube design. Most importantly though, our intention is to celebrate and explore; to ask questions rather than answer them.

To skip to the conclusion, by looking at the drafts through the lens of packages, here is how the package lens sorts the pods:

* {{mana:R}} 2 Red aggro decks
* {{mana:G}} 2 Green ramp/graveyard decks
* {{mana:U}} 2 Blue spells/looting decks
* {{mana:W}} 3 White Rectangles decks
* <span class='fdot'>●</span> 1 crazy companion

Using those categories, we can map the pods as drafted:
<span class='todo'>[draft — make it yours]</span>

{{seat-chart}}

% Every drafter at every pod, in draft order.
% Purple = the companion deck that stands out like a giant kraken in this analysis.

Let me walk you through it!

# The Well-Grooved Lanes

{{lanes-viewer}}

% The 7 big packages — packages of size 3 or more — grouped by lane.
% Click a package to see its cards.

First, the packages of size 3 or more. There are 7, and they fall into 3 groups.

<span class='todo'>[draft — make it yours]</span>

As a reminder, the definition of package means these cards:
- were drafted and maindecked in every pod. They were considered "good cards" by the drafters, at least in their current decks.
- are all selected by the same drafters. They play well in whatever strategic lane is shared by all of their drafters.
- are more likely to be specific to those strategies, since they were never "stolen" by drafters in a different strategic lane.

Which cards specifically show up in these packages is a bit arbitrary; again, we only have 3 pods here. However, the lanes from which those cards are drawn are anything but arbitrary. The larger and clearer the lane, the more likely two cards are to be desired together, and the more likely it is that *some* subset of that strategy ends up in a package. These cards point to an overall strategy, but they aren't necessarily more valuable in that strategy than cards which are missing (and may have been contested by other drafters).

## 2 Red aggro packages

The RW tokens package, at 9 cards, is the largest here; the RB
sacrifice package has only 3. The difference is competition. Only the
sacrifice decks contested the tokens cards, and only lightly, so all 3
tokens drafters took many of the same cards. The sacrifice decks varied
far more, borrowing from both the tokens package and what I will call the
"White Rectangles" lane. {{drafter:2:Aviseras}} drafted Weaponize the Monsters and
built sacrifice synergies into his tokens deck, but took none of this
particular package; in all 3 pods, different drafters drafted the 2 packages.

### {{mana:WR}} Tokens

{{core-tokens}}

### {{mana:BR}} Sacrifice

{{core-sac}}

## 3 Green packages for 2 decks

There are 3 green packages — Temur Ramp, Golgari Ramp, and Golgari
Graveyard — but they represent just 2 "lanes": each pod had only 2 drafters drafting the 3 packages, with 1 drafter per pod drafting 2 of the 3 packages.

Together they show green's 2 ways of building an inevitable board —
ramp and the graveyard — and the 2 mana bases used to do it: Temur and
Golgari, but at each pod the green decks staked out slightly different subsets of this space.

### {{mana:URG}} Temur Ramp

{{core-ramp-urg}}

### {{mana:BG}} Golgari Graveyard

{{core-graveyard}}

### {{mana:BG}} Golgari Ramp

{{core-ramp-bg}}

## 2 Blue packages

As with Red, the Blue lane splits cleanly: in each pod, different
drafters took spells-matters and looting cards. The spells package has 5 cards,
looting only 3 — the gap reflects looting's open-endedness; its decks
were the most distinct of any package's. The spells decks ranged from
tempo to control, wider than tokens, but their larger package marks a
clearer foundation — good cheap spells — than that of the infamously mysterious blue tempo deck.

### {{mana:UR}} Spells

{{core-spells}}

### {{mana:U}} Looting

{{core-discard}}

# Pairs and the 4th Lane: White Rectangles

Those 7 packages account for 6 drafters at each pod. That's all that shows up when you look for packages of size 3 or more.
However, if you look at the **pairs**, packages of size 2, you can find the 4th lane: White Rectangles, which covers all but 1 of the other drafters (to whom we will get, eventually).

To find the white rectangles lane, we have to organize the pairs into 2 different groups. There were 14 pairs -- 14 pairs of cards that were maindecked together in all 3 pods without being part of a larger package. Of those, half the pairs were drafted primarily or exclusively by the unaccounted-for drafters, drafters who did not draft any of the larger packages. These cards are mostly W, touching U and B, and generate lots of extra tokens. Each pair plays particularly well together, but overall they are quite modular, and could be combined with not only many of the other pairs here but also the packages above or other individual cards. What's different about the White Rectangles lane is that it fights with everyone.

{{rectangles-gallery}}

Rectangles decks borrow elements from the 3 other lanes. Most borrow primarily from one; some are more complex mixtures. Adding 3 rectangles drafters to a pod is kind of like adding another drafter to each of the other lanes, but mixed rather than distilled.

{{rect-compete-chart}}

% Cross-pod shared cards between each rectangles deck and the
% {{mana:R}} aggro, {{mana:G}} green, and {{mana:U}} blue lanes.
% Rectangles-to-rectangles overlap (each deck's largest) not shown.

So those 7 pairs define the White Rectangles lane, but what about the other pairs? The remaining 7 pairs were drafted primarily or exclusively by drafters from 1 of the 3 other lanes. Unlike White Rectangles, the synergistic pairs that are sought out by the Blue, Red, and Green lanes are disjoint. No pair was ever drafted by drafters from 2 of the 3 non-rectangles lanes across different pods.

{{fam-pairs-viewer}}

% Each contested pair with its three homes: pip labels mark package
% owners; italic names are the rectangles drafters who fought for them.

## Gyruda

Having now described 9 drafters at each pod, it is now time to talk about that crazy companion deck. From this lens of packages, one might say {{drafter:3:FOOMP}} drafted the most unique deck of all the drafters.
FOOMP's is the only deck in all three
pods with <i>no</i> package: not one pair of its non-land cards was
maindecked together in both other pods. The other 27 drafters all shared at least 1 pair with the other 2 pods:

{{teams-per-deck}}

% Decks by number of maindeck cards that belong to any package.

There's a mechanical reason for this: FOOMP's deck has a Gyruda companion. In my opinion, it is
an awesome statistical artifact validating how companions make deckbuilding truly unique.

{{foomp-link}}

{{foomp-gallery}}

% FOOMP's maindeck — every card an even mana value, per Gyruda.

## The most original decks

FOOMP wins one definition of "most original": no pair shared with both
other pods. But I explored a second definition: which decks had the
largest set of cards with no pair as a subset -- i.e., no 2 of its cards were ever maindecked together in any other deck.

The biggest such set of all belongs to {{deck:3:ColdBrewNate}} — 18
of its 37 non-land cards:
<span class='todo'>[draft — make it yours]</span>

{{ensemble-cbn}}

But ColdBrewNate had a cheat sky noodle: a Yorion companion. The record for a 40-card deck is 16 — a tie between
Mark and tox 🍉:
<span class='todo'>[draft — make it yours]</span>

{{originality-hist}}

% Decks by size of their largest unique ensemble (non-land cards, no pair
% shared with any other deck). Yorion decks excluded.

{{deck:1:Mark}}: 16 of its 24 non-land cards did not co-occur elsewhere:

{{ensemble-mark}}

{{deck:2:tox 🍉}}: likewise 16 of 24 — a completely different sixteen:

{{ensemble-tox}}

## Bangers

I want to leave you with a list of bangers. Not every card that was maindecked in all 3 pods joined a package.

<div class='defn'><div class='dlabel'>Definition</div>
<div class='deq'><span class='dterm'>banger</span>
<span class='dsym'>≔</span>
<span class='dbody'>a card that was maindecked in all 3 pods but is
part of no package</span></div></div>

These are the generically good cards of the format: everyone wants
them, and they can be used by multiple strategies even if they fit best into one lane. There are 48
of them, led by white.
<span class='todo'>[draft — make it yours]</span>

% The 48 bangers, tabbed by color.

{{bangers-gallery}}
