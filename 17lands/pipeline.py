# /// script
# requires-python = ">=3.11"
# dependencies = ["requests", "pandas", "pyarrow", "duckdb", "statsmodels", "matplotlib"]
# ///
"""CLI over lib17 — every artifact in this project regenerates from here.

  uv run pipeline.py prep <fmt>        logs -> parquets (+ as-picked cells)
  uv run pipeline.py slopes <fmt>      as-picked slopes & early/late summary
  uv run pipeline.py cards <fmt>       per-card corrected quality -> out/deepdive_<fmt>.csv
  uv run pipeline.py insights <fmt>    actionable HTML page -> out/insights_<fmt>.html
  uv run pipeline.py panels            weekly re-pricing panels + kappa
  uv run pipeline.py robustness        the full robustness battery -> out/robustness.md
  uv run pipeline.py report            figures + slept_on_cards_report.html

<fmt> in {sos, fin, tla, cube}. Everything runs offline from data/ except the
first `prep` of a format (S3 download) and a missing scryfall dump.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from lib17 import analysis, data, fetch, metrics
from lib17 import htmlfmt as H

HERE = Path(__file__).parent
OUT = HERE / "out"
LABELS = {t: f["label"] for t, f in data.FORMATS.items()}


# ------------------------------------------------------------------ prep ----
def cmd_prep(tag):
    data.prep_logs(tag)
    data.aspicked(tag, force=True)
    print(f"{tag}: parquets ready")


def cmd_slopes(tag):
    print(f"# {LABELS[tag]} — as-picked within-card slopes (pp per pick taken later)")
    for m, (b, se) in analysis.aspicked_slopes(tag).items():
        print(f"  {m:10s}: {b:+.3f} (card-clustered se {se:.3f})")
    pc = analysis.early_late(tag)
    print(f"early(1-4) vs late(7+) GIH, n>=300 both sides: {len(pc)} cards, "
          f"{(pc.z > 2).sum()} sig higher late, {(pc.z < -2).sum()} sig lower "
          f"(~{len(pc) * 0.025:.0f} expected per tail)")


def cmd_cards(tag):
    stats = data.card_stats(tag)
    q = metrics.card_quality(stats, fetch.scryfall())
    q = metrics.attach_early_deployment(q, data.aspicked(tag))
    q["grp"] = q.modal_deck.fillna("?")
    out = OUT / f"deepdive_{tag}.csv"
    q.to_csv(out, index=False)
    print(f"wrote {out} ({len(q)} cards, mu={q.mu.iloc[0]:.4f})")


# ------------------------------------------------------------- insights -----
HEAD = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{title} — Draft Insights</title>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,900&family=Newsreader:opsz,wght@6..72,400;6..72,500&family=IBM+Plex+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>{css}</style></head><body><div class="page">
<header><div class="kicker">17Lands Data · Actionable Draft Insights</div>
<h1>{title}</h1><div class="sub">{sub}</div></header>
<p>Companion to <em>Sleeping on Cards</em>. <b>quality</b> = corrected, noise-shrunk effect in an
average deck, GIH units (cost baselines exclude Power in cube); <b>if-early</b> = quality scaled by the
early-pick maindeck rate. Lists gated to play rate ≥35% and ≥1,000 in-hand games. Caveats on every
table: effects are measured only in decks that chose to play the card; tutors and zero-cost artifacts
are where draw-based methods are least reliable; all data is best-of-one Arena play. Treat lists as
hypotheses conditional on your seat, not pick orders.</p>
"""


def _deepdive(tag):
    """Path to the per-card csv; regenerate it if missing (so insights /
    robustness work standalone after out/ is cleared)."""
    p = OUT / f"deepdive_{tag}.csv"
    if not p.exists():
        cmd_cards(tag)
    return p


