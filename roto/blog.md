# The Lords of Limited Rotisserie Meta

I recently had the good fortune to play in some initial
<a href="https://docs.google.com/spreadsheets/d/1i5IK8JKOeZpKZpV27YbqIFVNEkOQZq1rXRJQq-IBwCw/">rotisserie drafts</a> of the
<a href="https://www.cubecobra.com/cube/list/0efda005-7243-457e-9d11-875e37d1b768">Lords of Limited cube</a>.
Thanks to Ethan and Ben of
<a href="https://www.lordsoflimited.com">Lords of Limited</a>, and Greg from their Discord, for envisioning,
designing, and administering the cube. Here I explore those drafts by
asking which cards were maindecked together in which pods.

I put together
<a href="https://docs.google.com/spreadsheets/d/1_w-YcYynXZgzObp13fPUB1q8XNxN6IH7gFkyHgH8E8w/">a spreadsheet</a>
of which cards each player maindecked. To do this analysis, I define a
**package**:

<div class='defn'><div class='dlabel'>Definition</div>
<div class='deq'><span class='dterm'>package</span>
<span class='dsym'>≔</span>
<span class='dbody'>a set of 2 or more non-land cards that were all drafted and maindecked together by the same drafter in all 3 pods</span></div></div>

Packages are a pattern in how people build decks in this cube. This was just 3 drafts, and the cube has already been majorly redesigned.
Nothing here discusses which decks won, and it offers ~zero predictive
power about future drafts. Still, it's fun to look at what happened! To
skip to the conclusion, here is what I see at each pod:

* {{mana:R}} 2 Red aggro decks
* {{mana:G}} 2 Green ramp/graveyard decks
* {{mana:U}} 2 Blue spell/looting decks
* {{mana:W}} 3 White rectangle decks
* <span class='fdot'>●</span> 1 crazy companion

{{seat-chart}}

% Every drafter at every pod, in draft order. Tinted = owns one of the 7
% big packages, colored by macro lane. Cream = White Rectangles.
% Purple = the companion deck.

Let me walk you through it!

# The Well-Grooved Lanes

{{lanes-viewer}}

First, the packages of size 3 or more. There are 7, and they fall into 3 groups.

These cards:
- were drafted and maindecked in every pod. They are considered "good cards" by the community, at least in their current decks.
- are all selected by the same drafters. They play well in whatever strategy is shared by all of their drafters.
- are more likely to be specific to those strategies, since they were never demonstrated to be attractive to any other strategy.

Which cards specifically show up in these packages is a bit arbitrary; again, we only have 3 drafts here. However, the lanes from which those cards
are drawn are anything but arbitrary. The larger and clearer the lane, the more likely two cards are to be desired together, and the more likely it is that *some* subset of that strategy ends up in a package.

## Two Red aggro packages

The RW tokens package, at 9 cards, is the largest in the data; the RB
sacrifice package has only 3. The difference is competition. Only the
sacrifice decks contested the tokens cards, and only lightly, so all 3
tokens drafters took many of the same cards. The sacrifice decks varied
far more, borrowing from both the tokens lane and what I will call the
"white rectangles" lane. Aviseras drafted Weaponize the Monsters and
built sacrifice synergies into his token deck, but took none of this
particular package; in all 3 pods, different players drafted the two packages.

### {{mana:WR}} Tokens

{{core-tokens}}

### {{mana:BR}} Sacrifice

{{core-sac}}

## Three green packages for 2 decks

There are 3 green packages — Temur Ramp, Golgari Ramp, and Golgari
Graveyard — but they represent just two lanes -- each pod had just 2 drafters drafting the 3 packages.

Together they show green's two ways of building an inevitable board —
ramp and the graveyard — and the two mana bases used to do it: Temur and
Golgari. One package is the "temur ramp package", another is the "golgari graveyard package", and the third is sort of a hybrid/mixture.

### {{mana:URG}} Temur Ramp

{{core-ramp-urg}}

### {{mana:BG}} Golgari Graveyard

{{core-graveyard}}

### {{mana:BG}} Golgari Ramp

{{core-ramp-bg}}

## Two blue packages

