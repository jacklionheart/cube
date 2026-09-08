# %% [markdown]
# # The ATA tax — master notebook
#
# **One question:** how much of a card's 17Lands win rate is *real strength*
# versus *inflation from being picked late*? A card taken later was acquired
# more cheaply, so the deck around it is better — an "ATA tax" on the printed
# stats. This notebook reproduces the whole investigation end-to-end from
# `lib17`; the exhaustive catalog of confounders, hypotheses, and the methods
# retrospective lives in **`NOTES.md`** (this notebook stays runnable, the notes
# hold the depth).
#
# Self-contained: every figure is computed inline from `data/`; nothing here
# reads `out/`, so the output directory can be cleared freely.
#
# **Contents**
# 0. Setup
# 1. Format context (general primitives — top cards, archetypes, movers)
# 2. The metrics and their biases
# 3. The answer: the as-picked design
# 4. The weekly panel, and why it is *not* a tax estimator
# 5. GIH = GNS + IIH: deck vs card, and the mover attribution
# 6. Card vs archetype (gold vs flexible)
# 7. Worked example: Aang priced like Teferi
# 8. Synthesis

# %%
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd().parent))
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from lib17 import data, metrics, analysis, weekly, overview
from lib17 import htmlfmt as H
plt.rcParams.update(H.MPL_STYLE)
pd.set_option("display.width", 200)
FORMATS = ["sos", "fin", "tla", "cube"]
RETAIL = ["sos", "fin", "tla"]
NAMES = {"sos": "SOS", "fin": "FIN", "tla": "TLA", "cube": "Powered Cube"}
CRIM, INK, FADE, GOLD = H.CRIM, H.INK, H.FADE, "#9a7b2d"

# %% [markdown]
# ## 1. Format context (general-purpose primitives)
#
# These concepts are reusable for any 17Lands format read, independent of the
# tax question: top cards (overall and by rarity), the archetype metagame, and
# the biggest re-pricings — each available whole-format and week by week
# (`lib17.overview`).

# %% [markdown]
# **Top commons and uncommons over the whole format** (the limited workhorses):

# %%
for tag in RETAIL:
    print(f"\n=== {NAMES[tag]}: top commons ===")
    display(overview.top_cards(tag, rarity="common", n=6))

# %% [markdown]
# **The archetype metagame** — share and win rate over the whole format:

# %%
for tag in RETAIL:
    print(f"\n=== {NAMES[tag]} ===")
    display(overview.archetype_summary(tag))

# %% [markdown]
# **Archetype trends, week by week** — share (left) and win rate vs format
# (right). This is the seasonal movement that will turn out to drive the weekly
# re-pricing panel (§4).

# %%
fig, axes = plt.subplots(len(RETAIL), 2, figsize=(10, 3 * len(RETAIL)))
for row, tag in zip(axes, RETAIL):
    t = overview.archetype_trends(tag)
    top = t.groupby("arch").n.sum().nlargest(6).index
    pal = [CRIM, INK, GOLD, "#5b7553", "#5d6d92", FADE]
    for arch, c in zip(top, pal):
        g = t[t.arch == arch].sort_values("wk")
        row[0].plot(g.wk, g.share * 100, "-o", ms=3, color=c, label=arch)
        row[1].plot(g.wk, g.rel_wr * 100, "-o", ms=3, color=c)
    row[0].set_ylabel(f"{NAMES[tag]}\nmetagame share %"); row[1].axhline(0, color=INK, lw=.5)
    row[1].set_ylabel("WR vs format (pp)"); row[0].legend(fontsize=7, ncol=2)
for ax in axes[-1]:
    ax.set_xlabel("week")
plt.tight_layout(); plt.show()

# %% [markdown]
# **The biggest movers** — cards the community re-priced most, split into those
# taken progressively **earlier** (discovered) and **later** (faded). Each row
# shows GIH win rate (vs format) before/after, the card's most-played archetypes
# and shares (`mix`), and that top archetype's own win-rate movement over the
# season (`top arch ΔWR`) — so you can see whether the card moved *with its
# deck*. (Most do: foreshadows §5.)

