# Samp Roto s4 — the components

<!-- Preserved in-progress text from the old Python file: me -->

% {{pod-count}} pods · {{deck-count}} known maindecks · nonland cards.
% Working draft: the pieces first, prose later. Win rates shown
% throughout, mostly not yet interpreted.

## Sacrifice <span class='meta' style='display:inline'>· {{sacrifice-colors}} package</span>

% Core = {{sacrifice-size}} cards (Jaccard-0.6 co-occurrence component) · deck set = {{sacrifice-deck-count}} decks running ≥{{sacrifice-threshold}} core cards · pooled {{sacrifice-record}}. Card caption: backbone depth · inclusion · that card's deck WR.

{{sacrifice-cards}}

<div class='grouphdr'>WR by how deep a deck goes into the package</div>

{{sacrifice-density}}

<div class='grouphdr'>Also played by these decks (not core)</div>

{{sacrifice-also-played}}

## Discard <span class='meta' style='display:inline'>· {{discard-colors}} package</span>

% Core = {{discard-size}} cards (Jaccard-0.6 co-occurrence component) · deck set = {{discard-deck-count}} decks running ≥{{discard-threshold}} core cards · pooled {{discard-record}}. Card caption: backbone depth · inclusion · that card's deck WR.

{{discard-cards}}

<div class='grouphdr'>WR by how deep a deck goes into the package</div>

{{discard-density}}

<div class='grouphdr'>Also played by these decks (not core)</div>

{{discard-also-played}}

## Green <span class='meta' style='display:inline'>· graveyard vs landfall</span>

% Green never forms a package; it splits by emphasis. Two honest ways to score
% that split — label the decks, or label the cards — shown side by side.

### A · label the decks, pool their records

{{green-decks}}

### B · label the cards, average each card's deck-WR

{{green-card-rates}}

<div class='grouphdr'>Landfall payoffs</div>

{{green-landfall}}

<div class='grouphdr'>Graveyard payoffs</div>

{{green-graveyard}}

% (Payoffs tagged from oracle text; some read as both — curation pending.)

## Blue <span class='meta' style='display:inline'>· four soft-color clusters</span>

% Blue never clusters; instead each staple (md≥6) is colored by the partner
% color its decks most often carry. Grouped by that dominant partner; heading
% shows the group's average card WR.

{{blue-groups}}

## White <span class='meta' style='display:inline'>· function tags</span>

% White is jobs, not a package. Each card is multi-tagged; the table splits
% white decks by how many of each function they run (median split) with each
% side's WR.

{{white-functions}}

<div class='grouphdr'>Removal</div>

{{white-removal}}

<div class='grouphdr'>Aggro</div>

{{white-aggro}}

<div class='grouphdr'>Tokens</div>

{{white-tokens}}

<div class='grouphdr'>Draws</div>

{{white-draws}}

% (Removal/Tokens/Draws from oracle text, Aggro a hand seed — curation pending.)
