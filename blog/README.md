# Blog

The authoring and presentation system for posts hosted on etude.gg. The
hosting name is not a separate code layer. Data analysis lives in `../roto/`.

## Write and preview

- [LoL kickoff](lol-kickoff/post.md)
- [Samp season 4](samp-season-4/post.md)

**Every post starts as `post.md` plus `components.py`.** Write prose,
headings, captions, and section order in Markdown. Keep only computed
values, tables, and galleries in Python. Never make the author edit Python
strings or generated HTML to write their article.

From the repository root:

```sh
python3 blog/build.py samp-season-4
python3 blog/build.py lol-kickoff
python3 blog/build.py
```

Open `blog/site/<post>/index.html` in a browser after rebuilding. Output is
ignored and self-contained except for hotlinked card images and mana pips.
Building does not publish or refresh data. LoL requires its three cached
source workbooks under `roto/lol/sources/`; Samp uses `roto/samp/sources/`.

Each post builds in a separate Python process so the two pipelines' legacy
module names cannot cross-contaminate a combined build.

## Authoring dialect

Separate blocks with blank lines:

- `#`, `##`, `###`: headings.
- Plain text: paragraphs; `**bold**`, `*italic*`, and ` -- ` are supported.
- `% caption`: smaller caption text. Consecutive `%` lines form one paragraph.
- `- item`: a list. Raw HTML is supported when needed.
- `{{sacrifice-cards}}`: a generated block; put it on its own line.
- `{{pod-count}}`: a generated value inside a sentence.
- `{{mana:WUBRG}}`: mana pips.

Use HTML anchors for links; this intentionally small dialect does not
implement general Markdown link syntax. Unknown component names fail the
build. Posts can provide callable `name:` components for inline tokens.

## Shared presentation

`render.py` owns typography, card galleries, captions, tables, charts,
keyboard-enabled tabs, card/deck hover previews, and mobile behavior.
The defaults come from the LoL article and apply to Samp automatically.

Components should use `card_gallery()` and `tabbed_panels()` rather than
copy HTML/JS/CSS. Helpers preserve the caller's card order. Sort ties
explicitly so rebuilding does not reshuffle equally ranked cards.

`components.py` exports `TITLE` and `build() -> dict`. It may provide
`SLUG`, `SCRIPTS`, `HOVER`, or an extended `CSS` when needed. Keep
reusable analysis in `roto/`; a post selects its dataset and renders results.
Computed claims should use slots or assert the numbers beside the computation.

## Add a post

Create `blog/<slug>/post.md` and `components.py`. The builder discovers
that pair automatically. Start with the shared presentation; promote
useful polish here so subsequent posts receive it too.

`site/` is the deployment artifact. Existing draft-marker spans are removed
there; `build_post()` returns a preview with those markers retained.
