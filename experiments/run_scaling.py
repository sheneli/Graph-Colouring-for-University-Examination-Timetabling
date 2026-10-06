"""Synthetic scaling experiment (pre-registration section 3.4; requirement P4).

Outputs: results/scaling_summary.csv, results/scaling_events.csv.gz
"""

from __future__ import annotations

import time

from common import cli_config, out_dir, write_csv
from examrepair.experiment import initial_timetable, method_registry, run_stream
from examrepair.model import make_state, max_degree, n_edges
from examrepair.proximity import raw_cost
from examrepair.streams import holdout_stream, synthetic_instance


def main() -> None:
    cfg = cli_config()
    RESULTS = out_dir(cfg)
    sc = cfg["scaling"]
    reg = method_registry()
    summaries, events = [], []
    skip_recompute = False
    for n in sc["sizes"]:
        for seed in sc["seeds"]:
            t0 = time.time()
            inst = synthetic_instance(n, seed, students_per_exam=sc["students_per_exam"])
            stream = holdout_stream(inst, sc["T"], seed)
            tau0, k0, _ = initial_timetable(inst.n_exams, stream.initial_students, "tight")
            base = make_state(inst.n_exams, stream.initial_students, tau0, k0)
            P0 = raw_cost(base.adj, base.tau)
            build = time.time() - t0
            for m in sc["methods"]:
                if m == "RECOMPUTE" and skip_recompute:
                    continue
                t1 = time.time()
                out = run_stream(inst, stream, "tight", m, reg[m], base, P0)
                wall = time.time() - t1
                s = out.summary
                s.update({"n": n, "m": n_edges(base.adj), "max_degree": max_degree(base.adj),
                          "students": inst.n_students, "build_s": round(build, 2),
                          "wall_s": round(wall, 2)})
                summaries.append(s)
                events.extend(out.rows)
                print(n, seed, m, s["clash_events"], s["lat_clash_median_us"], f"{wall:.1f}s", flush=True)
                if m == "RECOMPUTE" and wall > sc["recompute_run_cap_s"]:
                    skip_recompute = True  # pre-registered cap
    write_csv(RESULTS / "scaling_summary.csv", summaries)
    write_csv(RESULTS / "scaling_events.csv.gz", events)


if __name__ == "__main__":
    main()