As with red, the blue lanes split cleanly: in each pod, different
drafters took spells-matters and looting cards. The spells package has 5 cards,
looting only 3 — the gap reflects looting's open-endedness; its decks
were the most distinct of any package's. The spells decks ranged from
tempo to control, wider than tokens, but their larger core marks a
clearer foundation — good cheap spells — than the core of the mysterious looting deck.

### {{mana:UR}} Spells

{{core-spells}}

### {{mana:U}} Looting

{{core-discard}}

# The 4th Lane: White Rectangles

Those 7 lanes describe 6 drafters at each pod. That's all that shows up when you look for packages of size 3 or more.
However, if you look at the **pairs**, packages of size 2, you can find the 4th lane: White Rectangles, which covers all but 1 of the other drafters (to whom we will get, eventually).


Half of the pairs showed up either only or mostly in decks that also played larger packages. These pairs can be thought of as contested cards within the 3 lanes above: in most pods
they went to those lanes, but for five of the seven, one pod's White Rectangles drafter took them instead. But half of the pairs were drafted mostly by decks outside the 3 established lanes. If you look at these 7 pairs, they
are all clearly "rectangles" cards, mostly W and touching U and B.

{{rectangles-gallery}}

The contested pairs, for the record: 

{{fam-pairs-viewer}}

What's different about the White Rectangles lane is that it fights with everyone. While the cards that define the lane are all esper cards, these cards can be played alongside any of the other three lanes.
For the most part, the synergistic pairs that are sought out by the Blue, Red, and Green lanes are disjoint, and they do not fight with each other. But they all want to play some rectangles cards and a rectangles
core can be made to play well with cards from any of the three other lanes.

Rectangles decks borrow elements from the 3 other lanes. Many of the decks borrow primarily from one other lane, but some decks have more complex mixtures. Adding 3 rectangles drafters to a pod is kind of like adding another drafter to each of the other lanes, but mixed rather than distilled.

{{rect-compete-chart}}

% Cross-pod shared cards between each rectangles deck and the
% {{mana:R}} aggro, {{mana:G}} green, and {{mana:U}} blue lanes.
% Rectangles-to-rectangles overlap (each deck's largest) not shown.

## Gyruda

Which brings us to the purple seat. In a statistical sense, it would 
be reasonable to say FOOMP drafted the most unique deck of all the drafters.
FOOMP's is the only deck in all three
pods with <i>no</i> package: not one pair of its nonland cards was 
maindecked together at both other pods.

The other 27 drafters all shared at least one pair with the other two pods:

{{teams-per-deck}}

% Decks by number of packages (pairs or cores) in their maindeck.

There's a mechanical reason for this: FOOMP's deck has a Gyruda companion. In my opinion, it is
an awesome statistical artifact validating how companions make deckbuilding truly unique.

{{foomp-link}}

{{foomp-gallery}}

## The most original decks

FOOMP wins one definition of "most original": no pair shared with both
other pods. But I explored as a second definition: which decks had the 
largest set of cards which had no pair as a subset -- i.e., no 2 of its cards were ever maindecked together in any other deck.

The biggest such set of all belongs to {{deck:3:ColdBrewNate}} — 18
of its 37 nonland cards:
<span class='todo'>[draft — make it yours]</span>

{{ensemble-cbn}}

But ColdBrewNate had a cheat sky noodle: Yorion companion. The record for a 40-card deck is 16 — a tie between
Mark and tox 🍉:
<span class='todo'>[draft — make it yours]</span>

{{originality-hist}}

% Decks by size of their largest unique ensemble (nonland cards, no pair
% shared with any other deck). Yorion decks excluded.

{{deck:1:Mark}}: 16 of its 24 nonland cards did not co-occur elsewhere:

{{ensemble-mark}}

{{deck:2:tox 🍉}}: 16 of its 24 nonland did not co-occur elsewhere:

{{ensemble-tox}}

## Bangers

Not every card that was maindecked in all 3 pods joined a package.

<div class='defn'><div class='dlabel'>Definition</div>
<div class='deq'><span class='dterm'>banger</span>
<span class='dsym'>≔</span>
<span class='dbody'>a card that was maindecked in all 3 pods but is
part of no package</span></div></div>

These are the generically good cards of the format: everyone wants
them, and they tie themselves to no particular strategy. There are 48
of them, led by white.
<span class='todo'>[draft — make it yours]</span>

{{bangers-gallery}}
