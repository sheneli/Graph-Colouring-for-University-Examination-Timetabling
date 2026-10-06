"""Working-memory measurement for TBR repairs (requirement P5).

For each Toronto instance, replay the seed-0 tight stream with TBR; for the first 50 clash
events (or all if fewer), measure peak traced memory allocated during the repair call with
tracemalloc (Python Software Foundation documentation). tracemalloc slows execution, so
this is a separate run from the timing experiments.

Output: results/memory.csv
"""

from __future__ import annotations

import tracemalloc

from common import cli_config, out_dir, write_csv
from examrepair.experiment import initial_timetable
from examrepair.io import load_named
from examrepair.model import apply_enrolment, find_clash, make_state
from examrepair.repair import TBR, TBRPLUS, repair_clash

CONFIGS = {"TBR": TBR, "TBRPLUS": TBRPLUS}
from examrepair.streams import holdout_stream


def main() -> None:
    cfg = cli_config()
    RESULTS = out_dir(cfg)
    mc = cfg["memory"]
    rows = []
    for name in cfg["data"]["instances"]:
        inst = load_named(cfg["data"]["toronto_dir"], name)
        # use a longer stream if needed to reach the event quota
        T = min(sum(len(s) for s in inst.students if len(s) >= 2), 2000)
        stream = holdout_stream(inst, T, mc["seed"])
        tau0, k0, _ = initial_timetable(inst.n_exams, stream.initial_students, mc["condition"], name)
        st = make_state(inst.n_exams, stream.initial_students, tau0, k0)
        count = 0
        for s, e in stream.events:
            others = apply_enrolment(st, s, e)
            f = find_clash(st, e, others)
            if f is None:
                continue
            tracemalloc.start()
            tracemalloc.reset_peak()
            base_cur, _ = tracemalloc.get_traced_memory()
            res = repair_clash(st, e, f, CONFIGS[mc.get('method', 'TBR')])
            _cur, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            rows.append({"instance": name, "event": count, "tier": res.tier,
                         "peak_bytes": peak - base_cur, "D": res.D})
            count += 1
            if count >= mc["events_per_instance"]:
                break
        print(name, count, max(r["peak_bytes"] for r in rows if r["instance"] == name), flush=True)
    write_csv(RESULTS / "memory.csv", rows)


if __name__ == "__main__":
    main()
