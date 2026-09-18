"""Render out/blog-post.html: the shareable blog-post version.

The post now lives in the etude publishing structure:
  etude/posts/lol-roto-meta/post.md          the essay copy (was blog.md)
  etude/posts/lol-roto-meta/components.py    the {{slot}} components
  etude/etudelib/render.py                   the shared dialect/CSS/JS

This wrapper is kept so the historical entry point still works; it
renders the same post via etude and writes the same output file.
`python3 etude/build.py` renders it to etude/site/lol-roto-meta/ for
etude.gg instead.

Usage: python3 blog.py
"""

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ETUDE = HERE.parent / "etude"
sys.path.insert(0, str(ETUDE))


def main():
    from build import build_post
    html = build_post(ETUDE / "posts" / "lol-roto-meta")
    dest = HERE / "out" / "blog-post.html"
    dest.parent.mkdir(exist_ok=True)
    dest.write_text(html)
    print(dest)


if __name__ == "__main__":
    main()
