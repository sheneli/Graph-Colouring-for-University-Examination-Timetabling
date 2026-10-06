"""Generate all figures from saved result files (no experiment is re-run).

Palette: validated categorical order from the project's data-visualisation guidance
(blue, orange, aqua, yellow), with hatching as secondary encoding for print/CVD.
Each figure's plotted data are written next to it as CSV (figures/data/).
"""

from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import FIGURES, ROOT

# Set in main() from the command line: v1 (results/, TBR) or v2 (results/v2/, TBRPLUS).
RESULTS = ROOT / "results"
AN = RESULTS / "analysis"
DATA = FIGURES / "data"
M = "TBR"          # proposed method plotted
SUFFIX = ""        # appended to every figure name
COL = {"TBR": "#2a78d6", "TBRPLUS": "#2a78d6", "SINGLE": "#eb6834", "ONE_BLOCKER": "#1baf7a",
       "RECOMPUTE": "#eda100"}
HATCH = {"TBR": "", "TBRPLUS": "", "SINGLE": "//", "ONE_BLOCKER": "..", "RECOMPUTE": "xx"}
LABEL = {"TBR": "TBR (v1, B = 8)", "TBRPLUS": "TBR+ (v2, B = 8)", "SINGLE": "Single-move repair",
         "ONE_BLOCKER": "One-blocker repair", "RECOMPUTE": "Full recomputation"}
SHORT = {"car-f-92": "car92", "car-s-91": "car91", "ear-f-83": "ear83", "hec-s-92": "hec92",
         "kfu-s-93": "kfu93", "lse-f-91": "lse91", "pur-s-93": "pur93", "rye-s-93": "rye93",
         "sta-f-83": "sta83", "tre-s-92": "tre92", "uta-s-92": "uta92", "ute-s-92": "ute92",
         "yor-f-83": "yor83"}
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "legend.frameon": False, "figure.dpi": 200, "savefig.bbox": "tight",
})


def save(fig, name, data: pd.DataFrame):
    FIGURES.mkdir(exist_ok=True)
    DATA.mkdir(exist_ok=True)
    fig.savefig(FIGURES / f"{name}{SUFFIX}.png")
    plt.close(fig)
    data.to_csv(DATA / f"{name}{SUFFIX}.csv", index=False)


def fig_static():
    s = pd.read_csv(AN / "static_colours.csv")
    order = s.sort_values("n").instance.tolist()
    s = s.set_index("instance").loc[order].reset_index()
    cons = ["first_fit", "welsh_powell", "smallest_last", "dsatur", "rlf"]
    names = {"first_fit": "First-fit", "welsh_powell": "Welsh–Powell", "smallest_last": "Smallest-last",
             "dsatur": "DSATUR", "rlf": "RLF"}
    colors = ["#9b9a95", "#eb6834", "#1baf7a", "#2a78d6", "#eda100"]
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    x = np.arange(len(order))
    w = 0.16
    for i, c in enumerate(cons):
        ax.bar(x + (i - 2) * w, s[c], w * 0.9, color=colors[i], label=names[c], linewidth=0)
    ax.scatter(x, s["official_periods"], marker="_", s=180, color=INK, label="Published periods", zorder=3)
    ax.scatter(x, s["clique_lb"], marker="v", s=14, color=MUTED, label="Clique lower bound", zorder=3)
    ax.set_xticks(x, [SHORT[i] for i in order], rotation=0)
    ax.set_ylabel("Periods (colours) used")
    ax.legend(ncol=4, fontsize=7.5, loc="upper left")
    ax.set_ylim(0, max(s["first_fit"]) * 1.25)
    save(fig, "fig_static_colours", s[["instance", *cons, "official_periods", "clique_lb"]])


