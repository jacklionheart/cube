# etude

The publishing structure for essays on [etude.gg](https://etude.gg).
Each post is prose in a minimally-templated markdown-ish file plus a
Python module that computes its data-driven components. The renderer,
essay CSS, and hover-card JS were extracted from `roto/blog.py` and are
shared by every post.

## Layout

- `etudelib/render.py` — the dialect (`render_doc`), shared essay CSS
  (`ESSAY_CSS`), mana-pip helper (`mana`), hover-card JS, and
  `render_page()` which assembles a full page
- `posts/<slug>/post.md` — the essay copy
- `posts/<slug>/components.py` — builds the `{{slot}}` parts dict;
  exports `TITLE` and `def build() -> dict`
- `build.py` — renders every post to `site/<slug>/index.html`
- `site/` — build output (gitignored)

## Building

```
python3 build.py                 # all posts
python3 build.py lol-roto-meta   # one post
```

`python3 roto/blog.py` still works: it is a thin wrapper that renders
the `lol-roto-meta` post through this machinery and writes the
historical `roto/out/blog-post.html` path.

## The dialect (post.md)

Blocks are separated by blank lines:

- `# / ## / ###` — headings
- plain paragraphs — raw HTML passes through untouched; lines within a
  block are joined with spaces
- `**bold**`, `*italic*`, and ` -- ` becomes an em dash
- `% ...` — a caption/meta paragraph (`.meta` styling); consecutive
  `%` lines join into one caption
- `* item` / `- item` / `+ item` — list items; a block may mix stem
  lines (rendered as paragraphs) with bullet runs. A list whose items
  are all pips/HTML chips gets `class='plain'` (no markers)
- a block starting with `<` — raw HTML, passed through without `<p>`
  wrapping (slots still substituted)
- `{{name}}` — a component slot. Alone on its own block it is inserted
  as a block; inline it is substituted into the surrounding text
- `{{mana:WUBRG}}` — inline mana pips (no components.py entry needed)
- posts can define their own inline tokens: a callable stored under a
  key ending in `:` receives everything after the first colon — e.g.
  `parts["deck:"]` makes `{{deck:1:Mark}}` render
  `parts["deck:"]("1:Mark")`. The lol-roto-meta post uses this for
  `{{deck:N:Player}}` and `{{drafter:N:Player}}` links

Every other `{{name}}` must have a matching key in the dict returned by
`components.build()` — a missing key fails the build (KeyError), which
is what you want.

## Starting a new post

1. `mkdir posts/my-post` and write `posts/my-post/post.md`.
2. Add `posts/my-post/components.py`:

   ```python
   TITLE = "My Post"

   def build():
       return {"my-chart": "<div class='vchart'>...</div>"}
   ```

   Optional module attributes: `CSS` (a full stylesheet replacing
   `ESSAY_CSS` — usually `ESSAY_CSS + "..."`), `HOVER = False` to drop
   the hover-card layer if the post has no `data-img` links, and
   `SCRIPTS` — raw HTML appended after the doc, before the hover layer.
   `SCRIPTS` may be set by `build()` via `global` when it depends on
   computed data; the lol-roto-meta post emits its `deckImgs` dict this
   way, which the shared hover layer reads to show a whole-deck gallery
   over any `[data-deck]` element.
3. `python3 build.py my-post` and open `site/my-post/index.html`.

Conventions that make posts hold up:

- **Assert your prose.** If post.md hardcodes a number ("the record is
  16"), assert it in `build()` so a data refresh that changes the
  number fails the build instead of silently contradicting the copy.
- **Deterministic output.** Seed any shuffle from the data (see
  `gallery(shuffle=True)` in the lol-roto-meta components) so rebuilds
  are diffable.
- Components that need project data should `sys.path`-insert the
  project directory (e.g. `roto/`) and import its library; keep the
  heavy analysis in the project, not in components.py.

## Deployment

Output pages are single self-contained HTML files — inline CSS/JS, no
local assets. Card images and mana symbols are hotlinked from Scryfall
(`cards.scryfall.io` / `svgs.scryfall.io`), which Scryfall permits and
which keeps the site static. Publishing is therefore just copying
`site/` to wherever etude.gg is hosted; `site/<slug>/index.html` gives
stable `etude.gg/<slug>/` URLs. Nothing at build time hits the network
(the roto post reads only committed caches), so builds are reproducible
offline.
