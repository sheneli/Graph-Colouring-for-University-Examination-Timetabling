"""Exact minimum-move repair oracle using Google OR-Tools CP-SAT (LIBRARY SOLVER).

This is NOT the proposed algorithm. It solves, exactly when it terminates, the Color-Fixing
problem restricted to the current period count (Garnero et al., 2017):

    variables  x[e,p] in {0,1}, e in E, p in 0..k-1
    s.t.       sum_p x[e,p] = 1                  for all e
               x[i,p] + x[j,p] <= 1              for all {i,j} in C, p
    minimise   sum_e (1 - x[e, tau_prev[e]])     (number of moved exams, D*)

The model formulation and the wrapper code are original; the search is performed by CP-SAT
(Perron and Didier, OR-Tools). Status values: OPTIMAL, FEASIBLE (time limit hit before proof),
INFEASIBLE (no proper colouring within k periods: a new period is unavoidable), UNKNOWN.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from ortools.sat.python import cp_model


@dataclass
class OracleResult:
    status: str
    d_star: int | None
    bound: float | None
    wall_time: float


def min_moves(adj: Sequence[Mapping[int, int]], tau_prev: Sequence[int], k: int,
              time_limit: float = 20.0, workers: int = 2, seed: int = 0) -> OracleResult:
    n = len(adj)
    model = cp_model.CpModel()
    x = [[model.NewBoolVar(f"x_{e}_{p}") for p in range(k)] for e in range(n)]
    for e in range(n):
        model.AddExactlyOne(x[e])
    for i in range(n):
        for j in adj[i]:
            if i < j:
                for p in range(k):
                    model.AddBoolOr([x[i][p].Not(), x[j][p].Not()])
    stay = [x[e][tau_prev[e]] for e in range(n) if 0 <= tau_prev[e] < k]
    model.Minimize(n - sum(stay))
    for e in range(n):
        if 0 <= tau_prev[e] < k:
            model.AddHint(x[e][tau_prev[e]], 1)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(time_limit)
    solver.parameters.num_search_workers = int(workers)
    solver.parameters.random_seed = int(seed)
    status = solver.Solve(model)
    name = solver.StatusName(status)
    d_star = int(round(solver.ObjectiveValue())) if status in (cp_model.OPTIMAL, cp_model.FEASIBLE) else None
    bound = solver.BestObjectiveBound() if status in (cp_model.OPTIMAL, cp_model.FEASIBLE) else None
    return OracleResult(name, d_star, bound, solver.WallTime())
