# The Lords of Limited Rotisserie Meta

I was recently fortunate enough to participate in some initial
<a href="https://docs.google.com/spreadsheets/d/1i5IK8JKOeZpKZpV27YbqIFVNEkOQZq1rXRJQq-IBwCw/">rotisserie drafts</a> of the
<a href="https://www.cubecobra.com/cube/list/0efda005-7243-457e-9d11-875e37d1b768">Lords of Limited cube</a>.
Thanks to Ethan, Ben, and Greg of
<a href="https://www.lordsoflimited.com">Lords of Limited</a> for envisioning,
designing, and administering the cube. Today I want to explore what happened
in those drafts by looking at which cards were maindecked together in what
pods.

I put together
<a href="https://docs.google.com/spreadsheets/d/1_w-YcYynXZgzObp13fPUB1q8XNxN6IH7gFkyHgH8E8w/">a spreadsheet</a>
that identifies which cards were maindecked by which players. The unit of analysis
I want to use today is what I am calling a **package**. A **package** of
(non-land) cards is any group of cards, 2 or more, that were maindecked
together in all 3 pods. We can use these cards as a lens towards what are
some of the attractive lanes of the cube.

By looking at these cards, I think we can see what I see as the lanes as drafted by the players in these drafts. This was of course just 3 drafts, and already the cube has been majorly redesigned. Nothing here will discuss which decks won, and this offers ~zero predictive power about how future drafts will behave. However, I find it fun to look at what actually happened nonetheless. To skip to the conclusion, when I look at the **packages** that appeared in these drafts, this is what I see:

* 2 Mardu aggro decks
* 2 Green ramp/graveyard decks
* 2 Blue spell/looting decks
* 3 Esper rectangle decks
+ 1 crazy companion

Let me walk you through it!

# The Major Lanes

First, let's look at packages of size 3 or more -- these are large groups of cards that got played together in all 3 pods. There are 7 such packages of roughly 3 macro lanes: 2 mardu aggro packages, 3 green packages, and 2 blue packages.

Before we look at any individual package, let's review what this means. These are sets of cards that were maindecked together, in the same deck, in the three pods. Cards that are more linear are more likely to show up here, since they are more likely to be drafted only by someone in a specific lane. However, this is only three drafts, and most cards are sometimes contested, so there is quite a bit of randomness in which cards happened to co-occur in this particular set of drafts.

However, the more cards that really do tend together, the more likely any subset of that group of cards is going to show up in this way. Therefore, while the presence of any specific card here means fairly little, the existence of some package in some general area is somewhat more robust.

{{lanes-viewer}}

## Two Mardu aggro packages

The RW tokens package is the largest package found in the data at 9 cards, while the RB sacrifice package is only 3 cards. I think this mostly reflects the fact that the tokens deck competed for cards with only the sacrifice decks, and only a little bit, so all 3 drafters were able to draft many of the same cards. The sacrifice decks at the three pods were much more different, and could play cards both from the tokens lanes as well as what I will later call the "esper rectangles" lane. While Aviseras did draft Weaponize the Monsters and put sacrifice synergies into his token deck, he didn't draft any of the cards in this "package"; in all 3 pods, the players in each pod drafting each of the two mardu aggro packages were different.


## Three green packages for 2 decks

There are 3 green packages, but they represent two lanes. The three packages are Temur Ramp, Golgari Ramp, and Golgari Graveyard. The way the cards split into three packages is kinda arbitrary here. Each pod had only 2 drafters splitting these three packages.

As a group though, they demonstrate the two main ways for green to create an inevitable board presence: through ramp and the graveyard, and represent the two mana bases people are using to do it: temur and golgari.

## Two blue packages

Like with the mardu decks, the blue lanes split fairly cleanly, with two different drafters in each pod for the two "lanes" of spells-matters and looting. The fact that the spells matter package is 5 cards while the looting package is only 3 cards reflects the open-endedness of the blue looting package: the decks using this package across pods were probably the most distinct of any of the packages. The spells package had a wider spectrum than the tokens decks, from tempo to control, but its wider core represents I think a clearer foundation of playing good cheap spells.


# Pairs

{{seat-chart}}

