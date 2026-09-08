# /// script
# requires-python = ">=3.11"
# dependencies = ["nbformat", "nbclient", "nbconvert", "ipykernel",
#                 "pandas", "pyarrow", "duckdb", "statsmodels", "scipy",
#                 "matplotlib", "requests"]
# ///
"""Notebook build system: percent-format .py  ->  executed .ipynb (+ .html).

Author notebooks as readable/diffable percent-format .py files in this dir
(cells split on `# %%`, markdown cells on `# %% [markdown]` with `#`-prefixed
lines). This converts, executes against lib17, and exports HTML.

  uv run notebooks/build.py [name ...]   # default: all notebooks/[0-9]*.py
"""
import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter

HERE = Path(__file__).parent


def to_notebook(pyfile):
    nb = nbformat.v4.new_notebook()
    cells, buf, kind = [], [], "code"

    def flush():
        txt = "\n".join(buf).strip("\n")
        if kind == "markdown":
            md = "\n".join(l[2:] if l.startswith("# ") else l.lstrip("#")
                           for l in txt.split("\n"))
            if md.strip():
                cells.append(nbformat.v4.new_markdown_cell(md))
        elif txt.strip():
            cells.append(nbformat.v4.new_code_cell(txt))

    for line in pyfile.read_text().splitlines():
        if line.startswith("# %%"):
            flush(); buf = []
            kind = "markdown" if "markdown" in line else "code"
        else:
            buf.append(line)
    flush()
    nb.cells = cells
    return nb


def build(pyfile):
    nb = to_notebook(pyfile)
    NotebookClient(nb, timeout=1200, resources={"metadata": {"path": str(HERE)}}).execute()
    out = pyfile.with_suffix(".ipynb")
    nbformat.write(nb, out)
    html, _ = HTMLExporter(exclude_input=False).from_notebook_node(nb)
    (HERE / "html").mkdir(exist_ok=True)
    (HERE / "html" / (pyfile.stem + ".html")).write_text(html)
    print(f"built {out.name} (+ html/{pyfile.stem}.html)")


def main():
    names = sys.argv[1:]
    files = ([HERE / f"{n}.py" if not n.endswith(".py") else HERE / n for n in names]
             if names else sorted(p for p in HERE.glob("*.py") if p.name != "build.py"))
    for f in files:
        build(f)


if __name__ == "__main__":
    main()
