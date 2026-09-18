# Rotisserie Drating the The Lords of Limited Cube

I recently had the good fortune to play in some initial
🍗 <a href="https://docs.google.com/spreadsheets/d/1i5IK8JKOeZpKZpV27YbqIFVNEkOQZq1rXRJQq-IBwCw/">rotisserie drafts</a> 🍗 of the
<a href="https://www.cubecobra.com/cube/list/0efda005-7243-457e-9d11-875e37d1b768">Lords of Limited cube</a>.
Thanks to Ethan and Ben of
<a href="https://www.lordsoflimited.com">Lords of Limited</a>, and Greg from their Discord, for envisioning,
designing, and administering the cube. Here I explore those drafts by
asking which cards were maindecked together in which pods.

I put together
<a href="https://docs.google.com/spreadsheets/d/1_w-YcYynXZgzObp13fPUB1q8XNxN6IH7gFkyHgH8E8w/">a spreadsheet</a>
of which cards each drafter maindecked. To do this analysis, I define a
**package**:

<div class='defn'><div class='dlabel'>Definition</div>
<div class='deq'><span class='dterm'>package</span>
<span class='dsym'>≔</span>
<span class='dbody'>a set of 2 or more non-land cards that were all drafted and maindecked together by the same drafter in all 3 pods</span></div></div>

Packages are a pattern in how drafters build decks in this cube. Throughout this post I will use **lane** for a strategy; a package is the fingerprint a lane leaves in the data.

One thing you will not find here is win rates. A package records what
drafters wanted to build, not whether it worked; deck strength, play
skill, and matchup luck are all invisible to this analysis. Nothing
here is a power ranking of the lanes or of the drafters.
<span class='todo'>[draft — make it yours]</span>

To skip to the conclusion, here is what I see at each pod:

* {{mana:R}} 2 Red aggro decks
* {{mana:G}} 2 Green ramp/graveyard decks
* {{mana:U}} 2 Blue spells/looting decks
* {{mana:W}} 3 White Rectangles decks
* <span class='fdot'>●</span> 1 crazy companion

How to read the chart below: every drafter gets a seat, colored by the
strategy their deck served — we will define everything as we go.
Throughout this post, hover any drafter's name to preview their deck.
<span class='todo'>[draft — make it yours]</span>

{{seat-chart}}

% Every drafter at every pod, in draft order. Tinted = owns one of the 7
% big packages, colored by lane. Cream = White Rectangles.
% Purple = the companion deck.

Let me walk you through it!

# The Well-Grooved Lanes

{{lanes-viewer}}

% The 7 big packages — packages of size 3 or more — grouped by lane.
% Click a package to see its cards.

First, the packages of size 3 or more. There are 7, and they fall into 3 groups.

A caveat before you extract any heuristics: this is archaeology, not a
draft guide. This was just 3 pods, and the cube has already been
majorly redesigned — partly in response to these very drafts — so none
of this predicts the next one. Read the lanes as a record of what one
metagame discovered, not as advice.
<span class='todo'>[draft — make it yours]</span>

These cards:
- were drafted and maindecked in every pod. They are considered "good cards" by the community, at least in their current decks.
- are all selected by the same drafters. They play well in whatever strategy is shared by all of their drafters.
- are more likely to be specific to those strategies, since they were never demonstrated to be attractive to any other strategy.

Which cards specifically show up in these packages is a bit arbitrary; again, we only have 3 pods here. However, the lanes from which those cards
are drawn are anything but arbitrary. The larger and clearer the lane, the more likely two cards are to be desired together, and the more likely it is that *some* subset of that strategy ends up in a package.

## Two Red aggro packages

The RW tokens package, at 9 cards, is the largest in the data; the RB
sacrifice package has only 3. The difference is competition. Only the
sacrifice decks contested the tokens cards, and only lightly, so all 3
tokens drafters took many of the same cards. The sacrifice decks varied
far more, borrowing from both the tokens package and what I will call the
"White Rectangles" lane. {{drafter:2:Aviseras}} drafted Weaponize the Monsters and
built sacrifice synergies into his tokens deck, but took none of this
particular package; in all 3 pods, different drafters drafted the two packages.