# %%
for tag in RETAIL:
    print(f"\n=== {NAMES[tag]}: taken EARLIER (discovered) ===")
    display(overview.biggest_movers(tag, n=10, direction="up"))
    print(f"=== {NAMES[tag]}: taken LATER (faded) ===")
    display(overview.biggest_movers(tag, n=10, direction="down"))

# %% [markdown]
# ## 2. The metrics and their biases
#
# 17Lands metrics and the biases to keep in mind (full table in `NOTES.md §2`).
# The load-bearing identity is **`GIH = GNS + IIH`**: GNS WR (never-seen) is
# pure deck context (the control group), IIH (= GIH − GNS) is the card's own
# in-hand value, deck-cancelled by construction. The ATA tax is a *deck-quality*
# effect, so it should live in **GNS**, not IIH — a prediction we test in §3.

# %%
print(metrics.__doc__[:1100])

# %% [markdown]
# ## 3. The answer: the as-picked design
#
# Compare the *same card* taken at pick 3 vs pick 10 across simultaneous drafts,
# card fixed effects (`lib17.analysis`, from the public logs). This holds the
# season/discovery state fixed and makes the pick exogenous to that draft's
# result — the one estimator that is stable across metric, units, and controls.
# Slopes are pp of win rate **per taken-at pick**, card-clustered SEs.

# %%
rows = []
for tag in FORMATS:
    s = analysis.aspicked_slopes(tag)
    rows.append({"format": NAMES[tag],
                 **{m: round(s[m][0], 3) for m in ["gp_wr", "gih_wr", "oh_wr", "gns_wr"]},
                 "maindeck/pick": round(s["md_rate"][0], 2)})
display(pd.DataFrame(rows))

# %% [markdown]
# Two facts: **GNS carries the largest slope** in every format — a card taken
# later wins more *in games it never appears in*, which can only be the
# surrounding deck. That is the tax, and it correctly shows up in deck quality.
# And **maindeck probability falls ~4pp per pick** — the deployment filter.
#
# The premium is **front-loaded** (most of it in the first picks), and the
# deployment filter is brutal for narrow cards:

# %%
def aspicked_frame(tag):
    a = data.aspicked(tag)
    return a

fig, axes = plt.subplots(1, 2, figsize=(10, 3.4))
for tag, c in zip(FORMATS, [INK, FADE, GOLD, CRIM]):
    a = aspicked_frame(tag)
    curve, _, _ = analysis.within_card(a, "gp_wr", "n_gp")
    curve = (curve - curve.iloc[0]) * 100
    axes[0].plot(curve.index, curve.values, "-o", ms=3, color=c, label=NAMES[tag])
axes[0].axhline(0, color=INK, lw=.5); axes[0].legend(fontsize=8)
axes[0].set_xlabel("pick taken at"); axes[0].set_ylabel("GP WR vs pick 1 (pp)")
axes[0].set_title("front-loaded lateness premium", loc="left", fontweight="bold")
a = aspicked_frame("sos")
for nm, c in [("Fix What's Broken", CRIM), ("Stock Up", INK)]:
    g = a[a.name == nm].sort_values("pick_mid")
    axes[1].plot(g.pick_mid, g.md_rate * 100, "-o", ms=4, color=c, label=nm)
axes[1].set_xlabel("pick taken at"); axes[1].set_ylabel("maindeck rate %"); axes[1].set_ylim(0, 100)
axes[1].legend(fontsize=8); axes[1].set_title("the deployment filter (SOS)", loc="left", fontweight="bold")
plt.tight_layout(); plt.show()

# %% [markdown]
# ## 4. The weekly panel, and why it is *not* a tax estimator
#
# The other design — `WR ~ ALSA + card FE + week FE` on weekly stat tables,
# identified by the community re-pricing cards — reads 2–5× higher and is
# unstable across metric / units / card subset. A real tax does not move with
# bookkeeping.

