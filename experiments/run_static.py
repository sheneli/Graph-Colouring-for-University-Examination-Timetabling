"""Static constructor comparison on the 13 Toronto instances (pre-registration section 3.5).

Output: results/static_constructors.csv
"""

from __future__ import annotations

import time

import networkx as nx

from common import cli_config, out_dir, write_csv
from examrepair.constructors import (CONSTRUCTORS, greedy_clique_lower_bound, is_proper,
                                     n_colours)
from examrepair.io import OFFICIAL_PERIODS, load_named
from examrepair.model import build_adjacency, max_degree, n_edges
from examrepair.proximity import cost


def main() -> None:
    cfg = cli_config()
    RESULTS = out_dir(cfg)
    rows = []
    for name in cfg["data"]["instances"]:
        inst = load_named(cfg["data"]["toronto_dir"], name)
        adj = build_adjacency(inst.n_exams, inst.students)
        lb = greedy_clique_lower_bound(adj)
        g = nx.Graph()
        g.add_nodes_from(range(inst.n_exams))
        g.add_edges_from((i, j) for i in range(inst.n_exams) for j in adj[i] if i < j)
        lib = {s: max(nx.greedy_color(g, strategy=s).values()) + 1
               for s in ("largest_first", "smallest_last", "DSATUR")}
        for cname, fn in CONSTRUCTORS.items():
            t0 = time.perf_counter()
            col = fn(adj)
            dt = time.perf_counter() - t0
            rows.append({
                "instance": name, "n": inst.n_exams, "m": n_edges(adj), "max_degree": max_degree(adj),
                "density": round(2 * n_edges(adj) / (inst.n_exams * (inst.n_exams - 1)), 4),
                "students": inst.n_students, "enrolments": inst.n_enrolments,
                "official_periods": OFFICIAL_PERIODS[name], "clique_lb": lb,
                "constructor": cname, "colours": n_colours(col), "proper": int(is_proper(adj, col)),
                "time_s": round(dt, 4), "carter_cost_at_colours": round(cost(adj, col, inst.n_students), 3),
                "nx_largest_first": lib["largest_first"], "nx_smallest_last": lib["smallest_last"],
                "nx_dsatur": lib["DSATUR"],
            })
            print(name, cname, n_colours(col), f"{dt:.3f}s")
    write_csv(RESULTS / "static_constructors.csv", rows)


if __name__ == "__main__":
    main()
