"""Carter proximity cost (Carter, Laporte and Lee, 1996) - original implementation.

P(tau) = (1/|S|) * sum_{ {i,j} in C } w_ij * pi(|tau_i - tau_j|),
pi(d) = 2^(5-d) for 1 <= d <= 5 and 0 otherwise (pi(0) = 0: clashes are hard constraints).

All internal computations use the *raw* integer sum (without 1/|S|) so that comparisons
are exact; divide by |S| only for reporting.
"""

from __future__ import annotations

from typing import Mapping, Sequence

PI = (0, 16, 8, 4, 2, 1)  # pi(d) for d = 0..5


def pi(d: int) -> int:
    d = abs(d)
    return PI[d] if d <= 5 else 0


def raw_cost(adj: Sequence[Mapping[int, int]], tau: Sequence[int]) -> int:
    """Raw proximity cost, O(n + m)."""
    total = 0
    for i, nbrs in enumerate(adj):
        ti = tau[i]
        for j, w in nbrs.items():
            if i < j:
                d = abs(ti - tau[j])
                if d <= 5:
                    total += w * PI[d]
    return total


def cost(adj: Sequence[Mapping[int, int]], tau: Sequence[int], n_students: int) -> float:
    """Normalised Carter cost (per student)."""
    return raw_cost(adj, tau) / max(n_students, 1)


def delta_vector(adj: Sequence[Mapping[int, int]], tau: Sequence[int], x: int, k: int,
                 override: Mapping[int, int] | None = None) -> list[int]:
    """Raw proximity change of moving exam ``x`` to each period p in 0..k-1.

    ``override`` gives positions of neighbours that are assumed already moved (used by the
    double move, where the partner exam has moved). Complexity O(deg(x) + k).
    """
    vec = [0] * k
    base = 0
    tx = tau[x]
    for u, w in adj[x].items():
        q = override.get(u, tau[u]) if override else tau[u]
        d0 = abs(tx - q)
        if d0 <= 5:
            base += w * PI[d0]
        for d in range(1, 6):
            wd = w * PI[d]
            if q - d >= 0:
                vec[q - d] += wd
            if q + d < k:
                vec[q + d] += wd
    return [v - base for v in vec]


def delta_moves(adj: Sequence[Mapping[int, int]], tau: Sequence[int],
                moves: Mapping[int, int]) -> int:
    """Raw proximity change of applying ``moves`` (exam -> new period) simultaneously.

    Each affected edge is counted once. Complexity O(sum of degrees of moved exams).
    """
    delta = 0
    for v, newp in moves.items():
        oldp = tau[v]
        for u, w in adj[v].items():
            if u in moves:
                if u < v:  # edge between two moved exams: count once (when visiting the smaller id)
                    continue
                new_u = moves[u]
            else:
                new_u = tau[u]
            delta += w * (pi(newp - new_u) - pi(oldp - tau[u]))
    return delta