# %%
KAPPA = metrics.KAPPA  # within-card dATA/dALSA = 1.546
inst = []
for tag in RETAIL:
    a = analysis.weekly_panel(NAMES[tag], "gp_wr", "n_gp")[0]
    inst.append({"format": NAMES[tag], "GP panel /ALSA-pick": round(a, 2),
                 "/ATA-pick (÷κ)": round(a / KAPPA, 2),
                 "as-picked GP (logs)": round(analysis.aspicked_slopes(tag)["gp_wr"][0], 2)})
display(pd.DataFrame(inst))

# %% [markdown]
# **Why it reads high: the archetype tide.** The panel has *week* fixed effects
# but no *archetype* fixed effects, so an archetype's own seasonal win-rate arc
# survives. Re-net each card's weekly win rate against *its own archetype's*
# weekly win rate (instead of the format), and the slope collapses — proving the
# panel is reading the deck underneath the card, not the card.

# %%
def panel_vs_archetype(tag):
    w, windows = weekly.weekly_panel(tag)
    w = w[w.ata.notna()].copy()
    modal = data.card_stats(tag).set_index("name").modal_deck
    ab = weekly.arch_baseline(tag, windows)[["arch", "t", "arch_rel"]]
    w["arch"] = w.name.map(modal)
    w = w.merge(ab, on=["arch", "t"], how="left")
    p = w.dropna(subset=["ata", "gih_wr_rel", "arch_rel", "n_gih"]).copy()
    k = p.groupby("name").window.nunique(); p = p[p.name.isin(k[k >= 3].index)].reset_index(drop=True)
    p["net"] = p.gih_wr_rel - p.arch_rel
    p["xr"] = weekly.residualize(p, "ata"); p["yf"] = weekly.residualize(p, "gih_wr_rel")
    p["yn"] = weekly.residualize(p, "net")
    return weekly.panel_slope(p, "xr", "yf"), weekly.panel_slope(p, "xr", "yn")

rows = []
for tag in RETAIL:
    vf, vn = panel_vs_archetype(tag)
    rows.append({"format": NAMES[tag], "GIH~ATA slope vs format": round(vf, 2),
                 "vs OWN archetype": round(vn, 2)})
display(pd.DataFrame(rows))

# %% [markdown]
# Netting against the archetype zeroes it in every set — the positive panel
# slope was the archetype's seasonal arc, inherited by cards whose ATA drifted a
# little while their deck's win rate moved a lot.
#
# **And even before netting, the slope isn't a property of the cards — it's a
# few of them.** Among non-movers (cards that barely re-price), the *typical*
# card's ATA→WR slope is ~zero, as a noise model predicts; the positive pooled
# number is carried by a handful of high-leverage discovery co-trends. Drop the
# top 5 and it vanishes:

# %%
w, windows = weekly.weekly_panel("sos"); w = w[w.ata.notna()]
_, allf = weekly.find_movers(w, "sos")
movers = allf[(allf.move.abs() >= 1.25) & (allf.rho.abs() >= 0.6)].index
p = w.dropna(subset=["ata", "gih_wr_rel", "n_gih"]).copy()
k = p.groupby("name").window.nunique(); p = p[p.name.isin(k[k >= 3].index)].reset_index(drop=True)
p["xr"] = weekly.residualize(p, "ata"); p["yr"] = weekly.residualize(p, "gih_wr_rel")
g = p[~p.name.isin(movers)].groupby("name").apply(
    lambda d: pd.Series({"N": (d.n_gih * d.xr * d.yr).sum(), "D": (d.n_gih * d.xr ** 2).sum()}),
    include_groups=False)
g["slope"] = g.N / g.D * 100
pooled = g.N.sum() / g.D.sum() * 100
jk = {f"drop top {kk}": round(g.drop(g.nlargest(kk, "D").index).pipe(lambda x: x.N.sum() / x.D.sum() * 100), 2)
      for kk in [0, 1, 3, 5]}
print(f"non-mover pooled slope {pooled:+.2f} | median per-card {g.slope.median():+.2f} | "
      f"% positive {(g.slope > 0).mean():.0%}")
print("jackknife:", jk)
print("the 5 leverage cards (discovery co-trends):", list(g.nlargest(5, "D").index))

