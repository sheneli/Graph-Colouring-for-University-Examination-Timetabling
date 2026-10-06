"""Exact-oracle comparison (pre-registration section 3.3; requirements Q1, Q2).

Replays the TBR (B = 8) trajectory on the six smallest instances (tight condition). For
every clash event, BEFORE repairing, the CP-SAT oracle computes D* (minimum exams moved
within the current k periods) on the updated graph. TBR's result on that same state is then
compared. The oracle is a library solver used only as a reference.

Output: results/oracle_events.csv
"""

from __future__ import annotations

import time

from common import cli_config, out_dir, write_csv
from examrepair.experiment import initial_timetable
from examrepair.io import load_named
from examrepair.model import apply_enrolment, find_clash, make_state
from examrepair.oracle import min_moves
from examrepair.repair import TBR, TBRPLUS, repair_clash

CONFIGS = {"TBR": TBR, "TBRPLUS": TBRPLUS}
from examrepair.streams import holdout_stream


def main() -> None:
    cfg = cli_config()
    RESULTS = out_dir(cfg)
    oc = cfg["oracle"]
    T = cfg["streams"]["T"]
    B = cfg["streams"]["headline_budget"]
    rows = []
    t_start = time.time()
    for name in oc["instances"]:
        inst = load_named(cfg["data"]["toronto_dir"], name)
        for seed in oc["seeds"]:
            stream = holdout_stream(inst, T, seed)
            tau0, k0, _ = initial_timetable(inst.n_exams, stream.initial_students, oc["condition"], name)
            st = make_state(inst.n_exams, stream.initial_students, tau0, k0)
            for t, (s, e) in enumerate(stream.events):
                others = apply_enrolment(st, s, e)
                f = find_clash(st, e, others)
                if f is None:
                    continue
                o = min_moves(st.adj, st.tau, st.k, time_limit=oc["time_limit_s"],
                              workers=oc["workers"], seed=oc["solver_seed"])
                res = repair_clash(st, e, f, CONFIGS[oc.get('method', 'TBR')])
                if o.status == "OPTIMAL":
                    opt = (0, o.d_star) if o.d_star <= B else (1, 1)
                elif o.status == "INFEASIBLE":
                    opt = (1, 1)
                else:
                    opt = None
                tbr = (res.dk, res.D)
                rows.append({
                    "instance": name, "seed": seed, "t": t, "tier": res.tier, "tbr_dk": res.dk,
                    "tbr_D": res.D, "oracle_status": o.status, "d_star": o.d_star,
                    "oracle_bound": o.bound, "oracle_time_s": round(o.wall_time, 3),
                    "solved": int(opt is not None),
                    "lex_optimal": (int(tbr == opt) if opt is not None else ""),
                    "k": st.k - res.dk,
                })
            print(f"{name} seed {seed}: {sum(1 for r in rows if r['instance']==name and r['seed']==seed)} clash events "
                  f"({time.time() - t_start:.0f}s)", flush=True)
    write_csv(RESULTS / "oracle_events.csv", rows)


if __name__ == "__main__":
    main()
