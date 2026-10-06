"""Independent timetable checker (original code).

Deliberately independent of the algorithm: it never reads the conflict graph ``adj`` built
by :mod:`examrepair.model`. It re-derives clashes directly from raw per-student enrolment
lists, so a bug in graph maintenance or in the repair code cannot hide a clash.
"""

from __future__ import annotations

from typing import Iterable, Sequence


class TimetableError(AssertionError):
    pass


def check_timetable(students: Iterable[Iterable[int]], tau: Sequence[int], k: int,
                    n_exams: int) -> None:
    """Raise TimetableError unless every exam has exactly one period in [0, k) and no
    student has two exams in the same period. O(n + |A|)."""
    if len(tau) != n_exams:
        raise TimetableError("timetable does not assign every exam exactly once")
    for e, p in enumerate(tau):
        if not isinstance(p, int) or not 0 <= p < k:
            raise TimetableError(f"exam {e} has invalid period {p!r} (k={k})")
    for s, exams in enumerate(students):
        seen: dict[int, int] = {}
        for e in exams:
            p = tau[e]
            if p in seen and seen[p] != e:
                raise TimetableError(f"student {s}: exams {seen[p]} and {e} both in period {p}")
            seen[p] = e


class IncrementalChecker:
    """Event-by-event independent check.

    Keeps its own copy of the enrolment lists and an exam -> students index. After each
    event it (1) diffs the timetable against its own previous copy to find moved exams
    (it does not trust the algorithm's report), and (2) re-checks every student who takes a
    moved exam plus the student who enrolled. Students whose exams all kept their periods
    cannot acquire a new clash, so this is complete. A full check is run on demand.
    """

    def __init__(self, students: Iterable[Iterable[int]], tau: Sequence[int], k: int,
                 n_exams: int) -> None:
        self.students = [list(s) for s in students]
        self.takers: list[list[int]] = [[] for _ in range(n_exams)]
        for s, exams in enumerate(self.students):
            for e in exams:
                self.takers[e].append(s)
        self.prev = list(tau)
        self.n_exams = n_exams
        check_timetable(self.students, tau, k, n_exams)

    def _check_student(self, s: int, tau: Sequence[int]) -> None:
        seen: dict[int, int] = {}
        for e in self.students[s]:
            p = tau[e]
            if p in seen:
                raise TimetableError(f"student {s}: exams {seen[p]} and {e} both in period {p}")
            seen[p] = e

    def after_event(self, s: int, e: int, tau: Sequence[int], k: int) -> int:
        """Record enrolment (s, e) and verify; return number of exams that moved."""
        self.students[s].append(e)
        self.takers[e].append(s)
        if len(tau) != self.n_exams:
            raise TimetableError("timetable length changed")
        moved = [v for v in range(self.n_exams) if tau[v] != self.prev[v]]
        for v in moved:
            p = tau[v]
            if not isinstance(p, int) or not 0 <= p < k:
                raise TimetableError(f"exam {v} has invalid period {p!r}")
        to_check = {s}
        for v in moved:
            to_check.update(self.takers[v])
        for st in to_check:
            self._check_student(st, tau)
        self.prev = list(tau)
        return len(moved)

    def full_check(self, tau: Sequence[int], k: int) -> None:
        check_timetable(self.students, tau, k, self.n_exams)