def cmd_insights(tag):
    sub = {"cube": "card data: Nov 2025 run logs (the only public cube logs)",
           }.get(tag, "Premier Draft logs")
    dd = pd.read_csv(_deepdive(tag))
    dd = dd[~dd.type.str.contains("Basic Land", na=False)].copy()
    np_ = dd[~dd.name.isin(metrics.POWER)].copy() if tag == "cube" else dd
    np_ = np_[(np_.pct_gp >= 0.35) & (np_.n_gih >= 1000)].copy()
    np_["ci95"] = 1.96 * np_.se_v3 * 100
    np_ = np_.rename(columns={"adj_gih_wr": "quality", "early_gih_wr": "if-early",
                              "gih_wr": "raw GIH", "ata": "avg taken at",
                              "pct_gp": "play rate", "name": "card", "ci95": "effect ±pp"})
    np_["rank_B"] = np_["if-early"].rank(ascending=False)
    np_["div"] = np_["avg taken at"].rank() - np_.rank_B
    cols = ["card", "avg taken at", "raw GIH", "quality", "if-early", "play rate", "effect ±pp"]

    body = [HEAD.format(title=LABELS[tag], sub=sub, css=H.CSS)]
    body.append('<h2><span class="act">Action: take these earlier</span>Underpicked — quality far ahead of pick position</h2>')
    body.append(H.html_table(np_.nlargest(10, "div"), cols))
    body.append('<h2><span class="act">Action: stop fighting for these</span>Overpicked — pick position far ahead of corrected value</h2>')
    body.append(H.html_table(np_.nsmallest(10, "div"), cols))
    body.append('<h2><span class="act">Action: discount the shiny stats</span>Context riders — win rate that belongs to the deck</h2>')
    body.append("<p>Highest never-seen win rates vs format (game-length-reweighted). Subtract <b>context</b> before believing the GIH column.</p>")
    cr = dd[dd.n_gns >= 1000].assign(context_pp=dd.context * 100).nlargest(10, "context_pp")
    body.append(H.html_table(cr.rename(columns={"name": "card", "ata": "avg taken at",
                                               "gih_wr": "raw GIH", "modal_deck": "home deck",
                                               "context_pp": "context (pp)"}),
                            ["card", "home deck", "avg taken at", "raw GIH", "context (pp)"]))
    body.append('<h2><span class="act">Action: calibrate your pick order</span>Best cards by corrected quality</h2>')
    body.append(H.html_table(np_.nlargest(12, "quality"), cols))
    body.append('<div class="note">A card slept on by ~6 picks carries roughly +0.5–1pp of win rate that is circumstance, not quality, and each pick of lateness costs it 3–4pp of maindeck probability. The corrections remove circumstance; they do <b>not</b> remove win rate a card earns from its archetype being good.</div>')
    body.append('<div class="foot">Methods, robustness, and the full story: slept_on_cards_report.html. Data: 17lands.com public datasets.</div>')
    body.append("</div></body></html>")
    out = OUT / f"insights_{tag}.html"
    out.write_text("\n".join(body))
    print(f"wrote {out}")


# ------------------------------------------------------- panels / checks ----
def cmd_panels():
    k, kse = analysis.kappa()
    print(f"kappa (within-card dATA/dALSA, SOS weekly): {k:.3f} ± {kse:.3f}")
    for exp in ["SOS", "FIN", "TLA", "CubeRun4"]:
        try:
            b, se, n = analysis.weekly_panel(exp)
            print(f"{exp}: GP WR panel {b:+.3f} ± {se:.3f} pp/ALSA-pick "
                  f"(÷{metrics.KAPPA:.2f} = {b / metrics.KAPPA:+.3f} per taken-at pick; n={n})")
        except Exception as e:
            print(f"{exp}: unavailable ({e})")