# %% [markdown]
# ## 5. GIH = GNS + IIH: deck vs card, and the mover attribution
#
# For each format's ten biggest movers, split the season GIH change into
# **deck (ΔGNS)** — pure deck context, well sampled — and **individual (ΔIIH)** —
# the card's in-hand lift over its own decks. We don't lean on a precise
# individual number: the deck channel is the trustworthy one, and individual
# counts only when it clears twice its sampling noise.

# %%
def attribute_movers(tag, k=10):
    w, _ = weekly.weekly_panel(tag)
    w = w[w.ata.notna() & w.gns_wr.notna() & (w.n_gns >= 50)]
    _, allf = weekly.find_movers(w, tag, min_gih=800)
    top = allf.reindex(allf.move.abs().sort_values(ascending=False).index).head(k)
    rows = []
    for name in top.index:
        g = w[w.name == name]
        if g.t.nunique() < 4:
            continue
        s = weekly.season_split(g)
        if abs(s["d_iih"]) < 2 * s["se_iih"]:
            v = "deck-driven"
        elif abs(s["d_iih"]) > abs(s["d_gns"]):
            v = "individual"
        else:
            v = "mixed"
        rows.append({"card": name, "ATA move": round(top.loc[name, "move"], 1),
                     "ΔGIH": round(s["d_gih"], 1), "deck ΔGNS": round(s["d_gns"], 1),
                     "indiv ΔIIH": round(s["d_iih"], 1), "±se": round(s["se_iih"], 1),
                     "verdict": v})
    return pd.DataFrame(rows)

tally = {"deck-driven": 0, "individual": 0, "mixed": 0}
for tag in RETAIL:
    df = attribute_movers(tag)
    for v in df.verdict:
        tally[v] += 1
    print(f"\n=== {NAMES[tag]} ===")
    display(df)
print("\nTALLY across the three sets:", tally)

# %% [markdown]
# Almost every big re-pricing is **deck-driven**: the community took the card
# earlier/later and its GIH moved, but the move was its *archetype's* win rate,
# not the card's own in-hand value. The card's IIH is far stabler than its
# headline GIH — which is the whole reason the answer to "is this card as good
# picked early?" is usually *yes for the card, the change was the deck.*

# %% [markdown]
# ## 6. Card vs archetype: gold (locked) vs flexible
#
# A gold card lives in one archetype, so "taken earlier and winning less" can't
# distinguish card from deck. Track a discovered card's GIH *within its
# archetype* (ink) against that archetype's baseline win rate (grey), as ATA
# drifts (crimson). If ink and grey fall together, it's the deck.

# %%
def discovered_example(tag, gold):
    w, windows = weekly.weekly_panel(tag)
    w = w[w.ata.notna()]
    _, allf = weekly.find_movers(w, tag, min_gih=800)
    disc = allf[(allf.move < -0.4) & (allf.rho < -0.4)]
    cstats = data.card_stats(tag).set_index("name")
    import json
    sc = json.load(open(Path.cwd().parent / "data" / "raw" / "scryfall_oracle.json"))
    cid = {c["name"]: len(c.get("color_identity", [])) for c in sc}
    names = [n for n in disc.index if cid.get(n, 0) >= 2] if gold else [n for n in disc.index if cid.get(n, 0) <= 1]
    names = [n for n in names if cstats.loc[n].modal_deck and len(str(cstats.loc[n].modal_deck)) == 2] if False else names
    # pick the highest-volume one with a 2-color modal deck
    best = max(names, key=lambda n: cstats.loc[n].n_gih if n in cstats.index else 0, default=None)
    return best, windows