def fig_moved():
    a = pd.read_csv(AN / "per_instance_method.csv")
    a = a[a.condition == "tight"]
    order = sorted(a.instance.unique(), key=lambda i: SHORT[i])
    meths = [M, "SINGLE", "ONE_BLOCKER", "RECOMPUTE"]
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    x = np.arange(len(order))
    w = 0.2
    rows = []
    for i, m in enumerate(meths):
        v = a[a.method == m].set_index("instance").loc[order, "D_median"]
        ax.bar(x + (i - 1.5) * w, v, w * 0.9, color=COL[m], hatch=HATCH[m], edgecolor="white",
               linewidth=0, label=LABEL[m])
        rows += [{"instance": o, "method": m, "median_total_moved": float(val)} for o, val in zip(order, v)]
    ax.set_yscale("log")
    ax.set_xticks(x, [SHORT[i] for i in order])
    ax.set_ylabel("Exams moved per stream\n(median of 10 seeds, log scale)")
    ax.legend(ncol=2, fontsize=7.5, loc="upper left")
    ax.set_ylim(1, 1e4)
    save(fig, "fig_exams_moved", pd.DataFrame(rows))


def fig_periods():
    s = pd.read_csv(RESULTS / "stream_summary.csv")
    meths = [M, "SINGLE", "ONE_BLOCKER", "RECOMPUTE"]
    g = s[s.method.isin(meths)].groupby(["condition", "method"]).periods_added.sum().unstack(0)
    g = g.loc[meths]
    fig, ax = plt.subplots(figsize=(5.2, 2.6))
    x = np.arange(2)
    w = 0.2
    for i, m in enumerate(meths):
        v = [g.loc[m, "tight"], g.loc[m, "official"]]
        bars = ax.bar(x + (i - 1.5) * w, v, w * 0.9, color=COL[m], hatch=HATCH[m], edgecolor="white",
                      linewidth=0, label=LABEL[m])
        for b, val in zip(bars, v):
            ax.text(b.get_x() + b.get_width() / 2, val + 1, f"{int(val)}", ha="center", fontsize=7, color=INK)
    ax.set_xticks(x, ["Tight session", "Published session"])
    ax.set_ylabel("Extra periods opened\n(sum over 130 streams)")
    ax.legend(fontsize=7, loc="upper right")
    save(fig, "fig_periods_added", g.reset_index())


def fig_latency():
    lat = pd.read_csv(AN / "latency_clash_events.csv")
    order = sorted(lat.instance.unique(), key=lambda i: SHORT[i])
    fig, ax = plt.subplots(figsize=(7.2, 2.8))
    x = np.arange(len(order))
    rows = []
    for m, off in [(M, -0.15), ("RECOMPUTE", 0.15)]:
        d = lat[lat.method == m].set_index("instance").loc[order]
        ax.bar(x + off, d["median"] / 1000, 0.28, color=COL[m], hatch=HATCH[m], edgecolor="white",
               linewidth=0, label=f"{LABEL[m]}: median")
        ax.errorbar(x + off, d["median"] / 1000, yerr=[np.zeros(len(d)), (d["p95"] - d["median"]) / 1000],
                    fmt="none", ecolor=MUTED, elinewidth=0.8, capsize=2)
        rows += [{"instance": o, "method": m, "median_ms": md / 1000, "p95_ms": p / 1000}
                 for o, md, p in zip(order, d["median"], d["p95"])]
    ax.set_yscale("log")
    ax.set_xticks(x, [SHORT[i] for i in order])
    ax.set_ylabel("Repair latency per clash (ms, log)\nbar = median, whisker = 95th pct.")
    ax.legend(fontsize=7.5, loc="upper left")
    save(fig, "fig_latency", pd.DataFrame(rows))


