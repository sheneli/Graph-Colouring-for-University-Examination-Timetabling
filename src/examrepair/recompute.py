"""Full-recomputation baseline (M4).

On a clash, recolour the whole updated graph with DSATUR (original code, constructors.py)
and relabel the new colour classes onto existing periods so that as many exams as possible
keep their period. The relabelling is a maximum-weight assignment solved with the LIBRARY
call ``scipy.optimize.linear_sum_assignment`` (SciPy's modified Jonker-Volgenant algorithm,
Crouse, 2016). This gives recomputation its most favourable (least disruptive) labelling.

Colours that cannot be matched to an existing period become new periods appended after the
existing ones; the session never shrinks (k_t >= k_{t-1}).
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import linear_sum_assignment

from .constructors import dsatur
from .model import State, apply_enrolment, find_clash
from .proximity import delta_moves
from .repair import TIER_NONE, RepairResult

TIER_RECOMPUTE = "recompute"


def relabel_to_periods(new_colour: list[int], old_tau: list[int], k_old: int) -> list[int]:
    """Map colour classes of ``new_colour`` to periods maximising unchanged exams."""
    c = max(new_colour) + 1 if new_colour else 0
    size = max(c, k_old)
    agree = np.zeros((size, size), dtype=np.int64)
    for v, col in enumerate(new_colour):
        agree[col, old_tau[v]] += 1
    rows, cols = linear_sum_assignment(agree, maximize=True)
    mapping = {int(r): int(cl) for r, cl in zip(rows, cols)}
    # colours mapped to a "virtual" period >= k_old become appended periods in order
    extra = sorted(r for r in range(c) if mapping[r] >= k_old)
    for i, r in enumerate(extra):
        mapping[r] = k_old + i
    return [mapping[col] for col in new_colour]


def process_event_recompute(state: State, s: int, e: int) -> RepairResult:
    others = apply_enrolment(state, s, e)
    f = find_clash(state, e, others)
    if f is None:
        return RepairResult(TIER_NONE)
    new_colour = dsatur(state.adj)
    new_tau = relabel_to_periods(new_colour, state.tau, state.k)
    moves = {v: p for v, p in enumerate(new_tau) if p != state.tau[v]}
    dP = delta_moves(state.adj, state.tau, moves)
    W = sum(state.size[v] for v in moves)
    record = tuple((v, state.tau[v], p) for v, p in sorted(moves.items()))
    k_new = max(state.k, max(new_tau) + 1)
    dk = k_new - state.k
    state.tau[:] = new_tau
    state.k = k_new
    return RepairResult(TIER_RECOMPUTE, record, len(moves), W, dP, dk, (e, f), 1,
                        extra={"colours": max(new_colour) + 1})
