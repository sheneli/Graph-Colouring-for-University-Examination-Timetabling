"""Descriptive measurement of the persistent data structures (exploratory; see deviations log #7).

For each Toronto instance: build the adjacency map and the per-student enrolment sets exactly as
the library does, and record the memory traced by tracemalloc, the number of stored adjacency
entries (2m), and the sizes that rejected alternatives would need (computed arithmetically).
Output: results/ds_memory.csv
"""

from __future__ import annotations

import time
import tracemalloc

from common import RESULTS, cli_config, write_csv
from examrepair.io import load_named
from examrepair.model import build_adjacency, exam_sizes


def main() -> None:
    cfg = cli_config()
    rows = []
    for name in cfg["data"]["instances"]:
        inst = load_named(cfg["data"]["toronto_dir"], name)
        n = inst.n_exams
        students = inst.students
        tracemalloc.start()
        t0 = time.perf_counter()
        adj = build_adjacency(n, students)
        t_adj = time.perf_counter() - t0
        adj_bytes = tracemalloc.get_traced_memory()[0]
        tracemalloc.stop()
        tracemalloc.start()
        enrol = [set(s) for s in students]
        size = exam_sizes(n, students)
        enrol_bytes = tracemalloc.get_traced_memory()[0]
        tracemalloc.stop()
        m = sum(len(d) for d in adj) // 2
        rows.append({
            "instance": name, "n": n, "m": m, "adj_entries": 2 * m,
            "adj_bytes": adj_bytes, "enrol_bytes": enrol_bytes, "build_adj_s": round(t_adj, 4),
            "matrix_cells": n * n, "matrix_int32_bytes": 4 * n * n,
            "csr_int32_bytes": 4 * (n + 1) + 2 * 4 * (2 * m),
            "bytes_per_adj_entry": round(adj_bytes / max(1, 2 * m), 1),
        })
        print(name, n, m, adj_bytes, flush=True)
        del adj, enrol, size
    write_csv(RESULTS / "ds_memory.csv", rows)


if __name__ == "__main__":
    main()
