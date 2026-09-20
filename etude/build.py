"""Build every etude.gg post: posts/<slug>/{post.md,components.py} ->
site/<slug>/index.html (self-contained; card images and mana pips are
hotlinked from Scryfall, so no local assets are needed).

Usage:
  python3 build.py              build all posts
  python3 build.py <slug> ...   build specific posts
"""

import importlib.util
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
POSTS = HERE / "posts"
SITE = HERE / "site"

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from etudelib.render import ESSAY_CSS, render_page  # noqa: E402


def load_components(post_dir):
    """Import a post's components.py as an isolated module."""
    post_dir = pathlib.Path(post_dir)
    spec = importlib.util.spec_from_file_location(
        f"etude_post_{post_dir.name.replace('-', '_')}",
        post_dir / "components.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build_post(post_dir):
    """Render one post directory to a full HTML string."""
    post_dir = pathlib.Path(post_dir)
    mod = load_components(post_dir)
    parts = mod.build()
    text = (post_dir / "post.md").read_text()
    return render_page(
        getattr(mod, "TITLE", post_dir.name),
        text, parts,
        css=getattr(mod, "CSS", ESSAY_CSS),
        hover=getattr(mod, "HOVER", True),
        scripts=getattr(mod, "SCRIPTS", ""),
    )


def main():
    wanted = sys.argv[1:]
    dirs = sorted(d for d in POSTS.iterdir()
                  if (d / "post.md").exists() and (d / "components.py").exists())
    if wanted:
        by_name = {d.name: d for d in dirs}
        missing = [w for w in wanted if w not in by_name]
        if missing:
            sys.exit(f"unknown post(s): {', '.join(missing)}; "
                     f"have: {', '.join(by_name)}")
        dirs = [by_name[w] for w in wanted]
    if not dirs:
        sys.exit("no posts found under posts/")
    for d in dirs:
        html = build_post(d)
        # site/ is the publish artifact: draft markers stay visible in
        # dev builds but never ship
        html = re.sub(r"\s*<span class='todo'>.*?</span>", "", html)
        dest = SITE / d.name / "index.html"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(html)
        print(dest)


if __name__ == "__main__":
    main()
