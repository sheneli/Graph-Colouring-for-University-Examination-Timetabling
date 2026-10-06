"""Late-enrolment streams and synthetic instances (original code).

Hold-out stream (modelling assumption, docs/preregistration.md section 3.1): draw T
enrolments (s, e) uniformly without replacement among students with >= 2 exams, remove
them to obtain the "published" enrolment data A_0, then replay them in a seeded random
order as late enrolments. Uses :mod:`random` (Mersenne Twister) with explicit seeds.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

import numpy as np

from .io import Instance


@dataclass(frozen=True)
class Stream:
    initial_students: tuple[tuple[int, ...], ...]
    events: tuple[tuple[int, int], ...]
    seed: int


def holdout_stream(inst: Instance, T: int, seed: int) -> Stream:
    rng = random.Random(seed)
    eligible = [(s, e) for s, exams in enumerate(inst.students) if len(exams) >= 2
                for e in exams]
    if T > len(eligible):
        raise ValueError(f"T={T} exceeds {len(eligible)} eligible enrolments")
    chosen = rng.sample(eligible, T)
    removed: dict[int, set[int]] = {}
    for s, e in chosen:
        removed.setdefault(s, set()).add(e)
    initial = tuple(tuple(e for e in exams if e not in removed.get(s, ()))
                    for s, exams in enumerate(inst.students))
    events = list(chosen)
    rng.shuffle(events)
    return Stream(initial, tuple(events), seed)


def synthetic_instance(n_exams: int, seed: int, students_per_exam: int = 8,
                       min_exams: int = 3, max_exams: int = 7, zipf_s: float = 1.0) -> Instance:
    """Random enrolment data: |S| = students_per_exam * n; each student takes U{min..max}
    distinct exams drawn with Zipf-like popularity p_i proportional to 1/(rank_i)^s."""
    rng = np.random.default_rng(seed)
    ranks = rng.permutation(n_exams) + 1
    weights = 1.0 / ranks.astype(float) ** zipf_s
    probs = weights / weights.sum()
    students = []
    for _ in range(students_per_exam * n_exams):
        m = int(rng.integers(min_exams, max_exams + 1))
        exams = rng.choice(n_exams, size=m, replace=False, p=probs)
        students.append(tuple(sorted(int(x) for x in exams)))
    return Instance(name=f"synth-n{n_exams}-s{seed}", n_exams=n_exams,
                    exam_ids=tuple(range(1, n_exams + 1)), students=tuple(students))
