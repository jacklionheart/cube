"""The etude.gg essay renderer — extracted from roto/blog.py.

A post is a minimally-templated markdown-ish document (see render_doc)
plus a dict of generated HTML components ("parts"). This module owns the
dialect, the shared essay CSS, the mana-pip helper, and the hover-card
JS; it computes nothing — data-driven components come from each post's
components.py.
"""

import re

ESSAY_CSS = """
body { font-family: Charter, Georgia, 'Times New Roman', serif;
       font-size: 19px; line-height: 1.65; color: #1a1a1a;
       max-width: 680px; margin: 56px auto 120px; padding: 0 20px; }
h1 { font-size: 28px; line-height: 1.25; margin: 0 0 6px; }
h2 { font-size: 21px; margin: 48px 0 8px; }
h3 { font-size: 17px; margin: 30px 0 4px; }
a { color: inherit; text-decoration: underline;
    text-decoration-color: #b8b8b8; text-underline-offset: 2px; }
a:hover { text-decoration-color: #1a1a1a; }
.meta { font-family: -apple-system, 'Segoe UI', Helvetica, sans-serif;
        font-size: 14px; color: #6b6b6b; margin: 2px 0 14px; }
.mana { width: 13px; height: 13px; vertical-align: -1px; margin-right: 1px; }
.cards { display: flex; flex-wrap: wrap; gap: 8px; margin: 14px 0 18px; }
.cards img { width: 160px; border-radius: 6px; }
.todo { background: #fff8dc; padding: 2px 6px; font-family: -apple-system,
        'Segoe UI', Helvetica, sans-serif; font-size: 13px; }
.vchart { display: flex; align-items: flex-end; gap: 18px;
         height: 190px; margin: 18px 0 6px; font-family: -apple-system,
         'Segoe UI', Helvetica, sans-serif; font-size: 13px; }
.vcol { display: flex; flex-direction: column; align-items: center;
        justify-content: flex-end; height: 100%; }
.vbar { width: 34px; background: #7d93a8; border-radius: 4px 4px 0 0; }
.vnum { color: #444; margin-bottom: 3px; }
.vlab { margin-top: 6px; }
.tabs { margin: 10px 0 4px; }
.tabs button { background: none; border: none; cursor: pointer;
               font: 14px -apple-system, 'Segoe UI', Helvetica, sans-serif;
               color: #6b6b6b; padding: 4px 10px 5px 6px;
               border-bottom: 2px solid transparent; }
.tabs button.on { color: #1a1a1a; border-bottom-color: #1a1a1a; }
table { border-collapse: collapse; margin: 14px 0 18px;
        font: 14px/1.5 -apple-system, 'Segoe UI', Helvetica, sans-serif; }
th { text-align: left; font-weight: 600; color: #6b6b6b; }
th, td { padding: 6px 16px 6px 0; border-bottom: 1px solid #e8e8e8;
         vertical-align: top; }
.pairs { margin: 8px 0 16px; }
.pair { display: inline-flex; gap: 2px; margin: 3px 10px 3px 0; }
.pair img { width: 128px; border-radius: 5px; }
[hidden] { display: none !important; }
.explorer { display: grid; grid-template-columns: 110px 1fr; gap: 20px;
            margin: 24px 0 8px; }
.sidebar button { display: block; width: 100%; text-align: left;
    background: none; border: none; cursor: pointer; padding: 6px 8px;
    font: 15px -apple-system, 'Segoe UI', Helvetica, sans-serif;
    color: #6b6b6b; border-left: 2px solid transparent; }
.sidebar button.on { color: #1a1a1a; border-left-color: #1a1a1a; }
.vpanes { height: 400px; overflow-y: auto; }
.vpanes .cards img { width: 122px; }
.sbh { font: 600 11px -apple-system, 'Segoe UI', Helvetica, sans-serif;
       text-transform: uppercase; letter-spacing: .06em; color: #999;
       margin: 12px 0 2px; }
.seats { display: grid; grid-template-columns: repeat(3, 1fr);
         gap: 16px; margin: 18px 0;
         font: 13px -apple-system, 'Segoe UI', Helvetica, sans-serif; }
.seat { padding: 5px 9px; border-radius: 7px; margin: 4px 0;
        border: 1px solid transparent; }
.seat span { display: block; font-size: 11px; color: #6b6b6b; }
.sAggro { background: #f7ebe8; } .sGreen { background: #ebf3e8; }
.sBlue { background: #e8eff6; }
.sRect { background: #f6f1e2; }
.sFoomp { background: #f0e7f8; }
.fdot { color: #9a6bb8; }
ul { list-style: none; padding-left: 4px; margin: 14px 0 18px; }
li { margin: 5px 0; }
#hovercard { position: fixed; display: none; z-index: 10;
             pointer-events: none; }
#hovercard img { width: 250px; border-radius: 12px;
                 box-shadow: 0 6px 18px rgba(0,0,0,.28); }
"""

