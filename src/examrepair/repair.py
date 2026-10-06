"""Tiered Budgeted Repair (TBR) and incremental repair baselines.

ORIGINAL CODE. The individual moves are established techniques:

* Tier 1 single move - incremental first-fit recolouring.
* Tier 2 unique-blocker double move - adapted from unique-neighbour recolouring in dynamic
  graph colouring (Bhattacharya et al., 2018).
* Tier 3 bounded Kempe-chain interchange - classical Kempe chains (e.g. Lewis, 2021;
  Hardy, Lewis and Thompson, 2017), here capped at the budget B and applied to the
  conflict graph minus the clashing edge.
* Tier 4 bounded exact repair search (TBR+ only; search.py) - bounded search tree, cf. the
  fixed-parameter tractability of Color-Fixing (Garnero et al., 2017).
* Fallback new period - feasibility fallback.

The contribution of this project is the integration (tier order by disruption, one
lexicographic acceptance key, an explicit budget B) and its evaluation; see
docs/design/design.md for pseudocode, proofs (Theorems 2-4) and complexity.

Method configurations
---------------------
* ``TBR``          tiers (1, 2, 3) + fallback, budget B  (pre-registered v1; M1)
* ``TBRPLUS``      tiers (1, 2, 3, 4) + fallback, node budget N (v2; addendum A)
* ``SINGLE``       tiers (1,) + fallback                 (baseline M2)
* ``ONE_BLOCKER``  tiers (1, 2) + fallback               (baseline M3)
* ablations: ``use_proximity=False`` (A1); tiers (1, 3) (A2).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Iterable

from .model import State, apply_enrolment, find_clash
from .proximity import delta_moves, delta_vector
from .search import bounded_repair_search

TIER_NONE = "none"
TIER_SINGLE = "single"
TIER_DOUBLE = "double"
TIER_KEMPE = "kempe"
TIER_SEARCH = "search"
TIER_NEW = "new_period"


@dataclass(frozen=True)
class RepairConfig:
    """Configuration of a repair method."""

    name: str = "TBR"
    tiers: tuple[int, ...] = (1, 2, 3)
    budget: int = 8
    use_proximity: bool = True
    node_budget: int = 2000  # Tier 4 (bounded exact search) expansions per event

    def __post_init__(self) -> None:
        if self.budget < 1:
            raise ValueError("budget B must be >= 1")
        if not set(self.tiers) <= {1, 2, 3, 4} or 1 not in self.tiers:
            raise ValueError("tiers must include 1 and be a subset of {1, 2, 3, 4}")
        if self.node_budget < 1:
            raise ValueError("node_budget must be >= 1")


TBR = RepairConfig("TBR", (1, 2, 3), 8, True)
TBRPLUS = RepairConfig("TBRPLUS", (1, 2, 3, 4), 8, True, 2000)
SINGLE = RepairConfig("SINGLE", (1,), 8, True)
ONE_BLOCKER = RepairConfig("ONE_BLOCKER", (1, 2), 8, True)


@dataclass
class RepairResult:
    """Outcome of one late-enrolment event."""

    tier: str
    moves: tuple[tuple[int, int, int], ...] = ()  # (exam, old period, new period)
    D: int = 0            # exams moved
    W: int = 0            # student registrations whose time changed (sum of sizes)
    dP_raw: int = 0       # raw proximity change caused by the repair moves
    dk: int = 0           # periods added (0 or 1)
    clash: tuple[int, int] | None = None
    candidates: int = 0   # candidate repairs evaluated (diagnostic)
    extra: dict = field(default_factory=dict)


class _Best:
    """Keeps the best candidate under the lexicographic key (D, W, dP, canonical moves)."""

    __slots__ = ("key", "moves", "dP", "count", "use_prox")

    def __init__(self, use_prox: bool) -> None:
        self.key = None
        self.moves: dict[int, int] | None = None
        self.dP = 0
        self.count = 0
        self.use_prox = use_prox

    def offer(self, moves: dict[int, int], W: int, dP: int) -> None:
        self.count += 1
        canon = tuple(sorted(moves.items()))
        key = (len(moves), W, dP if self.use_prox else 0, canon)
        if self.key is None or key < self.key:
            self.key, self.moves, self.dP = key, dict(moves), dP


def bounded_kempe_chain(state: State, x: int, a: int, b: int, skip: tuple[int, int],
                        cap: int) -> set[int] | None:
    """Kempe chain of ``x`` in the subgraph induced by periods {a, b}, ignoring edge ``skip``.

    Returns the vertex set, or None if it has more than ``cap`` vertices (BFS stops early).
    Complexity O(cap * max degree).
    """
    tau, adj = state.tau, state.adj
    s0, s1 = skip
    chain = {x}
    queue = deque([x])
    while queue:
        v = queue.popleft()
        for u in adj[v]:
            if (v == s0 and u == s1) or (v == s1 and u == s0):
                continue
            if u not in chain and (tau[u] == a or tau[u] == b):
                chain.add(u)
                if len(chain) > cap:
                    return None
                queue.append(u)
    return chain


def _tier1(state: State, ends: Iterable[int], best: _Best) -> None:
    tau, adj, k, size = state.tau, state.adj, state.k, state.size
    for x in ends:
        occupied = {tau[u] for u in adj[x]}
        free = [p for p in range(k) if p != tau[x] and p not in occupied]
        if not free:
            continue
        vec = delta_vector(adj, tau, x, k) if best.use_prox else None
        for p in free:
            best.offer({x: p}, size[x], vec[p] if vec is not None else 0)


def _tier2(state: State, ends: Iterable[int], best: _Best) -> None:
    tau, adj, k, size = state.tau, state.adj, state.k, state.size
    for x in ends:
        by_period: dict[int, list[int]] = {}
        for u in adj[x]:
            by_period.setdefault(tau[u], []).append(u)
        vec_x = delta_vector(adj, tau, x, k) if best.use_prox else None
        for p in range(k):
            if p == tau[x]:
                continue
            blockers = by_period.get(p)
            if not blockers or len(blockers) != 1:
                continue
            w = blockers[0]
            forbidden = {tau[u] for u in adj[w] if u != x}
            forbidden.add(p)  # x now occupies p and is adjacent to w
            options = [q for q in range(k) if q not in forbidden]
            if not options:
                continue
            vec_w = delta_vector(adj, tau, w, k, override={x: p}) if best.use_prox else None
            W = size[x] + size[w]
            for q in options:
                dP = (vec_x[p] + vec_w[q]) if vec_x is not None else 0
                best.offer({x: p, w: q}, W, dP)


def _tier3(state: State, e: int, f: int, budget: int, best: _Best) -> None:
    tau, k, size = state.tau, state.k, state.size
    cap = budget
    for x, y in ((e, f), (f, e)):
        a = tau[x]
        for p in range(k):
            if p == a:
                continue
            limit = cap if best.key is None else min(cap, best.key[0])
            chain = bounded_kempe_chain(state, x, a, p, (e, f), limit)
            if chain is None or y in chain:
                continue
            moves = {v: (p if tau[v] == a else a) for v in chain}
            W = sum(size[v] for v in chain)
            dP = delta_moves(state.adj, tau, moves) if best.use_prox else 0
            best.offer(moves, W, dP)


def repair_clash(state: State, e: int, f: int, cfg: RepairConfig) -> RepairResult:
    """Resolve the single clash {e, f} (tau[e] == tau[f]) in place. See design section 8."""
    best = _Best(cfg.use_proximity)
    ends = (e, f)
    tier = None
    _tier1(state, ends, best)
    if best.moves is not None:
        tier = TIER_SINGLE
    elif 2 in cfg.tiers and cfg.budget >= 2:
        _tier2(state, ends, best)
        if best.moves is not None:
            tier = TIER_DOUBLE
    if tier is None and 3 in cfg.tiers and cfg.budget >= 3:
        _tier3(state, e, f, cfg.budget, best)
        if best.moves is not None:
            tier = TIER_KEMPE
    search_info = {}
    if tier in (None, TIER_KEMPE) and 4 in cfg.tiers and cfg.budget >= 3:
        d_max = cfg.budget if best.key is None else min(cfg.budget, best.key[0])
        out = bounded_repair_search(state, e, f, 3, d_max, cfg.node_budget, cfg.use_proximity)
        search_info = {"nodes": out.nodes, "exhausted": out.exhausted}
        if out.moves is not None:
            before = best.key
            best.offer(out.moves, out.W, out.dP)
            if best.key != before:
                tier = TIER_SEARCH

    tau = state.tau
    if tier is None:  # Tier 4: open a new period after the existing ones
        x = min(ends, key=lambda v: (state.size[v], v))
        moves = {x: state.k}
        dP = delta_moves(state.adj, tau, moves)
        old = tau[x]
        tau[x] = state.k
        state.k += 1
        return RepairResult(TIER_NEW, ((x, old, state.k - 1),), 1, state.size[x], dP, 1,
                            (e, f), best.count, extra=search_info)

    moves = best.moves
    record = tuple((v, tau[v], p) for v, p in sorted(moves.items()))
    W = sum(state.size[v] for v in moves)
    dP = best.dP if cfg.use_proximity else delta_moves(state.adj, tau, moves)
    for v, p in moves.items():
        tau[v] = p
    return RepairResult(tier, record, len(moves), W, dP, 0, (e, f), best.count, extra=search_info)


def process_event(state: State, s: int, e: int, cfg: RepairConfig = TBR) -> RepairResult:
    """Apply late enrolment (s, e) and repair the timetable in place.

    Raises :class:`examrepair.model.EventError` (state unchanged) for invalid events.
    """
    others = apply_enrolment(state, s, e)
    f = find_clash(state, e, others)
    if f is None:
        return RepairResult(TIER_NONE)
    return repair_clash(state, e, f, cfg)
