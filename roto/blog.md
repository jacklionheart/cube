# Three Rotos, One Cube

I was recently fortunate enough to participate in some initial
<a href="https://mtg.wiki/page/Rotisserie_Draft">rotisserie drafts</a> of the
<a href="https://www.cubecobra.com/cube/list/0efda005-7243-457e-9d11-875e37d1b768">Lords of Limited cube</a>.
A lot of fun was had by all: lots of love to Ethan, Ben, and Greg of
<a href="https://www.lordsoflimited.com">Lords of Limited</a> for envisioning,
designing, and administering the cube. Today I want to explore what happened
in those drafts by looking at which cards were maindecked together in what
pods.

I put together
<a href="https://docs.google.com/spreadsheets/d/1_w-YcYynXZgzObp13fPUB1q8XNxN6IH7gFkyHgH8E8w/">a spreadsheet</a>
that says for each drafter which cards they maindecked. The unit of analysis
I want to use today is what I am calling a **team**. A **team** of
(non-land) cards is any group of cards, 2 or more, that were maindecked
together in all 3 pods. We can use these cards as a lens towards what are
some of the attractive lanes of the cube.

# The Major Lanes

First, I want to look at teams of size 3 or more -- these are large groups of cards that got played together in all 3 pods. There are 7 such lanes of roughly 3 macro groups: 2 mardu aggro lanes, 3 green lanes, and 2 blue lanes:

{{lanes-viewer}}

## Two Mardu aggro packages

The RW tokens team is the largest team found in the data at 9 cards, while the RB sacrifice team is only 3 cards. I think this mostly reflects the fact that the tokens deck competed for cards with only the sacrifice decks, and only a little bit, so all 3 drafters were able to draft many of the same cards. The sacrifice decks at the three pods were much more different, and could play cards both from the tokens lanes as well as what I will later call the "esper rectangles" lane. While Aviseras did draft Weaponize the Monsters and put sacrifice synergies into his token deck, he didn't draft any of the cards in this "team"; in all 3 pods, the players in each pod drafting each of the two mardu aggro teams were different.


## Three green packages for 2 decks

There are 3 green teams, but they mostly represent two lanes. The three teams are Temur Ramp, Golgari Ramp, and Golgari Graveyard, but the way the cards split into three teams is kinda arbitrary — an artifact of which decks happened to share them. Path to the World Tree and Everything Pizza are basically the same card, and they sit in different teams only because pod 1 split them between two decks. The green players blended these strategies freely: in every pod, just 2 drafters covered all 3 teams, with one of them running two green teams in the same deck.

## Two blue packages

Like with the mardu decks, the blue lanes split fairly cleanly, with two different drafters in each pod for the two "lanes" of spells-matters and looting. The fact that the spells matter team is 5 cards while the looting team is only 3 cards reflects the open-endedness of the blue looting package: the decks using this package across pods were probably the most distinct of any of the packages. The spells package had a wider spectrum than the tokens decks, from tempo to control, but its wider core represents I think a clearer foundation of playing good cheap spells.


# Pairs

{{seat-chart}}

% Every deck in every pod, by its place in the team system. Tinted = owns a
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

## Where the teams live

Add the pairs to the cores and count where the teams actually live:

{{teams-chart}}

% Cards in teams of each color identity (teams of two or more colors).

% The two-card teams, by color:

{{pair-tabs}}

## The most original decks

Flip the question over. Instead of asking what recurred, ask what
<i>never</i> did. There are two ways to be original here. The modest way:
hold few teams — few of your two-card combinations were ever maindecked
together in both other pods. The radical way: contain a large group of
cards that <i>no other deck anywhere</i>, in any pod, ever ran two of
together — a whole ensemble invented at your seat.

### Fewest teams

Count each deck's teams and the field bunches at two:

{{teams-per-deck}}

% Decks by number of teams (pairs or cores) in their maindeck.

Twenty-seven decks hold at least one team. Exactly one holds zero — the
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

Raise a glass. Twenty-seven drafters built decks made of teams —
combinations the other pods discovered too. One did not. Three pods looked
at the same 540 cards and kept drawing the same seven shapes; one drafter
picked up Gyruda and drew a shape nobody else could even reach.
<span class='todo'>[draft — make it yours]</span>

Every other drafter — all 27 of them — built a deck containing at least one
team: some two-card combination that also showed up, together, in both
other pods. FOOMP is the exception. Not one pair of nonland cards in this
deck was ever maindecked together in both other pods. There's a mechanical
reason: the companion is Gyruda, and every single nonland card here has
even mana value — a constraint that pulled this deck out of the card pool
everyone else was drafting from. Twenty-eight decks, one true original.
{{foomp-link}}

{{foomp-gallery}}

% <span class='todo'>TODO: continue — next sections from Jack's outline</span>
