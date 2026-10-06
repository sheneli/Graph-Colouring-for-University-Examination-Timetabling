"""Static graph-colouring constructors for the initial published timetable (original code).

All functions take an adjacency structure ``adj`` (sequence of mappings or sets; only the
keys are used) and return ``list[int]`` colours 0..c-1. Ties are broken by exam index so
results are deterministic.

* first_fit       - natural order greedy; O(n + m).
* welsh_powell    - largest-degree-first order (Welsh and Powell, 1967); O(n log n + m).
* smallest_last   - smallest-last order (Matula and Beck, 1983); bucket queue, O(n + m) without
                    the deterministic min-index tie-break, O(n^2 + m) worst case with it.
* dsatur          - saturation degree (Brelaz, 1979), ties by degree in the uncoloured
                    subgraph then index; binary heap with lazy deletion, O((n + m) log n).
* rlf             - recursive largest first (Leighton, 1979); O(n (n + m)) worst case here.
* greedy_clique_lower_bound - size of a greedily grown clique (a valid lower bound on chi).
"""

from __future__ import annotations

import heapq
from typing import Iterable, Mapping, Sequence

Adj = Sequence[Mapping[int, int] | set]


def _first_fit_in_order(adj: Adj, order: Iterable[int]) -> list[int]:
    n = len(adj)
    colour = [-1] * n
    for v in order:
        used = {colour[u] for u in adj[v] if colour[u] >= 0}
        c = 0
        while c in used:
            c += 1
        colour[v] = c
    return colour


def first_fit(adj: Adj) -> list[int]:
    return _first_fit_in_order(adj, range(len(adj)))


def welsh_powell(adj: Adj) -> list[int]:
    order = sorted(range(len(adj)), key=lambda v: (-len(adj[v]), v))
    return _first_fit_in_order(adj, order)


def smallest_last_order(adj: Adj) -> list[int]:
    """Matula-Beck smallest-last ordering using a bucket queue (O(n + m)); the min-index
    tie-break scans the lowest bucket, so the worst case here is O(n^2 + m)."""
    n = len(adj)
    deg = [len(adj[v]) for v in range(n)]
    maxd = max(deg, default=0)
    buckets: list[set[int]] = [set() for _ in range(maxd + 1)]
    for v in range(n):
        buckets[deg[v]].add(v)
    removed = [False] * n
    order_rev: list[int] = []
    d = 0
    for _ in range(n):
        d = max(d - 1, 0)
        while not buckets[d]:
            d += 1
        v = min(buckets[d])  # deterministic tie-break by index
        buckets[d].discard(v)
        removed[v] = True
        order_rev.append(v)
        for u in adj[v]:
            if not removed[u]:
                buckets[deg[u]].discard(u)
                deg[u] -= 1
                buckets[deg[u]].add(u)
    return order_rev[::-1]


def smallest_last(adj: Adj) -> list[int]:
    return _first_fit_in_order(adj, smallest_last_order(adj))


def dsatur(adj: Adj) -> list[int]:
    """DSATUR (Brelaz, 1979).

    Select the uncoloured vertex with maximum saturation (number of distinct colours among
    its neighbours); ties by maximum degree in the uncoloured subgraph, then smallest index;
    give it the smallest feasible colour.
    """
    n = len(adj)
    colour = [-1] * n
    sat: list[set[int]] = [set() for _ in range(n)]
    udeg = [len(adj[v]) for v in range(n)]
    heap = [(0, -udeg[v], v) for v in range(n)]
    heapq.heapify(heap)
    coloured = 0
    while coloured < n:
        negsat, negdeg, v = heapq.heappop(heap)
        if colour[v] >= 0 or -negsat != len(sat[v]) or -negdeg != udeg[v]:
            continue  # stale entry (lazy deletion)
        used = sat[v]
        c = 0
        while c in used:
            c += 1
        colour[v] = c
        coloured += 1
        for u in adj[v]:
            if colour[u] < 0:
                udeg[u] -= 1
                sat[u].add(c)
                heapq.heappush(heap, (-len(sat[u]), -udeg[u], u))
    return colour


def rlf(adj: Adj) -> list[int]:
    """Recursive Largest First (Leighton, 1979).

    Build one colour class at a time. Start with the uncoloured vertex of maximum degree in
    the uncoloured subgraph; then repeatedly add the candidate (uncoloured, not adjacent to
    the class) with the most neighbours among the excluded vertices (uncoloured vertices
    adjacent to the class), ties by fewest neighbours among candidates, then index.
    """
    n = len(adj)
    colour = [-1] * n
    uncoloured = set(range(n))
    c = 0
    while uncoloured:
        # degree within uncoloured subgraph
        v0 = max(uncoloured, key=lambda v: (sum(1 for u in adj[v] if u in uncoloured), -v))
        candidates = set(uncoloured)
        excluded: set[int] = set()
        n_excl = {v: 0 for v in candidates}  # neighbours in excluded set
        n_cand = {v: sum(1 for u in adj[v] if u in candidates) for v in candidates}

        def take(v: int) -> None:
            colour[v] = c
            candidates.discard(v)
            uncoloured.discard(v)
            for u in adj[v]:
                if u in candidates:
                    n_cand[u] -= 1
            # neighbours of v leave the candidate set and become excluded
            newly = [u for u in adj[v] if u in candidates]
            for u in newly:
                candidates.discard(u)
                excluded.add(u)
                for z in adj[u]:
                    if z in candidates:
                        n_excl[z] += 1
                        n_cand[z] -= 1

        take(v0)
        while candidates:
            v = max(candidates, key=lambda x: (n_excl[x], -n_cand[x], -x))
            take(v)
        c += 1
    return colour


def n_colours(colour: Sequence[int]) -> int:
    return (max(colour) + 1) if colour else 0


def is_proper(adj: Adj, colour: Sequence[int]) -> bool:
    return all(colour[i] != colour[j] for i in range(len(adj)) for j in adj[i])


def greedy_clique_lower_bound(adj: Adj, starts: int = 50) -> int:
    """Largest clique found by greedy growth from the ``starts`` highest-degree vertices.

    Any clique size is a valid lower bound on the chromatic number.
    """
    n = len(adj)
    if n == 0:
        return 0
    order = sorted(range(n), key=lambda v: (-len(adj[v]), v))[:starts]
    best = 1
    for v in order:
        clique = [v]
        cand = set(adj[v])
        while cand:
            u = max(cand, key=lambda x: (len(cand.intersection(adj[x])), -x))
            clique.append(u)
            cand &= set(adj[u])
        best = max(best, len(clique))
    return best


CONSTRUCTORS = {
    "first_fit": first_fit,
    "welsh_powell": welsh_powell,
    "smallest_last": smallest_last,
    "dsatur": dsatur,
    "rlf": rlf,
}