% Every deck in every pod, by its place in the package system. Tinted = owns a
% core (its family's color). Dashed white = Rectangles deck, with the family
% its bonds lean toward. Gray = the wildcard.

Those 7 lanes describe 6 of the drafters at each pod.  There were 2 pods of 9 people and 1 of 10 people, so this leaves 3-4 drafters per pod still undescribed by these major lanes. To answer this, I want to now look at all the **pairs** that were maindecked together in all 3 pods.

{{pair-table}}

## Pairs and the macro lanes

Now let's start to look at pairs and ask: when were they played together with the bigger "lanes"? By definition, none of these pairs were *always* played in the same lane, as they otherwise would be included in that lane. However, if we look at our 7 packages as representing 3 macro lanes, we can ask, how often do they stay within the 3 macro lanes?

There are 14 such pairs. Of those, 2 were always within a macro lane:

{{pairs-in-lane}}

and 5 were drafted within one macro lane 2x, and in the third pod were drafted by one of the drafters outside one of the 7 "lanes" we've currently explored:

{{pairs-contested}}

There are 7 pairs left. These 7 were drafted by at most one drafter in the lanes we've currently explored. They reveal what I would call the 4th macro lane, Esper Rectangles:

{{pairs-rect-table}}

Is it fair to call this a lane? The cards make the case themselves: rooms,
cases, sagas, omens, auras, adventures — white, black, and blue non-creature
cardboard. Rectangles. The decks make it stronger: of the 21 deck-slots
these 7 pairs occupy, 17 belong to decks outside the seven lanes, and the
same names keep coming up — BladeTheKing hosted four of the seven pairs,
Balbadorf and bengolds three each. The honest counterargument is that no
three of these cards ever assembled in one deck across all three pods, the
way the real lanes did — the bonds kept forming pairwise and never found
their third card. Call it the eighth core that never quite assembled, or
the lane the cube keeps offering that nobody has fully accepted yet.
<span class='todo'>[draft — make it yours]</span>

{{rectangles-gallery}}

## Where the packages live

Add the pairs to the cores and count where the packages actually live:

{{teams-chart}}

% Cards in packages of each color identity (packages of two or more colors).

% The two-card packages, by color:

{{pair-tabs}}

## The most original decks

Flip the question over. Instead of asking what recurred, ask what
<i>never</i> did. There are two ways to be original here. The modest way:
hold few packages — few of your two-card combinations were ever maindecked
together in both other pods. The radical way: contain a large group of
cards that <i>no other deck anywhere</i>, in any pod, ever ran two of
together — a whole ensemble invented at your seat.

### Fewest packages

Count each deck's packages and the field bunches at two:

{{teams-per-deck}}

% Decks by number of packages (pairs or cores) in their maindeck.

Twenty-seven decks hold at least one package. Exactly one holds zero — the
gray seat from the chart, and it gets the full sendoff below.

### The largest unique ensemble

The radical way: for each deck, the largest group of cards no other deck
ever ran any two of — its unique ensemble, the part of the deck that was
genuinely invented at that table. (The three Yorion decks sit this one out:
a 60-card maindeck gets extra room for unique pairs just by being big.)
Core ownership turns out to be the opposite of originality: core decks
average 9.9 unique cards, decks outside the core system 12.5.

{{originality-hist}}

% Decks by size of their largest unique ensemble (nonland cards, no pair
% shared with any other deck). Yorion decks excluded.

The record is 16, and it's a tie.

{{originality-winners}}

## The FOOMP deck

Raise a glass. Twenty-seven drafters built decks made of packages —
combinations the other pods discovered too. One did not. Three pods looked
at the same 540 cards and kept drawing the same seven shapes; one drafter
picked up Gyruda and drew a shape nobody else could even reach.
<span class='todo'>[draft — make it yours]</span>

Every other drafter — all 27 of them — built a deck containing at least one
package: some two-card combination that also showed up, together, in both
other pods. FOOMP is the exception. Not one pair of nonland cards in this
deck was ever maindecked together in both other pods. There's a mechanical
reason: the companion is Gyruda, and every single nonland card here has
even mana value — a constraint that pulled this deck out of the card pool
everyone else was drafting from. Twenty-eight decks, one true original.
{{foomp-link}}

{{foomp-gallery}}

% <span class='todo'>TODO: continue — next sections from Jack's outline</span>
