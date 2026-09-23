# Blog authoring

- Every post is a `post.md` + `components.py` pair directly below `blog/`.
- All editable prose, headings, captions, and section order belong in Markdown.
  Python supplies generated content, not the author's writing surface.
- Share presentation in `render.py`; inherit the LoL-derived defaults.
- Keep reusable data analysis in `roto/`. Posts choose inputs and render results.
- Build the requested post and, after shared changes, both posts. Check cards,
  tables, and interactions on desktop and narrow viewports.
- For unattended captures use `lf screenshot`. Building is not publishing.
