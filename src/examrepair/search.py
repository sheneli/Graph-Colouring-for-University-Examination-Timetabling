"""Bounded exact repair search (Tier 4 of TBR+, original code).

A bounded search tree for the single-conflict Color-Fixing problem within the current k
periods. Garnero et al. (2017) show Color-Fixing is fixed-parameter tractable in the number
of recoloured vertices; this implementation uses the classical bounded-search-tree idea:

* every repair must give some endpoint of a remaining conflict edge a new final period;
* each exam is reassigned at most once (an optimal repair never needs to move an exam twice);
* iterative deepening over the number of moved exams d = d_min .. B makes the first depth
  with a solution equal to the minimum D (exact, if the node budget is not exhausted);
* at that depth all solutions are enumerated and the lexicographically best (W, dP) kept;
* pruning: (i) never move an exam into a period occupied by an already-moved neighbour;
  (ii) a lower bound LB = |forced exams| + |greedy matching of remaining conflict edges|;
  (iii) a visited set of partial assignments per depth.

Work is capped by ``node_budget`` expansions; if the cap is hit the search returns the best
solution found so far (possibly none) and reports ``exhausted=True``.

Complexity: O(min(node_budget, (2(k-1))^B) * Delta) time, O(B + |visited|) extra space.
"""

from __future__ import annotations

from dataclasses import dataclass

from .proximity import delta_moves


@dataclass
class SearchOutcome:
    moves: dict[int, int] | None
    W: int
    dP: int
    nodes: int
    exhausted: bool
    depth_completed: int  # largest depth fully explored without solution (or with solutions)


class _Abort(Exception):
    pass


def bounded_repair_search(state, e: int, f: int, d_min: int, d_max: int, node_budget: int,
                          use_proximity: bool = True) -> SearchOutcome:
    adj, tau, k, size = state.adj, state.tau, state.k, state.size
    assign: dict[int, int] = {}
    conflicts: set[tuple[int, int]] = {(min(e, f), max(e, f))}
    nodes = 0
    best = {"key": None, "moves": None, "W": 0, "dP": 0}

    def col(v: int) -> int:
        return assign.get(v, tau[v])

    def lower_bound() -> int | None:
        forced: set[int] = set()
        free_edges = []
        for (u, v) in conflicts:
            ua, va = u in assign, v in assign
            if ua and va:
                return None  # both endpoints fixed and equal: dead end
            if ua:
                forced.add(v)
            elif va:
                forced.add(u)
            else:
                free_edges.append((u, v))
        matched: set[int] = set(forced)
        m = 0
        for (u, v) in free_edges:
            if u not in matched and v not in matched:
                matched.add(u)
                matched.add(v)
                m += 1
        return len(forced) + m

    def apply(z: int, c: int) -> tuple[list, list]:
        old = col(z)
        removed, added = [], []
        for u in adj[z]:
            cu = col(u)
            edge = (z, u) if z < u else (u, z)
            if cu == old and edge in conflicts:
                conflicts.discard(edge)
                removed.append(edge)
            elif cu == c:
                conflicts.add(edge)
                added.append(edge)
        assign[z] = c
        return removed, added

    def undo(z: int, removed: list, added: list) -> None:
        del assign[z]
        for edge in added:
            conflicts.discard(edge)
        for edge in removed:
            conflicts.add(edge)

    def record() -> None:
        moves = dict(assign)
        W = sum(size[v] for v in moves)
        dP = delta_moves(adj, tau, moves) if use_proximity else 0
        key = (W, dP, tuple(sorted(moves.items())))
        if best["key"] is None or key < best["key"]:
            best.update(key=key, moves=moves, W=W, dP=dP)

    def dfs(left: int, visited: set) -> None:
        nonlocal nodes
        nodes += 1
        if nodes > node_budget:
            raise _Abort
        if not conflicts:
            if left == 0:
                record()
            return
        lb = lower_bound()
        if lb is None or lb > left:
            return
        sig = frozenset(assign.items())
        if sig in visited:
            return
        visited.add(sig)
        # choose the conflict edge with the fewest free endpoints (forced first)
        edge = min(conflicts, key=lambda ed: ((ed[0] not in assign) + (ed[1] not in assign), ed))
        for z in edge:
            if z in assign:
                continue
            cz = col(z)
            blocked = {assign[u] for u in adj[z] if u in assign}
            for c in range(k):
                if c == cz or c in blocked:
                    continue
                removed, added = apply(z, c)
                dfs(left - 1, visited)
                undo(z, removed, added)

    exhausted = False
    depth_done = d_min - 1
    try:
        for d in range(d_min, d_max + 1):
            dfs(d, set())
            depth_done = d
            if best["moves"] is not None:
                break
    except _Abort:
        exhausted = True
    return SearchOutcome(best["moves"], best["W"], best["dP"], nodes, exhausted, depth_done)