HOVER_JS = """<div id='hovercard'><img alt=''></div>
<script>
const hc = document.getElementById('hovercard');
const hcImg = hc.querySelector('img');
document.addEventListener('mouseover', e => {
  const a = e.target.closest('a[data-img]');
  if (a && a.dataset.img) { hcImg.src = a.dataset.img;
    hc.style.display = 'block'; }
  else if (!e.target.closest('#hovercard')) hc.style.display = 'none';
});
document.addEventListener('mousemove', e => {
  if (hc.style.display !== 'block') return;
  const w = 250, h = 349;
  let x = e.clientX + 16, y = e.clientY + 12;
  if (x + w > innerWidth - 8) x = e.clientX - w - 16;
  if (y + h > innerHeight - 8) y = innerHeight - h - 8;
  hc.style.left = x + 'px'; hc.style.top = Math.max(8, y) + 'px';
});
</script>"""


CANON = (["W", "U", "B", "R", "G"]
         + ["WU", "UB", "BR", "RG", "WG", "WB", "UR", "BG", "WR", "UG"]
         + ["WUG", "WUB", "UBR", "BRG", "WRG",
            "WBG", "WUR", "UBG", "WBR", "URG"]
         + ["WUBR", "WUBG", "WURG", "WBRG", "UBRG", "WUBRG", "C"])


def canon_key(cl):
    return CANON.index(cl) if cl in CANON else len(CANON)


def mana(letters):
    syms = [s for s in letters if s in "WUBRGC"] or ["C"]
    return "".join(
        f"<img class='mana' src='https://svgs.scryfall.io/card-symbols/"
        f"{s}.svg' alt='{s}'>" for s in syms)


def render_doc(text, parts):
    """The essay copy lives in post.md: markdown-ish headings and
    paragraphs (raw HTML passes through), '%'-prefixed lines for
    captions/meta, and {{name}} slots for generated components (block
    when alone on a line, inline otherwise). {{mana:WR}} renders pips."""
    def resolve(name):
        if name.startswith("mana:"):
            return mana(name[5:])
        return parts[name]

    def sub(s):
        s = re.sub(r"\{\{([\w:-]+)\}\}",
                   lambda m: resolve(m.group(1)), s)
        s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
        s = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<i>\1</i>", s)
        return s.replace(" -- ", " — ")

    out = []
    for block in re.split(r"\n\s*\n", text):
        block = block.strip()
        if not block:
            continue
        if re.fullmatch(r"\{\{[\w:-]+\}\}", block):
            out.append(resolve(block[2:-2]))
        elif block.startswith("### "):
            out.append(f"<h3>{sub(block[4:])}</h3>")
        elif block.startswith("## "):
            out.append(f"<h2>{sub(block[3:])}</h2>")
        elif block.startswith("# "):
            out.append(f"<h1>{sub(block[2:])}</h1>")
        elif block.startswith("%"):
            txt = " ".join(l.lstrip("% ") for l in block.splitlines())
            out.append(f"<p class='meta'>{sub(txt)}</p>")
        elif all(l.startswith(("* ", "+ ", "- ")) for l in block.splitlines()):
            items = "".join(f"<li>{sub(l[2:])}</li>"
                            for l in block.splitlines())
            out.append(f"<ul>{items}</ul>")
        else:
            out.append(f"<p>{sub(' '.join(block.splitlines()))}</p>")
    return out


def render_page(title, text, parts, css=None, hover=True):
    """Assemble a full self-contained essay page (a single HTML string).
    css defaults to the shared essay stylesheet; posts may extend it via
    a `CSS` attribute in their components.py. hover=False drops the
    card-image hover layer for posts with no data-img links."""
    out = [f"<meta charset='utf-8'>"
           f"<title>{title}</title>"
           f"<style>{css if css is not None else ESSAY_CSS}</style>"]
    out += render_doc(text, parts)
    if hover:
        out.append(HOVER_JS)
    return "\n".join(out)
