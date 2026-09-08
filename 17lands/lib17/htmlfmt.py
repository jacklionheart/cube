"""Shared HTML look for the project's report pages (editorial cream/ink/crimson)."""

CSS = """
:root{--ink:#2b2622;--paper:#faf6ee;--paper2:#f3ecdd;--crim:#a4282e;--fade:#8a8074;--rule:#d8cfbc}
body{margin:0;background:var(--paper);color:var(--ink);font-family:'Newsreader',Georgia,serif;
 font-size:16.5px;line-height:1.58}
.page{max-width:820px;margin:0 auto;padding:0 26px 80px}
header{padding:48px 0 22px;border-bottom:3px double var(--ink);margin-bottom:30px}
.kicker{font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:.2em;
 text-transform:uppercase;color:var(--crim);margin-bottom:12px}
h1{font-family:'Fraunces',serif;font-weight:900;font-size:40px;line-height:1.05;margin:0 0 10px}
.sub{font-family:'IBM Plex Mono',monospace;font-size:12px;color:var(--fade)}
h2{font-family:'Fraunces',serif;font-weight:900;font-size:24px;margin:46px 0 4px}
h2 .act{display:block;font-family:'IBM Plex Mono',monospace;font-size:11px;font-weight:600;
 letter-spacing:.18em;text-transform:uppercase;color:var(--crim);margin-bottom:6px}
p{margin:12px 0}
table{width:100%;border-collapse:collapse;margin:16px 0;font-size:14px}
th{font-family:'IBM Plex Mono',monospace;font-size:10.5px;letter-spacing:.05em;text-transform:uppercase;
 font-weight:600;text-align:left;padding:7px 9px;border-top:2px solid var(--ink);border-bottom:1px solid var(--ink)}
td{padding:6px 9px;border-bottom:1px solid var(--rule);font-variant-numeric:tabular-nums}
td.n,th.n{text-align:right;font-family:'IBM Plex Mono',monospace;font-size:12.5px}
.note{background:var(--paper2);border-left:4px solid var(--crim);padding:13px 18px;margin:20px 0;font-size:15px}
.note .tag{font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:.18em;
 text-transform:uppercase;color:var(--crim);display:block;margin-bottom:8px;font-weight:600}
.figure{margin:26px 0}.figure img{width:100%;border:1px solid var(--rule)}
.figcap{font-size:13.5px;color:var(--fade);margin-top:7px;line-height:1.5}
.foot{margin-top:54px;padding-top:14px;border-top:3px double var(--ink);font-size:13px;color:var(--fade)}
"""

HEAD = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{title}</title>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,900&family=Newsreader:opsz,wght@6..72,400;6..72,500&family=IBM+Plex+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>{css}</style></head><body><div class="page">
<header><div class="kicker">{kicker}</div>
<h1>{title}</h1><div class="sub">{sub}</div></header>
"""

FOOT = '<div class="foot">{text}</div></div></body></html>'

MPL_STYLE = {
    "figure.facecolor": "#faf6ee", "axes.facecolor": "#faf6ee",
    "savefig.facecolor": "#faf6ee", "text.color": "#2b2622",
    "axes.edgecolor": "#2b2622", "axes.labelcolor": "#2b2622",
    "xtick.color": "#2b2622", "ytick.color": "#2b2622",
    "font.family": "Georgia", "axes.spines.top": False,
    "axes.spines.right": False, "font.size": 11}
INK, CRIM, FADE = "#2b2622", "#a4282e", "#8a8074"


def page(title, kicker, sub, body_parts, foot):
    return (HEAD.format(title=title, kicker=kicker, sub=sub, css=CSS)
            + "\n".join(body_parts) + FOOT.format(text=foot))


def html_table(df, cols, ren=None):
    d = df[cols].rename(columns=ren or {})
    head = "".join(f"<th{' class=n' if d[c].dtype.kind in 'fi' else ''}>{c}</th>"
                   for c in d.columns)
    rows = []
    for _, r in d.iterrows():
        tds = []
        for c in d.columns:
            v = r[c]
            if isinstance(v, float):
                tds.append(f"<td class=n>{v:.3f}</td>" if abs(v) < 10 else f"<td class=n>{v:.1f}</td>")
            else:
                tds.append(f"<td>{v}</td>")
        rows.append("<tr>" + "".join(tds) + "</tr>")
    return f"<table><tr>{head}</tr>{''.join(rows)}</table>"


def embed_fig(fig, caption=""):
    import base64
    import io
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=160)
    b64 = base64.b64encode(buf.getvalue()).decode()
    cap = f'<div class="figcap">{caption}</div>' if caption else ""
    return f'<div class="figure"><img src="data:image/png;base64,{b64}">{cap}</div>'
