# Samp blog

Prose: `blog/samp-season-4/post.md`. Generated pieces: adjacent `components.py`.
Build: `python3 blog/build.py samp-season-4`; preview:
`blog/site/samp-season-4/index.html`. Both posts use `blog/render.py`.

Analysis and local data live in `roto/samp/`; reusable algorithms in `roto/`.
The blog uses 13 s4 pods even though refresh_all supports 37 drafts.
`roto/samp/refresh.py --dry-run` downloads Sheets and builds locally; RTB live
and standings payloads remain cached unless explicitly fetched beforehand.
Compare roster names, picks, and records to a backup after refreshing.
Reconcile roster spelling changes with both deck TSVs and record keys.
