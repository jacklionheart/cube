"""Build blog posts for hosting on etude.gg.

python3 blog/build.py           build every cube's post
python3 blog/build.py samp-season-4      build one post

Each post runs in its own process so cube-local modules such as packages
and roto_summary cannot leak between LoL and Samp. Prose lives beside components.py in each post directory.
"""

import contextlib
import importlib.util
import json
import pathlib
import re
import subprocess
import sys

from render import ESSAY_CSS, render_page

HERE = pathlib.Path(__file__).resolve().parent
SITE = HERE / "site"


def render_post(post_dir):
    """Worker: render one post using only its own analysis imports."""
    post_dir = pathlib.Path(post_dir).resolve()
    sys.path.insert(0, str(post_dir))
    spec = importlib.util.spec_from_file_location(
        f"roto_post_{post_dir.name}", post_dir / "components.py")
    mod = importlib.util.module_from_spec(spec)
    # stdout is the worker's JSON channel; analysis diagnostics go to stderr.
    with contextlib.redirect_stdout(sys.stderr):
        spec.loader.exec_module(mod)
        parts = mod.build()
    page = render_page(
        getattr(mod, "TITLE", post_dir.name),
        (post_dir / "post.md").read_text(), parts,
        css=getattr(mod, "CSS", ESSAY_CSS),
        hover=getattr(mod, "HOVER", True),
        scripts=getattr(mod, "SCRIPTS", ""),
    )
    return {"slug": getattr(mod, "SLUG", post_dir.name), "html": page}


def build_artifact(post_dir):
    post_dir = pathlib.Path(post_dir).resolve()
    result = subprocess.run(
        [sys.executable, str(HERE / "build.py"), "--render", str(post_dir)],
        cwd=post_dir, stdout=subprocess.PIPE, text=True, check=True,
    )
    return json.loads(result.stdout)


def build_post(post_dir):
    """Return a complete preview page with draft markers intact."""
    return build_artifact(post_dir)["html"]


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--render":
        print(json.dumps(render_post(sys.argv[2])))
        return
    wanted = sys.argv[1:]
    dirs = sorted(d for d in HERE.iterdir()
                  if (d / "post.md").exists() and (d / "components.py").exists())
    if wanted:
        by_name = {d.name: d for d in dirs}
        missing = [name for name in wanted if name not in by_name]
        if missing:
            sys.exit(f"unknown post(s): {', '.join(missing)}; "
                     f"have: {', '.join(by_name)}")
        dirs = [by_name[name] for name in wanted]
    if not dirs:
        sys.exit("no post.md + components.py pairs found under blog/")
    for directory in dirs:
        artifact = build_artifact(directory)
        page = re.sub(r"\s*<span class='todo'>.*?</span>", "", artifact["html"])
        dest = SITE / artifact["slug"] / "index.html"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(page)
        print(dest)


if __name__ == "__main__":
    main()