def cmd_robustness():
    lines = ["# Robustness battery (latest run)"]

    def log(s):
        print(s)
        lines.append(s)

    (b0, s0), (b1, s1) = analysis.slope_with_pod_control("sos")
    log(f"\npod-generosity control (SOS GP): +{b0:.3f} -> +{b1:.3f} (se {s1:.3f})")
    log("  NOTE: whole-draft, color-agnostic; same-color lane openness untested.")
    (b0, s0), (b1, s1) = analysis.slope_with_rank_fe("sos")
    log(f"ladder-rank FE (SOS GP): +{b0:.3f} -> +{b1:.3f} (se {s1:.3f})")
    (b0, s0), (b1, s1) = analysis.slope_with_week_fe("sos")
    log(f"draft-week FE (SOS GP): +{b0:.3f} -> +{b1:.3f} (se {s1:.3f})")
    k, kse = analysis.kappa()
    log(f"kappa = {k:.3f} ± {kse:.3f}")
    prem, se, members = analysis.staples_cohort("sos")
    log(f"no-filter staples cohort ({len(members)} cards): late premium {prem:+.2f}pp (se {se:.2f})")
    dd = pd.read_csv(_deepdive("cube"))
    fix = set(dd[dd.type.str.contains("Land", na=False)
                 | dd.name.str.contains("Talisman|Signet", na=False)].name)
    (d1, s1, n1), (d2, s2, n2) = analysis.class_late_premium("cube", fix)
    log(f"fixing class (cube): within-card late premium {d1:+.2f}pp (se {s1:.2f}, {n1} cards) "
        f"vs others {d2:+.2f}pp (se {s2:.2f}, {n2}); diff {d1 - d2:+.2f} "
        f"(se {np.sqrt(s1 ** 2 + s2 ** 2):.2f}) — binomial SEs, no draft clustering")
    (OUT / "robustness.md").write_text("\n".join(lines))
    print(f"\nwrote {OUT / 'robustness.md'}")


