# Standard blog workflow

Create `blog/<slug>/post.md` and `components.py` from the beginning.
The author writes Markdown; generated charts and tables use `{{slot}}` blocks.
Do not embed editable article prose in Python or create a standalone HTML
article as the source. Reuse shared presentation from `blog/render.py` and
cube-independent analysis from `roto/`. etude.gg is the hosting destination.