def fig_tiers():
    s = pd.read_csv(RESULTS / "stream_summary.csv")
    keys = ["n_single", "n_double", "n_kempe", "n_search", "n_new"]
    if "n_search" not in s:
        s["n_search"] = 0
    t = s[s.method == M].groupby("condition")[keys].sum()
    rows = [("Pre-registered, tight", t.loc["tight"]), ("Pre-registered, published", t.loc["official"])]
    stress = ROOT / "results" / ("stress_summary.csv" if M == "TBR" else "stress_v2_summary.csv")
    if stress.exists():
        st = pd.read_csv(stress)
        if "n_search" not in st:
            st["n_search"] = 0
        rows.append(("Exploratory stress (T = 2000)", st[st.method == M][keys].sum()))
    labels = ["Single move", "Double move", "Kempe chain", "Bounded search", "New period"]
    cols = ["#2a78d6", "#1baf7a", "#4a3aa7", "#9b9a95", "#eb6834"]
    fig, ax = plt.subplots(figsize=(6.4, 2.2))
    data = []
    for yi, (name, r) in enumerate(rows):
        tot = r.sum()
        left = 0
        for j, key in enumerate(keys):
            share = r[key] / tot
            ax.barh(yi, share, left=left, color=cols[j], height=0.55, edgecolor="white", linewidth=1.5,
                    label=labels[j] if yi == 0 else None)
            if share > 0.04:
                ax.text(left + share / 2, yi, f"{share:.0%}", ha="center", va="center", color="white", fontsize=7)
            left += share
        data.append({"scenario": name, **{k: int(r[k]) for k in r.index}, "total": int(tot)})
    ax.set_yticks(range(len(rows)), [r[0] for r in rows])
    ax.invert_yaxis()
    ax.set_xlim(0, 1)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.set_xlabel(f"Share of clash events resolved by each tier ({LABEL[M].split(' (')[0]})")
    ax.legend(ncol=5, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.35))
    ax.grid(axis="y", visible=False)
    save(fig, "fig_tiers", pd.DataFrame(data))


def fig_scaling():
    sl = pd.read_csv(AN / "scaling_latency.csv")
    fig, ax = plt.subplots(figsize=(4.8, 2.8))
    for m in [M, "RECOMPUTE"]:
        d = sl[sl.method == m].sort_values("n")
        ax.plot(d.n, d["median"] / 1000, marker="o", ms=4, lw=2, color=COL[m], label=LABEL[m])
        ax.annotate(f"{d['median'].iloc[-1] / 1000:.2g} ms", (d.n.iloc[-1], d["median"].iloc[-1] / 1000),
                    textcoords="offset points", xytext=(4, 4), fontsize=7, color=INK)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Number of exams n (synthetic, log)")
    ax.set_ylabel("Median latency per clash (ms, log)")
    ax.legend(fontsize=7.5)
    save(fig, "fig_scaling", sl)


def fig_budget():
    s = pd.read_csv(RESULTS / "stream_summary.csv")
    meth = {"TBR_B2": 2, "TBR_B4": 4, "TBR": 8, "TBR_B16": 16, "TBR_B32": 32}
    d = s[(s.method.isin(meth)) & (s.condition == "tight")].groupby("method").agg(
        added=("periods_added", "sum"), moved=("total_D", "sum")).reset_index()
    d["B"] = d.method.map(meth)
    d = d.sort_values("B")
    fig, ax = plt.subplots(figsize=(4.8, 2.6))
    ax.plot(d.B, d.added, marker="o", lw=2, color=COL["TBR"])
    for b, a in zip(d.B, d.added):
        ax.annotate(f"{int(a)}", (b, a), textcoords="offset points", xytext=(0, 6), ha="center", fontsize=7)
    ax.set_xscale("log", base=2)
    ax.set_xticks(d.B, [str(b) for b in d.B])
    ax.set_xlabel("Budget B (max exams moved per event)")
    ax.set_ylabel("Extra periods opened\n(tight, 130 streams)")
    ax.set_ylim(0, d.added.max() * 1.25)
    save(fig, "fig_budget", d)


def main():
    global RESULTS, AN, M, SUFFIX
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--version", choices=["v1", "v2"], default="v1",
                    help="v1: results/ with TBR (seeds 0-9); v2: results/v2/ with TBR+ (seeds 10-19)")
    v = ap.parse_args().version
    if v == "v2":
        RESULTS, M, SUFFIX = ROOT / "results" / "v2", "TBRPLUS", "_v2"
    AN = RESULTS / "analysis"
    fig_static()
    fig_moved()
    fig_periods()
    fig_latency()
    fig_tiers()
    fig_scaling()
    if v == "v1":
        fig_budget()      # budget ablations were run for v1 only
    print("figures written to", FIGURES)


if __name__ == "__main__":
    main()