# ---------------------------------------------------------------- report ----
def cmd_report():
    import base64
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    KAPPA = metrics.KAPPA
    # re-pricing panel GP slopes per ALSA pick (cmd_panels; documented constants)
    PANEL = {"sos": (0.35, 0.09), "fin": (0.42, 0.07),
             "tla": (0.67, 0.11), "cube": (0.70, 0.48)}
    # SOS GNS panel raw / archetype-week-adjusted (studies/congestion_test.py)
    PANEL_GNS = {"raw": (0.59, 0.11), "arch_adj": (0.15, 0.12)}

    INK, PAPER, CRIM, FADE = "#2b2622", "#faf6ee", "#a4282e", "#8a8074"
    plt.rcParams.update({
        "figure.facecolor": PAPER, "axes.facecolor": PAPER, "savefig.facecolor": PAPER,
        "text.color": INK, "axes.edgecolor": INK, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "font.family": "Georgia",
        "axes.spines.top": False, "axes.spines.right": False, "font.size": 11})
    figs = {}

    fmts = ["sos", "fin", "tla", "cube"]
    names = {"sos": "SOS", "fin": "FIN", "tla": "TLA", "cube": "Cube"}
    cells = {f: data.aspicked(f) for f in fmts}

    fig, ax = plt.subplots(figsize=(8.6, 3.4))
    x = np.arange(4)
    ax.bar(x - 0.18, [PANEL[f][0] / KAPPA for f in fmts], 0.32,
           yerr=[PANEL[f][1] / KAPPA for f in fmts], capsize=3, color=FADE,
           label="Weekly re-pricing panel (stat tables)")
    ax.bar(x + 0.18, [analysis.within_card(cells[f], "gp_wr", "n_gp")[1] for f in fmts],
           0.32, color=CRIM, label="As-picked comparison (draft logs)")
    ax.set_xticks(x); ax.set_xticklabels([names[f] for f in fmts])
    ax.set_ylabel("GP WR, pp per pick taken later")
    ax.set_title("Two estimates of the slept-on boost (same units)",
                 loc="left", fontsize=13, fontweight="bold")
    ax.legend(frameon=False, fontsize=9); ax.axhline(0, color=INK, lw=0.6)
    fig.tight_layout(); figs["FIG_E2E4"] = fig

    fig, ax = plt.subplots(figsize=(8.6, 3.0))
    _, beta, se = analysis.within_card(cells["sos"], "gns_wr", "n_gns")
    vals = [PANEL_GNS["raw"][0] / KAPPA, PANEL_GNS["arch_adj"][0] / KAPPA, beta]
    errs = [PANEL_GNS["raw"][1] / KAPPA, PANEL_GNS["arch_adj"][1] / KAPPA, se]
    ax.barh([2, 1, 0], vals, xerr=errs, capsize=3, color=[FADE, CRIM, INK], height=0.55)
    ax.set_yticks([2, 1, 0])
    ax.set_yticklabels(["Re-pricing panel,\nraw GNS WR",
                        "Re-pricing panel,\nminus archetype-week WR",
                        "As-picked estimate\n(independent design)"], fontsize=10)
    ax.set_xlabel("GNS WR, pp per pick taken later (SOS)")
    ax.set_title("Most of a discovered card's stat decline is its archetype's tide",
                 loc="left", fontsize=13, fontweight="bold")
    fig.tight_layout(); figs["FIG_CONGESTION"] = fig

    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.2))
    examples = {"sos": [("Fix What's Broken", CRIM), ("Stock Up", INK)],
                "cube": [("Omnath, Locus of Creation", CRIM), ("Lightning Bolt", INK)]}
    for ax, (tag, cds) in zip(axes, examples.items()):
        for nm, c in cds:
            g = cells[tag][cells[tag].name == nm].sort_values("pick_mid")
            ax.plot(g.pick_mid, g.md_rate * 100, "-o", color=c, ms=4, label=nm)
        ax.set_xlabel("pick taken at"); ax.set_ylim(0, 100)
        ax.set_title(names[tag], loc="left", fontsize=11, fontweight="bold")
        ax.legend(frameon=False, fontsize=8.5)
    axes[0].set_ylabel("maindeck rate %")
    fig.suptitle("The deployment filter: who still gets played when taken late",
                 x=0.01, ha="left", fontsize=13, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.93]); figs["FIG_FILTER"] = fig

    fig, ax = plt.subplots(figsize=(8.6, 3.6))
    styles = {"sos": (INK, "-"), "fin": (FADE, "-"), "tla": (FADE, "--"), "cube": (CRIM, "-")}
    for f, (c, ls) in styles.items():
        curve, _, _ = analysis.within_card(cells[f], "gp_wr", "n_gp")
        curve = curve - curve.iloc[0]
        ax.plot(curve.index, curve.values * 100, ls, color=c, marker="o", ms=4,
                label=names[f])
    ax.set_xlabel("pick the card was taken at")
    ax.set_ylabel("GP WR vs same card taken pick 1 (pp)")
    ax.set_title("The lateness premium by position (within-card, card FE)",
                 loc="left", fontsize=13, fontweight="bold")
    ax.legend(frameon=False, fontsize=9); ax.axhline(0, color=INK, lw=0.6)
    fig.tight_layout(); figs["FIG_CURVE"] = fig

    html = (HERE / "report_template.html").read_text()
    for key, fig in figs.items():
        p = OUT / f"_{key.lower()}.png"
        fig.savefig(p, dpi=160)
        html = html.replace("{{%s}}" % key, base64.b64encode(p.read_bytes()).decode())
        p.unlink()
    assert "{{" not in html, "unfilled placeholder in template"
    (HERE / "slept_on_cards_report.html").write_text(html)
    print("report built")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd, args = sys.argv[1], sys.argv[2:]
    fns = {"prep": cmd_prep, "slopes": cmd_slopes, "cards": cmd_cards,
           "insights": cmd_insights, "panels": cmd_panels,
           "robustness": cmd_robustness, "report": cmd_report}
    if cmd not in fns:
        print(__doc__)
        sys.exit(1)
    fns[cmd](*args)


if __name__ == "__main__":
    main()
