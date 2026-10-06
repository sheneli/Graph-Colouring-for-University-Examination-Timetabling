"""Brute-force reference implementations used only by the tests (original code)."""

from __future__ import annotations

import itertools
import random

from examrepair.model import build_adjacency, make_state
from examrepair.proximity import raw_cost
from examrepair.constructors import dsatur, n_colours


def all_proper_colourings(adj, k):
    n = len(adj)
    edges = [(i, j) for i in range(n) for j in adj[i] if i < j]
    for col in itertools.product(range(k), repeat=n):
        if all(col[i] != col[j] for i, j in edges):
            yield col


def brute_force_repair(adj, tau, k, size):
    """Return (D*, best (W, dP_raw) among D* repairs) or (None, None) if infeasible in k."""
    base = raw_cost(adj, tau)
    best_d, best_sec = None, None
    for col in all_proper_colourings(adj, k):
        moved = [v for v in range(len(tau)) if col[v] != tau[v]]
        d = len(moved)
        sec = (sum(size[v] for v in moved), raw_cost(adj, col) - base)
        if best_d is None or d < best_d or (d == best_d and sec < best_sec):
            best_d, best_sec = d, sec
    return best_d, best_sec


def random_small_case(rng: random.Random, n_max=7, k_max=4, n_students_max=8):
    """Random instance with a proper initial timetable and a clash-producing late enrolment.

    Returns (n, students, tau, k, (s, e)) or None if no clash-producing enrolment exists.
    """
    n = rng.randint(3, n_max)
    n_students = rng.randint(2, n_students_max)
    students = []
    for _ in range(n_students):
        m = rng.randint(1, min(4, n))
        students.append(tuple(sorted(rng.sample(range(n), m))))
    adj = build_adjacency(n, students)
    tau = dsatur(adj)
    c = n_colours(tau)
    k = rng.randint(c, max(c, k_max))
    # random relabel of colours into k periods keeps properness
    perm = rng.sample(range(k), c)
    tau = [perm[x] for x in tau]
    options = [(s, e) for s, ex in enumerate(students) for e in range(n)
               if e not in ex and any(tau[f] == tau[e] for f in ex)]
    if not options:
        return None
    s, e = rng.choice(options)
    return n, students, tau, k, (s, e)


def state_from(n, students, tau, k):
    return make_state(n, students, tau, k)
