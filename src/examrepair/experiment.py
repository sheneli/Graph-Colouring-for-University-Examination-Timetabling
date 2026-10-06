"""Experiment runner: replay late-enrolment streams through repair methods (original code).

Each method starts from a deep copy of the same published timetable (paired design).
Latency is measured with ``time.perf_counter`` around the event-processing call only
(event validation + graph update + repair); the independent check, metric bookkeeping and
I/O are outside the timed region.
"""

from __future__ import annotations

import hashlib
import random
import statistics
import time
from dataclasses import dataclass
from typing import Callable

from .constructors import dsatur, n_colours
from .io import OFFICIAL_PERIODS, Instance
from .model import State, build_adjacency
from .proximity import raw_cost
from .recompute import process_event_recompute
from .repair import RepairConfig, RepairResult, process_event
from .streams import Stream
from .validate import IncrementalChecker

MethodFn = Callable[[State, int, int], RepairResult]


def method_registry(budgets=(2, 4, 8, 16, 32)) -> dict[str, MethodFn]:
    reg: dict[str, MethodFn] = {
        "TBR": lambda st, s, e: process_event(st, s, e, RepairConfig("TBR", (1, 2, 3), 8, True)),
        "SINGLE": lambda st, s, e: process_event(st, s, e, RepairConfig("SINGLE", (1,), 8, True)),
        "ONE_BLOCKER": lambda st, s, e: process_event(st, s, e, RepairConfig("ONE_BLOCKER", (1, 2), 8, True)),
        "RECOMPUTE": process_event_recompute,
        "TBR_NOPROX": lambda st, s, e: process_event(st, s, e, RepairConfig("TBR_NOPROX", (1, 2, 3), 8, False)),
        "TBR_NOT2": lambda st, s, e: process_event(st, s, e, RepairConfig("TBR_NOT2", (1, 3), 8, True)),
        "TBRPLUS": lambda st, s, e: process_event(st, s, e, RepairConfig("TBRPLUS", (1, 2, 3, 4), 8, True, 2000)),
        "TBRPLUS_N20000": lambda st, s, e: process_event(
            st, s, e, RepairConfig("TBRPLUS_N20000", (1, 2, 3, 4), 8, True, 20000)),
    }
    for b in budgets:
        if b != 8:
            reg[f"TBR_B{b}"] = (lambda bb: (lambda st, s, e: process_event(
                st, s, e, RepairConfig(f"TBR_B{bb}", (1, 2, 3), bb, True))))(b)
    return reg


def initial_timetable(n_exams: int, students, condition: str, name: str | None = None
                      ) -> tuple[list[int], int, int]:
    """Build tau0 with DSATUR. Returns (tau0, k0, dsatur_colours).

    condition 'tight': k0 = DSATUR colours; 'official': k0 = max(colours, published count),
    extra periods are empty and appended at the end.
    """
    adj = build_adjacency(n_exams, students)
    tau0 = dsatur(adj)
    c = n_colours(tau0)
    if condition == "tight":
        k0 = c
    elif condition == "official":
        k0 = max(c, OFFICIAL_PERIODS.get(name, c)) if name else c
    else:
        raise ValueError(condition)
    return tau0, k0, c


@dataclass
class StreamOutput:
    rows: list[dict]
    summary: dict


def run_stream(inst: Instance, stream: Stream, condition: str, method: str, fn: MethodFn,
               base: State, P0_raw: int, check: bool = True) -> StreamOutput:
    state = base.copy()
    checker = IncrementalChecker(stream.initial_students, state.tau, state.k, inst.n_exams) if check else None
    rows = []
    h = hashlib.sha256()
    lat_clash = []
    for t, (s, e) in enumerate(stream.events):
        n_others = len(state.enrol[s])
        t0 = time.perf_counter()
        res = fn(state, s, e)
        dt = time.perf_counter() - t0
        moved = checker.after_event(s, e, state.tau, state.k) if checker else -1
        if checker and moved != res.D:
            raise AssertionError(f"reported D={res.D} but checker saw {moved} moved exams")
        clash = res.tier != "none"
        if clash:
            lat_clash.append(dt)
        h.update(repr((t, res.tier, res.moves, state.k)).encode())
        rows.append({
            "instance": inst.name, "condition": condition, "seed": stream.seed, "method": method,
            "t": t, "s": s, "e": e, "n_others": n_others, "clash": int(clash), "tier": res.tier,
            "D": res.D, "W": res.W, "dP_raw": res.dP_raw, "dk": res.dk, "k_after": state.k,
            "latency_us": round(dt * 1e6, 2), "candidates": res.candidates,
            "search_nodes": res.extra.get("nodes", 0), "search_exhausted": int(res.extra.get("exhausted", False)),
        })
    if checker:
        checker.full_check(state.tau, state.k)
    tiers = [r["tier"] for r in rows]
    summary = {
        "instance": inst.name, "condition": condition, "seed": stream.seed, "method": method,
        "T": len(rows), "clash_events": sum(r["clash"] for r in rows),
        "k0": base.k, "k_final": state.k, "periods_added": state.k - base.k,
        "total_D": sum(r["D"] for r in rows), "total_W": sum(r["W"] for r in rows),
        "cum_dP_raw": sum(r["dP_raw"] for r in rows), "P0_raw": P0_raw,
        "rel_repair_dP": (sum(r["dP_raw"] for r in rows) / P0_raw) if P0_raw else 0.0,
        "P_final": raw_cost(state.adj, state.tau) / state.n_students,
        "n_single": tiers.count("single"), "n_double": tiers.count("double"),
        "n_kempe": tiers.count("kempe"), "n_search": tiers.count("search"),
        "n_new": tiers.count("new_period"),
        "search_exhausted": sum(1 for r in rows if r.get("search_exhausted")),
        "n_recompute": tiers.count("recompute"),
        "max_D": max((r["D"] for r in rows), default=0),
        "lat_clash_median_us": round(statistics.median(lat_clash) * 1e6, 2) if lat_clash else None,
        "lat_clash_p95_us": round(_quantile(lat_clash, 0.95) * 1e6, 2) if lat_clash else None,
        "lat_all_median_us": round(statistics.median(r["latency_us"] for r in rows), 2),
        "valid": 1 if check else -1,
        "hash": h.hexdigest(),
    }
    return StreamOutput(rows, summary)


def _quantile(xs, q):
    xs = sorted(xs)
    if not xs:
        return float("nan")
    pos = q * (len(xs) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def shuffled_methods(methods: list[str], seed: int) -> list[str]:
    order = list(methods)
    random.Random(10_000 + seed).shuffle(order)
    return order
