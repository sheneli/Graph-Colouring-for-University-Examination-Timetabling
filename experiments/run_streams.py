"""Main pre-registered stream experiment (pre-registration sections 3.1-3.2) and the
determinism check (requirement H6).

Outputs:
  results/stream_events.csv.gz    one row per (instance, condition, seed, method, event)
  results/stream_summary.csv      one row per stream
  results/initial_timetables.csv  tau0 statistics per (instance, seed, condition)
  results/determinism.json        two independent runs of the reference configuration
"""

from __future__ import annotations

import time

from common import cli_config, environment, out_dir, save_json, write_csv
from examrepair.experiment import initial_timetable, method_registry, run_stream, shuffled_methods
from examrepair.io import load_named
from examrepair.model import make_state
from examrepair.proximity import raw_cost
from examrepair.streams import holdout_stream


def main() -> None:
    cfg = cli_config()
    RESULTS = out_dir(cfg)
    sc = cfg["streams"]
    reg = method_registry()
    events, summaries, inits = [], [], []
    t_start = time.time()
    for name in cfg["data"]["instances"]:
        inst = load_named(cfg["data"]["toronto_dir"], name)
        for seed in sc["seeds"]:
            stream = holdout_stream(inst, sc["T"], seed)
            for cond in sc["conditions"]:
                tau0, k0, c = initial_timetable(inst.n_exams, stream.initial_students, cond, name)
                base = make_state(inst.n_exams, stream.initial_students, tau0, k0)
                P0 = raw_cost(base.adj, base.tau)
                inits.append({"instance": name, "seed": seed, "condition": cond,
                              "dsatur_colours": c, "k0": k0,
                              "P0": round(P0 / base.n_students, 4)})
                for m in shuffled_methods(sc["methods"], seed):
                    out = run_stream(inst, stream, cond, m, reg[m], base, P0)
                    events.extend(out.rows)
                    summaries.append(out.summary)
            print(f"{name} seed {seed} done  ({time.time() - t_start:.0f}s)", flush=True)
    write_csv(RESULTS / "stream_events.csv.gz", events)
    write_csv(RESULTS / "stream_summary.csv", summaries)
    write_csv(RESULTS / "initial_timetables.csv", inits)

    # H6: determinism - two independent runs of the reference configuration
    d = cfg["determinism"]
    inst = load_named(cfg["data"]["toronto_dir"], d["instance"])
    hashes = []
    for _ in range(2):
        stream = holdout_stream(inst, sc["T"], d["seed"])
        tau0, k0, _c = initial_timetable(inst.n_exams, stream.initial_students, d["condition"], d["instance"])
        base = make_state(inst.n_exams, stream.initial_students, tau0, k0)
        out = run_stream(inst, stream, d["condition"], d["method"], method_registry()[d["method"]],
                         base, raw_cost(base.adj, base.tau))
        hashes.append(out.summary["hash"])
    save_json(RESULTS / "determinism.json", {"config": d, "hashes": hashes,
                                              "identical": hashes[0] == hashes[1]})
    save_json(RESULTS / "environment.json", environment())
    print("total", round(time.time() - t_start), "s")


if __name__ == "__main__":
    main()
