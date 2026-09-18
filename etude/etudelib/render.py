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
.cards img { width: 160px; border-radius: 6px;
             aspect-ratio: 488 / 680; }
.cards.small img { width: 118px; }
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
.pair img { width: 128px; border-radius: 5px;
            aspect-ratio: 488 / 680; }
[hidden] { display: none !important; }
.explorer { display: grid; grid-template-columns: 120px 1fr; gap: 20px;
            width: min(920px, calc(100vw - 32px));
            margin: 24px 0 8px;
            margin-left: calc((100% - min(920px, 100vw - 32px)) / 2); }
.sidebar button { display: block; width: 100%; text-align: left;
    background: none; border: none; cursor: pointer; padding: 6px 8px;
    font: 15px -apple-system, 'Segoe UI', Helvetica, sans-serif;
    color: #6b6b6b; border-left: 2px solid transparent; }
.sidebar button.on { color: #1a1a1a; border-left-color: #1a1a1a; }
.vpanes { height: 620px; overflow-y: auto; }
.vpanes .cards img { width: 172px; }
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
.defn { background: #fafaf7; border: 1px solid #e8e6e0;
        border-radius: 8px; padding: 14px 20px; margin: 22px 0; }
.defn .dlabel { font: 600 11px -apple-system, 'Segoe UI', Helvetica,
        sans-serif; text-transform: uppercase; letter-spacing: .08em;
        color: #999; margin-bottom: 8px; }
.defn .deq { display: flex; align-items: baseline; gap: 14px; }
.defn .dterm { font-weight: 700; font-style: italic;
        white-space: nowrap; }
.defn .dsym { color: #8a8a8a; }
ul { margin: 14px 0 18px; padding-left: 26px; }
ul.plain { list-style: none; padding-left: 4px; }
li { margin: 5px 0; }
#deckhover { position: fixed; display: none; z-index: 11;
             pointer-events: none; background: #fff;
             border: 1px solid #ddd; border-radius: 10px; padding: 6px;
             box-shadow: 0 6px 18px rgba(0,0,0,.25); width: 480px; }
#deckhover img { width: 64px; border-radius: 3px; margin: 1px; }
#hovercard { position: fixed; display: none; z-index: 10;
             pointer-events: none; }
#hovercard img { width: 250px; border-radius: 12px;
                 box-shadow: 0 6px 18px rgba(0,0,0,.28); }
"""

HOVER_JS = """<div id='hovercard'><img alt=''></div>
<div id='deckhover'></div>
<script>
const hc = document.getElementById('hovercard');
const hcImg = hc.querySelector('img');
const dh = document.getElementById('deckhover');
document.addEventListener('mouseover', e => {
  const d = e.target.closest('[data-deck]');
  const a = e.target.closest('a[data-img]');
  if (d && d.dataset.deck && deckImgs[d.dataset.deck]) {
    dh.innerHTML = deckImgs[d.dataset.deck].map(
      u => `<img src='${u}' loading='lazy'>`).join('');
    dh.style.display = 'block'; hc.style.display = 'none';
  } else if (a && a.dataset.img) {
    hcImg.src = a.dataset.img;
    hc.style.display = 'block'; dh.style.display = 'none';
  } else { hc.style.display = 'none'; dh.style.display = 'none'; }
});
document.addEventListener('mousemove', e => {
  const el = dh.style.display === 'block' ? dh
           : (hc.style.display === 'block' ? hc : null);
  if (!el) return;
  const r = el.getBoundingClientRect();
  const w = r.width || 250, h = r.height || 349;
  let x = e.clientX + 16, y = e.clientY + 12;
  if (x + w > innerWidth - 8) x = e.clientX - w - 16;
  if (y + h > innerHeight - 8) y = innerHeight - h - 8;
  el.style.left = x + 'px'; el.style.top = Math.max(8, y) + 'px';
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
    when alone on a line, inline otherwise). {{mana:WR}} renders pips.

    Posts can define their own inline tokens: a callable stored under a
    key ending in ':' (e.g. parts['deck:']) receives everything after
    the first colon — so {{deck:1:Mark}} calls parts['deck:']('1:Mark')."""
    def resolve(name):
        if name in parts:
            return parts[name]
        if name.startswith("mana:"):
            return mana(name[5:])
        head, sep, rest = name.partition(":")
        fn = parts.get(head + ":")
        if sep and callable(fn):
            return fn(rest)
        return parts[name]

    def sub(s):
        s = re.sub(r"\{\{([^{}]+?)\}\}",
                   lambda m: resolve(m.group(1)), s)
        s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
        s = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<i>\1</i>", s)
        return s.replace(" -- ", " — ")

    out = []
    for block in re.split(r"\n\s*\n", text):
        block = block.strip()
        if not block:
            continue
        if re.fullmatch(r"\{\{[^{}]+?\}\}", block):
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
        elif any(l.startswith(("* ", "+ ", "- ")) for l in block.splitlines()):
            # stem lines render as a paragraph, bullet runs as a list;
            # lists of pips/HTML chips get class='plain' (no markers)
            lines = block.splitlines()
            i = 0
            while i < len(lines):
                if lines[i].startswith(("* ", "+ ", "- ")):
                    items = []
                    while (i < len(lines)
                           and lines[i].startswith(("* ", "+ ", "- "))):
                        items.append(lines[i][2:])
                        i += 1
                    plain = all(it.startswith(("{{", "<"))
                                for it in items)
                    cls = " class='plain'" if plain else ""
                    out.append(f"<ul{cls}>" + "".join(
                        f"<li>{sub(it)}</li>" for it in items) + "</ul>")
                else:
                    para = []
                    while (i < len(lines)
                           and not lines[i].startswith(("* ", "+ ", "- "))):
                        para.append(lines[i])
                        i += 1
                    out.append(f"<p>{sub(' '.join(para))}</p>")
        elif block.startswith("<"):
            # raw HTML block: pass through without <p> wrapping
            out.append(sub(" ".join(block.splitlines())))
        else:
            out.append(f"<p>{sub(' '.join(block.splitlines()))}</p>")
    return out


def render_page(title, text, parts, css=None, hover=True, scripts=""):
    """Assemble a full self-contained essay page (a single HTML string).
    css defaults to the shared essay stylesheet; posts may extend it via
    a `CSS` attribute in their components.py. hover=False drops the
    card-image hover layer for posts with no data-img links. scripts is
    raw HTML appended after the doc, before the hover layer — e.g. the
    deckImgs data that [data-deck] hover galleries need."""
    out = [f"<meta charset='utf-8'>"
           f"<title>{title}</title>"
           f"<style>{css if css is not None else ESSAY_CSS}</style>"]
    out += render_doc(text, parts)
    if scripts:
        out.append(scripts)
    if hover:
        out.append(HOVER_JS)
    return "\n".join(out)