### {{mana:WR}} Tokens

{{core-tokens}}

### {{mana:BR}} Sacrifice

{{core-sac}}

## Three Green packages for 2 decks

There are 3 green packages — Temur Ramp, Golgari Ramp, and Golgari
Graveyard — but they represent just two strategies — each pod had only 2 drafters drafting the 3 packages.

Together they show green's two ways of building an inevitable board —
ramp and the graveyard — and the two mana bases used to do it: Temur and
Golgari. One is the Temur ramp package, another the Golgari graveyard package, and the third is sort of a hybrid of the two.

### {{mana:URG}} Temur Ramp

{{core-ramp-urg}}

### {{mana:BG}} Golgari Graveyard

{{core-graveyard}}

### {{mana:BG}} Golgari Ramp

{{core-ramp-bg}}

## Two Blue packages

As with Red, the Blue lane splits cleanly: in each pod, different
drafters took spells-matters and looting cards. The spells package has 5 cards,
looting only 3 — the gap reflects looting's open-endedness; its decks
were the most distinct of any package's. The spells decks ranged from
tempo to control, wider than tokens, but their larger package marks a
clearer foundation — good cheap spells — than that of the mysterious blue tempo deck.

### {{mana:UR}} Spells

{{core-spells}}

### {{mana:U}} Looting

{{core-discard}}

# The 4th Lane: White Rectangles

Those 7 packages describe 6 drafters at each pod. That's all that shows up when you look for packages of size 3 or more.
However, if you look at the **pairs**, packages of size 2, you can find the 4th lane: White Rectangles, which covers all but 1 of the other drafters (we will get to them, eventually).


Half of the pairs showed up either only or mostly in decks that also played big packages. These pairs can be thought of as contested cards within the 3 lanes above: in most pods
they went to those lanes, but for 5 of the 7, one pod's White Rectangles drafter took them instead. But the other half were drafted mostly by decks outside the 3 established lanes. If you look at these 7 pairs, they
are all clearly "rectangles" cards, mostly W and touching U and B.

{{rectangles-gallery}}

% The 7 pairs that define the White Rectangles lane.

The contested pairs, for the record:

{{fam-pairs-viewer}}

% Each contested pair with its three homes: pip labels mark package
% owners; italic names are the rectangles drafters who fought for them.

What's different about the White Rectangles lane is that it fights with everyone. While the cards that define the lane are all Esper cards, these cards can be played alongside any of the other three lanes.
For the most part, the synergistic pairs that are sought out by the Blue, Red, and Green lanes are disjoint, and they do not fight with each other. But they all want to play some rectangles cards, and a rectangles
shell can be made to play well with cards from any of the three other lanes.

Rectangles decks borrow elements from the 3 other lanes. Most borrow primarily from one; some are more complex mixtures. Adding 3 rectangles drafters to a pod is kind of like adding another drafter to each of the other lanes, but mixed rather than distilled.

{{rect-compete-chart}}

% Cross-pod shared cards between each rectangles deck and the
% {{mana:R}} aggro, {{mana:G}} green, and {{mana:U}} blue lanes.
% Rectangles-to-rectangles overlap (each deck's largest) not shown.

## Gyruda

Which brings us to the purple seat. In a statistical sense, it would
be reasonable to say {{drafter:3:FOOMP}} drafted the most unique deck of all the drafters.
FOOMP's is the only deck in all three
pods with <i>no</i> package: not one pair of its non-land cards was
maindecked together in both other pods.

The other 27 drafters all shared at least one pair with the other two pods:

{{teams-per-deck}}

% Decks by number of maindeck cards that belong to any (maximal) package.

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

## Appendix: 

Everything in this post regenerates from
<a href="https://docs.google.com/spreadsheets/d/1_w-YcYynXZgzObp13fPUB1q8XNxN6IH7gFkyHgH8E8w/">this spreadsheet</a>
and a few hundred lines of Python in
<a href="https://github.com/jacklionheart/cube/tree/main/roto">the repo</a>.
