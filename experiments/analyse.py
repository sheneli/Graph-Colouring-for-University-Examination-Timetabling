"""Analysis of saved results: statistics, requirement coverage and report tables.

Reads only files in results/ and writes results/analysis/*. No experiment is re-run here.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

from common import ROOT, load_config, out_dir, save_json

B = 8
BUDGETS = {"TBR": 8, "TBR_NOPROX": 8, "TBR_NOT2": 8, "TBR_B2": 2, "TBR_B4": 4, "TBR_B16": 16,
           "TBR_B32": 32, "SINGLE": 8, "ONE_BLOCKER": 8, "TBRPLUS": 8, "TBRPLUS_N20000": 8}


def holm(pvals):
    """Holm-Bonferroni adjusted p-values (NaN kept)."""
    p = np.array(pvals, dtype=float)
    idx = [i for i in range(len(p)) if not np.isnan(p[i])]
    order = sorted(idx, key=lambda i: p[i])
    m = len(order)
    adj = np.full(len(p), np.nan)
    running = 0.0
    for rank, i in enumerate(order):
        val = min(1.0, (m - rank) * p[i])
        running = max(running, val)
        adj[i] = running
    return adj


def q(x, a):
    return float(np.quantile(x, a)) if len(x) else float("nan")


def paired_test(x, y):
    d = np.asarray(x, float) - np.asarray(y, float)
    if np.all(d == 0):
        return float("nan"), "no difference"
    res = wilcoxon(x, y)  # SciPy defaults: two-sided, zero_method='wilcox', method='auto'
    return float(res.pvalue), "wilcoxon"


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(ROOT / "configs" / "experiment.toml"))
    ap.add_argument("--method", default="TBR", help="proposed method evaluated for RC")
    args = ap.parse_args()
    M = args.method
    cfg = load_config(args.config)
    RESULTS = out_dir(cfg)
    OUT = RESULTS / "analysis"
    OUT.mkdir(parents=True, exist_ok=True)
    summ = pd.read_csv(RESULTS / "stream_summary.csv")
    ev = pd.read_csv(RESULTS / "stream_events.csv.gz")
    oracle = pd.read_csv(RESULTS / "oracle_events.csv")
    static = pd.read_csv(RESULTS / "static_constructors.csv" if (RESULTS / "static_constructors.csv").exists() else ROOT / "results" / "static_constructors.csv")
    scal = pd.read_csv(RESULTS / "scaling_summary.csv")
    scal_ev = pd.read_csv(RESULTS / "scaling_events.csv.gz")
    mem = pd.read_csv(RESULTS / "memory.csv")
    det = json.loads((RESULTS / "determinism.json").read_text())
    instances = cfg["data"]["instances"]
    conds = cfg["streams"]["conditions"]

    # ---------------- per-instance medians over seeds ----------------
    agg = summ.groupby(["instance", "condition", "method"]).agg(
        seeds=("seed", "count"), clash_mean=("clash_events", "mean"),
        D_median=("total_D", "median"), D_q1=("total_D", lambda x: q(x, .25)), D_q3=("total_D", lambda x: q(x, .75)),
        W_median=("total_W", "median"), added_median=("periods_added", "median"),
        added_mean=("periods_added", "mean"), added_total=("periods_added", "sum"),
        relP_median=("rel_repair_dP", "median"), n_single=("n_single", "sum"),
        n_double=("n_double", "sum"), n_kempe=("n_kempe", "sum"), n_new=("n_new", "sum"),
        maxD=("max_D", "max"), valid_all=("valid", "min")).reset_index()
    agg.to_csv(OUT / "per_instance_method.csv", index=False)

    # pooled clash-event latency per instance x method
    cl = ev[ev.clash == 1]
    lat = cl.groupby(["instance", "method"]).latency_us.agg(
        n="count", median="median", p95=lambda x: q(x, .95), max="max").reset_index()
    lat.to_csv(OUT / "latency_clash_events.csv", index=False)

    # ---------------- paired tests per instance ----------------
    tests = []
    for cond in conds:
        for base in [b for b in ["RECOMPUTE", "SINGLE", "ONE_BLOCKER", "TBR"] if b != M]:
            for metric in ["total_D", "total_W", "periods_added"]:
                rows = []
                for inst in instances:
                    a = summ[(summ.instance == inst) & (summ.condition == cond) & (summ.method == M)].sort_values("seed")
                    b = summ[(summ.instance == inst) & (summ.condition == cond) & (summ.method == base)].sort_values("seed")
                    p, kind = paired_test(a[metric].values, b[metric].values)
                    diff = a[metric].values - b[metric].values
                    rows.append({"condition": cond, "baseline": base, "metric": metric, "instance": inst,
                                 "tbr_median": float(np.median(a[metric])), "base_median": float(np.median(b[metric])),
                                 "median_paired_diff": float(np.median(diff)), "p": p, "test": kind})
                adj = holm([r["p"] for r in rows])
                for r, pa in zip(rows, adj):
                    r["p_holm"] = pa
                tests.extend(rows)
    tests = pd.DataFrame(tests)
    tests.to_csv(OUT / "paired_tests_per_instance.csv", index=False)

    across = []
    for cond in conds:
        for base in [b for b in ["RECOMPUTE", "SINGLE", "ONE_BLOCKER", "TBR"] if b != M]:
            for metric, col in [("total_D", "D_median"), ("total_W", "W_median"), ("periods_added", "added_median")]:
                a = agg[(agg.condition == cond) & (agg.method == M)].set_index("instance").loc[instances, col]
                b = agg[(agg.condition == cond) & (agg.method == base)].set_index("instance").loc[instances, col]
                p, kind = paired_test(a.values, b.values)
                across.append({"condition": cond, "baseline": base, "metric": metric, "n_instances": len(instances),
                               "tbr_median_of_medians": float(a.median()), "base_median_of_medians": float(b.median()),
                               "p": p, "test": kind})
    across = pd.DataFrame(across)
    across.to_csv(OUT / "across_instance_tests.csv", index=False)

    # ---------------- oracle ----------------
    solved = oracle[oracle.solved == 1]
    nontriv = solved[solved.tier != "single"]
    small = solved[(solved.oracle_status == "OPTIMAL") & (solved.d_star <= 2)]
    q1_ok = bool(((small.tbr_dk == 0) & (small.tbr_D == small.d_star)).all())
    oracle_summary = {
        "clash_events": int(len(oracle)), "solved": int(len(solved)),
        "unresolved": int((oracle.solved == 0).sum()),
        "status_counts": oracle.oracle_status.value_counts().to_dict(),
        "tier_counts": oracle.tier.value_counts().to_dict(),
        "lex_opt_rate_all_solved": float(solved.lex_optimal.astype(float).mean()) if len(solved) else None,
        "lex_opt_n_all": int(solved.lex_optimal.astype(float).sum()),
        "nontrivial_solved": int(len(nontriv)),
        "lex_opt_rate_nontrivial": float(nontriv.lex_optimal.astype(float).mean()) if len(nontriv) else None,
        "lex_opt_n_nontrivial": int(nontriv.lex_optimal.astype(float).sum()),
        "dstar_le2_events": int(len(small)), "q1_all_exact": q1_ok,
        "dstar_distribution": solved.d_star.value_counts(dropna=True).sort_index().to_dict(),
        "suboptimal_events": solved[solved.lex_optimal.astype(float) == 0][
            ["instance", "seed", "t", "tier", "tbr_dk", "tbr_D", "oracle_status", "d_star"]].to_dict("records"),
        "oracle_time_s_median": float(oracle.oracle_time_s.median()),
        "oracle_time_s_max": float(oracle.oracle_time_s.max()),
    }
    save_json(OUT / "oracle_summary.json", oracle_summary)

    # ---------------- scaling, memory, static ----------------
    sc_cl = scal_ev[scal_ev.clash == 1]
    sc_lat = sc_cl.assign(n=sc_cl.instance.str.extract(r"n(\d+)")[0].astype(int)).groupby(
        ["n", "method"]).latency_us.agg(events="count", median="median", p95=lambda x: q(x, .95)).reset_index()
    sc_lat.to_csv(OUT / "scaling_latency.csv", index=False)
    sc_tab = scal.groupby(["n", "method"]).agg(m=("m", "mean"), max_degree=("max_degree", "mean"),
                                               k0=("k0", "mean"), clash=("clash_events", "mean"),
                                               D=("total_D", "mean"), added=("periods_added", "mean"),
                                               wall_s=("wall_s", "mean")).reset_index()
    sc_tab.to_csv(OUT / "scaling_table.csv", index=False)
    mem_tab = mem.groupby("instance").peak_bytes.agg(events="count", median="median", max="max").reset_index()
    mem_tab.to_csv(OUT / "memory_table.csv", index=False)
    static_p = static.pivot(index="instance", columns="constructor", values="colours")
    static_p = static_p.join(static.groupby("instance")[["n", "m", "density", "official_periods", "clique_lb",
                                                          "nx_dsatur"]].first())
    static_p.to_csv(OUT / "static_colours.csv")
    static.pivot(index="instance", columns="constructor", values="time_s").to_csv(OUT / "static_times.csv")

    # ---------------- junit ----------------
    root = ET.parse(ROOT / "results" / "tests" / "junit.xml").getroot()
    ts = root if root.tag == "testsuite" else root.find("testsuite")
    cases = [(c.get("classname"), c.get("name"), (c.find("failure") is None and c.find("error") is None
                                                  and c.find("skipped") is None)) for c in ts.iter("testcase")]
    def passed(pattern):
        sel = [ok for cls, nm, ok in cases if pattern in nm]
        return bool(sel) and all(sel), len(sel)

    # ---------------- requirement coverage ----------------
    reqs = []

    def add(rid, text, value, met, evidence):
        reqs.append({"id": rid, "requirement": text, "measured": value, "met": bool(met), "evidence": evidence})

    stream_valid = bool((summ.valid == 1).all()) and bool((scal.valid == 1).all())
    n_events_checked = int(len(ev) + len(scal_ev))
    add("H1", "Every exam has exactly one period after every event",
        f"{n_events_checked} events checked; streams valid={stream_valid}", stream_valid,
        "results/stream_summary.csv; results/scaling_summary.csv (IncrementalChecker)")
    add("H2", "No student clash after every event (independent checker)",
        f"{n_events_checked} events; 0 violations" if stream_valid else "violations found", stream_valid,
        "examrepair/validate.py; results/stream_summary.csv")
    present = {m: b for m, b in BUDGETS.items() if m in set(summ.method)}
    bud_ok = all((summ[summ.method == m].max_D <= b).all() for m, b in present.items())
    add("H3", "No event moves more than B exams",
        "max D per method: " + ", ".join(f"{m}={int(summ[summ.method == m].max_D.max())}" for m in present),
        bud_ok, "results/stream_summary.csv")
    ok_val, n_val = passed("invalid")
    ok_mal, n_mal = passed("malformed")
    add("H4", "Invalid input rejected without state change", f"{n_val + n_mal} validation tests passed={ok_val and ok_mal}",
        ok_val and ok_mal, "results/tests/junit.xml")
    add("H5", "Every event completes (no crash/time-out)",
        f"{len(summ)} streams x 200 events + {len(scal)} scaling streams completed", stream_valid,
        "results/logs/*.log; stream_summary.csv")
    add("H6", "Deterministic decisions", f"hashes identical={det['identical']}", det["identical"],
        "results/determinism.json")
    add("Q1", "Exact whenever D* <= 2", f"{len(small)} events with D*<=2; all exact={q1_ok}", q1_ok and len(small) > 0,
        "results/oracle_events.csv")
    rate = oracle_summary["lex_opt_rate_all_solved"]
    add("Q2", ">=95% lexicographic optimality vs oracle",
        f"{oracle_summary['lex_opt_n_all']}/{oracle_summary['solved']} = {rate:.4f} "
        f"(non-trivial subset: {oracle_summary['lex_opt_n_nontrivial']}/{oracle_summary['nontrivial_solved']})",
        rate is not None and rate >= 0.95, "results/analysis/oracle_summary.json")
    q3_inst = all(agg[(agg.condition == c) & (agg.method == M)].set_index("instance").D_median[i] <
                  agg[(agg.condition == c) & (agg.method == "RECOMPUTE")].set_index("instance").D_median[i]
                  for c in conds for i in instances)
    q3_p = across[(across.baseline == "RECOMPUTE") & (across.metric == "total_D")].p
    q3 = q3_inst and bool((q3_p < 0.05).all())
    add("Q3", "Fewer exams moved than recomputation (every instance; across-instance p<0.05)",
        f"every instance={q3_inst}; across-instance p={', '.join(f'{x:.2e}' for x in q3_p)}", q3,
        "results/analysis/across_instance_tests.csv")
    q4 = all(agg[(agg.condition == c) & (agg.method == M)].set_index("instance").added_median[i] <=
             agg[(agg.condition == c) & (agg.method == "SINGLE")].set_index("instance").added_median[i]
             for c in conds for i in instances)
    add("Q4", "No more periods added than single-move baseline (median, every instance)",
        f"holds on all {len(instances) * len(conds)} instance-conditions={q4}", q4,
        "results/analysis/per_instance_method.csv")
    q5 = all(agg[(agg.condition == c) & (agg.method == M)].set_index("instance").W_median[i] <
             agg[(agg.condition == c) & (agg.method == "RECOMPUTE")].set_index("instance").W_median[i]
             for c in conds for i in instances)
    add("Q5", "Fewer students affected than recomputation (median, every instance)", f"{q5}", q5,
        "results/analysis/per_instance_method.csv")
    relmax = agg[agg.method == M].relP_median.max()
    add("Q6", "Repair-induced proximity change <= +5% (median, every instance)",
        f"max median = {relmax:+.4f}", relmax <= 0.05, "results/analysis/per_instance_method.csv")
    tl = lat[lat.method == M].set_index("instance")
    rl = lat[lat.method == "RECOMPUTE"].set_index("instance")
    add("P1", "Median TBR clash latency <= 5 ms (every instance)", f"max median = {tl['median'].max():.1f} us",
        tl["median"].max() <= 5000, "results/analysis/latency_clash_events.csv")
    add("P2", "p95 TBR clash latency <= 50 ms (every instance)", f"max p95 = {tl['p95'].max():.1f} us",
        tl["p95"].max() <= 50000, "results/analysis/latency_clash_events.csv")
    ratio = (rl["median"] / tl["median"]).min()
    add("P3", "TBR >= 10x faster than recomputation (median, every instance)", f"min ratio = {ratio:.1f}x",
        ratio >= 10, "results/analysis/latency_clash_events.csv")
    l8000 = sc_lat[(sc_lat.n == 8000) & (sc_lat.method == M)]["median"]
    p4v = float(l8000.iloc[0]) if len(l8000) else float("nan")
    add("P4", "Median TBR clash latency <= 10 ms at n = 8000", f"{p4v:.1f} us", p4v <= 10000,
        "results/analysis/scaling_latency.csv")
    add("P5", "Peak repair working memory <= 1 MiB", f"max = {mem.peak_bytes.max()} bytes over {len(mem)} events",
        mem.peak_bytes.max() <= 1048576, "results/analysis/memory_table.csv")
    r1_patterns = ["test_tbr_on_graph_families", "test_constructors_proper_on_families",
                   "test_event_with_no_other_exams", "test_no_clash_event_changes_nothing",
                   "test_invalid_events_leave_state_unchanged"]
    r1 = all(passed(p)[0] for p in r1_patterns)
    add("R1", "Correct on edge-case structures", f"{sum(passed(p)[1] for p in r1_patterns)} tests passed={r1}", r1,
        "results/tests/junit.xml")
    req = pd.DataFrame(reqs)
    req.to_csv(OUT / "requirement_coverage.csv", index=False)
    met = int(req.met.sum())
    headline = {"method": M, "requirements": len(req), "met": met, "coverage": met / len(req),
                "target_gt_95pct": met / len(req) > 0.95, "unmet": req[~req.met].id.tolist(),
                "hard_group_all_met": bool(req[req.id.str.startswith("H")].met.all()),
                "tests": {"total": len(cases), "passed": sum(ok for _, _, ok in cases)}}
    save_json(OUT / "headline.json", headline)
    print(req[["id", "measured", "met"]].to_string())
    print(json.dumps(headline, indent=1))


if __name__ == "__main__":
    main()