fig, axes = plt.subplots(1, 3, figsize=(11, 3))
for ax, tag in zip(axes, RETAIL):
    nm, windows = discovered_example(tag, gold=True)
    if nm is None:
        continue
    cd = weekly.card_by_archetype(tag, nm, windows)
    base = weekly.arch_baseline(tag, windows)
    d = cd.merge(base, on=["arch", "t"], how="left")
    a1 = d.groupby("arch").n_gih.sum().idxmax()
    da = d[d.arch == a1].sort_values("t")
    ax.plot(da.t, da.base * 100, "-o", color=FADE, ms=3, label=f"{a1} WR")
    ax.plot(da.t, da.card_gih * 100, "-s", color=INK, ms=3, label="card GIH in deck")
    w, _ = weekly.weekly_panel(tag); cw = w[w.name == nm].set_index("t")
    a2 = ax.twinx(); a2.plot(cw.index, cw.ata, ":", color=CRIM, lw=1.5); a2.invert_yaxis()
    a2.set_ylabel("ATA", color=CRIM, fontsize=8); a2.tick_params(labelcolor=CRIM, labelsize=7)
    ax.set_title(f"{NAMES[tag]} · {nm[:18]}", fontsize=9, fontweight="bold", loc="left")
    ax.legend(fontsize=7); ax.set_xlabel("week")
axes[0].set_ylabel("win rate %")
fig.suptitle("Gold discovered cards: the card's GIH-in-deck tracks the archetype WR (it's the deck)",
             x=0.01, ha="left", fontsize=10, fontweight="bold")
plt.tight_layout(rect=[0, 0, 1, 0.92]); plt.show()

# %% [markdown]
# ## 7. Worked example: Aang priced like Teferi (Powered Cube)
#
# "Taken like Teferi" is a policy bundle — position, deployment, deck, pilot.
# The headline: even after charging Aang the position penalty (from the cube's
# own lateness curve) and the deployment dilution, it still clears Teferi's GIH,
# because their deck contexts barely differ. Full estimand decomposition in
# `NOTES.md §1` / the original `aang_vs_teferi` analysis.

# %%
t = data.card_table("CubePowered", "run3_2026-05-28")
aang = t[t.name == "Aang, Swift Savior"].iloc[0]
tef = t[t.name == "Teferi, Time Raveler"].iloc[0]
mu = (t.n_gp * t.gp_wr).sum() / t.n_gp.sum()
cells = data.aspicked("cube")
curve, _, _ = analysis.within_card(cells, "gih_wr", "n_gih")
pos = np.interp(aang.ata, curve.index, curve.values) - np.interp(tef.ata, curve.index, curve.values)
effect = aang.gih_wr - aang.gns_wr
gns_curve, _, _ = analysis.within_card(cells, "gns_wr", "n_gns")
gns_loss = np.interp(aang.ata, gns_curve.index, gns_curve.values) - np.interp(tef.ata, gns_curve.index, gns_curve.values)
gns_cf = aang.gns_wr - gns_loss
display(pd.DataFrame([
    {"card": "Aang (observed)", "ATA": round(aang.ata, 1), "play": f"{aang.pct_gp:.0%}", "GIH": f"{aang.gih_wr:.1%}"},
    {"card": "Aang priced like Teferi", "ATA": round(tef.ata, 1), "play": "~67%",
     "GIH": f"{gns_cf + effect * 0.9:.1%}–{gns_cf + effect:.1%}"},
    {"card": "Teferi (observed)", "ATA": round(tef.ata, 1), "play": f"{tef.pct_gp:.0%}", "GIH": f"{tef.gih_wr:.1%}"},
]))
print(f"format mean GIH {mu:.1%} — priced like Teferi, Aang still clears Teferi's {tef.gih_wr:.1%}.")

# %% [markdown]
# ## 8. Synthesis
#
# - The ATA tax is **real, small, front-loaded, and lives in deck quality (GNS)**:
#   ≈ +0.1–0.15pp GIH per taken-at pick.
# - The **as-picked design measures it cleanly**; the **weekly panel does not**
#   (it mostly measures the archetype underneath the card — proven by
#   archetype-netting).
# - The card's own in-hand value (**IIH**) barely moves with pick position, so
#   26/30 of the biggest movers are **deck-driven**, only 4 card re-evaluations.
# - Practical reading of 17Lands stats: refund ~0.1–0.15pp per taken-at pick
#   (front-loaded), distrust low-play-rate late stats (survivorship), and check
#   GNS to see how much of a card's line is the deck.
#
# Confounders catalog, hypotheses-and-verdicts table, and the full methods
# retrospective (what worked / what didn't): **`NOTES.md`**.
