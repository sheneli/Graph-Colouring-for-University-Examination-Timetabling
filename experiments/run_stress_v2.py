"""EXPLORATORY stress analysis (deviation 3 in docs/deviations.md; not pre-registered and
not used for requirement coverage).

Heavier change: T = 2000 late enrolments, tight condition, seeds 0-4, methods TBR, SINGLE,
ONE_BLOCKER on all 13 Toronto instances. For the six small instances, every non-trivial TBR
event (Tier 1 failed) is also checked against the CP-SAT oracle.

Outputs: results/stress_v2_summary.csv, results/stress_v2_oracle.csv
"""

from __future__ import annotations

import time

from common import RESULTS, load_config, write_csv  # v2 (TBR+) exploratory stress
from examrepair.experiment import initial_timetable, method_registry, run_stream
from examrepair.io import load_named
from examrepair.model import apply_enrolment, find_clash, make_state
from examrepair.oracle import min_moves
from examrepair.proximity import raw_cost
from examrepair.repair import TBRPLUS as TBR, TIER_SINGLE, repair_clash
from examrepair.streams import holdout_stream

T = 2000
SEEDS = [0, 1, 2, 3, 4]
METHODS = ["TBRPLUS"]


def main() -> None:
    cfg = load_config()
    reg = method_registry()
    summaries, oracle_rows = [], []
    small = set(cfg["oracle"]["instances"])
    t0 = time.time()
    for name in cfg["data"]["instances"]:
        inst = load_named(cfg["data"]["toronto_dir"], name)
        for seed in SEEDS:
            stream = holdout_stream(inst, T, seed)
            tau0, k0, _ = initial_timetable(inst.n_exams, stream.initial_students, "tight", name)
            base = make_state(inst.n_exams, stream.initial_students, tau0, k0)
            P0 = raw_cost(base.adj, base.tau)
            for m in METHODS:
                out = run_stream(inst, stream, "tight", m, reg[m], base, P0)
                summaries.append(out.summary)
            if name in small:
                st = base.copy()
                for t, (s, e) in enumerate(stream.events):
                    others = apply_enrolment(st, s, e)
                    f = find_clash(st, e, others)
                    if f is None:
                        continue
                    probe = st.copy()
                    res = repair_clash(probe, e, f, TBR)
                    if res.tier != TIER_SINGLE:
                        o = min_moves(st.adj, st.tau, st.k, time_limit=20, workers=2, seed=0)
                        if o.status == "OPTIMAL":
                            opt = (0, o.d_star) if o.d_star <= 8 else (1, 1)
                        elif o.status == "INFEASIBLE":
                            opt = (1, 1)
                        else:
                            opt = None
                        oracle_rows.append({
                            "instance": name, "seed": seed, "t": t, "tier": res.tier,
                            "tbr_dk": res.dk, "tbr_D": res.D, "oracle_status": o.status,
                            "d_star": o.d_star, "oracle_time_s": round(o.wall_time, 3),
                            "lex_optimal": "" if opt is None else int((res.dk, res.D) == opt)})
                    repair_clash(st, e, f, TBR)
            print(name, seed, f"{time.time() - t0:.0f}s", flush=True)
    write_csv(RESULTS / "stress_v2_summary.csv", summaries)
    write_csv(RESULTS / "stress_v2_oracle.csv", oracle_rows)


if __name__ == "__main__":
    main()
