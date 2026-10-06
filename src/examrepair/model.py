"""Conflict graph, mutable timetable state and late-enrolment events (original code).

Data-structure choices (see docs/design/design.md, section 7):

* ``adj: list[dict[int, int]]`` - adjacency map. ``adj[i][j]`` is the number of students
  taking both exams ``i`` and ``j`` (the edge weight ``w_ij``). Expected O(1) edge test and
  update, O(deg) neighbour iteration, O(n + m) space.
* ``tau: list[int]`` - period of each exam.
* ``enrol: list[set[int]]`` - exams held by each student (O(1) membership).
* ``size: list[int]`` - number of students per exam.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from itertools import combinations
from typing import Iterable, Sequence


class EventError(ValueError):
    """Raised when a late-enrolment event is invalid. State is never modified."""


def build_adjacency(n_exams: int, students: Iterable[Iterable[int]]) -> list[dict[int, int]]:
    """Build the weighted conflict graph from per-student exam lists.

    Complexity: O(n + sum over students of |E(s)|^2) time, O(n + m) space.
    """
    adj: list[dict[int, int]] = [dict() for _ in range(n_exams)]
    for exams in students:
        for i, j in combinations(sorted(set(exams)), 2):
            adj[i][j] = adj[i].get(j, 0) + 1
            adj[j][i] = adj[j].get(i, 0) + 1
    return adj


def exam_sizes(n_exams: int, students: Iterable[Iterable[int]]) -> list[int]:
    size = [0] * n_exams
    for exams in students:
        for e in set(exams):
            size[e] += 1
    return size


def n_edges(adj: Sequence[dict[int, int]]) -> int:
    return sum(len(d) for d in adj) // 2


def max_degree(adj: Sequence[dict[int, int]]) -> int:
    return max((len(d) for d in adj), default=0)


@dataclass
class State:
    """Mutable timetable state.

    Invariant (I1): ``tau`` is a proper colouring of ``adj`` using periods 0..k-1
    at the start and end of every event.
    """

    adj: list[dict[int, int]]
    tau: list[int]
    k: int
    enrol: list[set[int]]
    size: list[int]
    n_students: int

    @property
    def n_exams(self) -> int:
        return len(self.tau)

    def copy(self) -> "State":
        """Deep copy (used so that every method starts from the same published timetable)."""
        return State(
            adj=[dict(d) for d in self.adj],
            tau=list(self.tau),
            k=self.k,
            enrol=[set(s) for s in self.enrol],
            size=list(self.size),
            n_students=self.n_students,
        )

    def is_proper(self) -> bool:
        """O(n + m) self-check using the state's own graph (the independent checker is
        :func:`examrepair.validate.check_timetable`)."""
        tau = self.tau
        if any(not (0 <= p < self.k) for p in tau):
            return False
        return all(tau[i] != tau[j] for i, nbrs in enumerate(self.adj) for j in nbrs if i < j)


def make_state(n_exams: int, students: Sequence[Iterable[int]], tau: Sequence[int],
               k: int) -> State:
    """Create a state from enrolments and a timetable; raises if ``tau`` is not proper."""
    adj = build_adjacency(n_exams, students)
    if len(tau) != n_exams:
        raise ValueError("timetable length differs from number of exams")
    st = State(adj=adj, tau=list(tau), k=k, enrol=[set(s) for s in students],
               size=exam_sizes(n_exams, students), n_students=len(students))
    if not st.is_proper():
        raise ValueError("initial timetable is not a proper colouring")
    return st


def validate_event(state: State, s: int, e: int) -> None:
    """Check a late enrolment (s, e) WITHOUT modifying state (requirement H4)."""
    if isinstance(s, bool) or isinstance(e, bool) or not isinstance(s, int) or not isinstance(e, int):
        raise EventError(f"student and exam must be integers, got {s!r}, {e!r}")
    if not 0 <= s < len(state.enrol):
        raise EventError(f"unknown student {s}")
    if not 0 <= e < state.n_exams:
        raise EventError(f"unknown exam {e}")
    if e in state.enrol[s]:
        raise EventError(f"student {s} is already enrolled in exam {e}")


def apply_enrolment(state: State, s: int, e: int) -> list[int]:
    """Validate then apply a late enrolment; return L = the student's other exams.

    Adds edge {e, f} (or increments its weight) for every f in L. Complexity O(|L|) expected.
    """
    validate_event(state, s, e)
    others = sorted(state.enrol[s])
    adj_e = state.adj[e]
    for f in others:
        adj_e[f] = adj_e.get(f, 0) + 1
        adj_f = state.adj[f]
        adj_f[e] = adj_f.get(e, 0) + 1
    state.enrol[s].add(e)
    state.size[e] += 1
    return others


def find_clash(state: State, e: int, others: Sequence[int]) -> int | None:
    """Return the unique f in ``others`` with tau[f] == tau[e], or None (Lemma 1).

    Because ``others`` is a clique in the previous graph, at most one such f exists.
    """
    pe = state.tau[e]
    clashing = [f for f in others if state.tau[f] == pe]
    if len(clashing) > 1:  # impossible if invariant I1 held before the event
        raise AssertionError("invariant violated: more than one clash after a single enrolment")
    return clashing[0] if clashing else None


def clone(obj):
    return copy.deepcopy(obj)
