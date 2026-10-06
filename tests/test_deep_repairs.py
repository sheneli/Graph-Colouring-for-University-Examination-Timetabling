"""Brute-force checks of Theorems 4 and 5 on events that need two or more moves.

Added after review (deviations log #8): the random generator used in test_tbr.py rarely produces
events with D* >= 3, so this file samples tight 3-period instances and keeps only events whose
brute-force minimum repair needs at least two moves.
"""

import random

from examrepair.constructors import dsatur, n_colours
from examrepair.model import apply_enrolment, build_adjacency
from examrepair.repair import TBR, TBRPLUS, RepairConfig, process_event
from examrepair.validate import check_timetable

from helpers import brute_force_repair, state_from

TBRPLUS_UNLIMITED = RepairConfig("TBRPLUS_BIG", (1, 2, 3, 4), 8, True, 10**7)


def _deep_case(rng):
    n = rng.randint(6, 8)
    students = [tuple(sorted(rng.sample(range(n), rng.randint(2, 3)))) for _ in range(rng.randint(6, 12))]
    adj = build_adjacency(n, students)
    tau = dsatur(adj)
    k = n_colours(tau)
    if k != 3:
        return None
    perm = rng.sample(range(k), k)
    tau = [perm[x] for x in tau]
    options = [(s, e) for s, ex in enumerate(students) for e in range(n)
               if e not in ex and any(tau[f] == tau[e] for f in ex)]
    if not options:
        return None
    s, e = rng.choice(options)
    return n, students, tau, k, (s, e)


def test_deep_repairs_theorems_4_and_5():
    """Events with D* >= 2: TBR exact when D* = 2 (Theorem 4); TBR+ with an unexhausted node budget exact
    in (dk, D) and (W, dP) for every D* (Theorem 5); TBR+ with N = 2,000 always valid and within budget."""
    rng = random.Random(31337)
    counts = {}
    tbr_misses_deep = 0
    while counts.get(2, 0) < 100 or sum(v for d, v in counts.items() if d >= 3) < 40:
        case = _deep_case(rng)
        if case is None:
            continue
        n, students, tau, k, (s, e) = case
        ref = state_from(n, students, tau, k)
        apply_enrolment(ref, s, e)
        d_star, sec = brute_force_repair(ref.adj, ref.tau, ref.k, ref.size)
        if d_star is None or d_star < 2:
            continue
        counts[d_star] = counts.get(d_star, 0) + 1
        st = state_from(n, students, tau, k)
        res = process_event(st, s, e, TBRPLUS_UNLIMITED)
        check_timetable(st.enrol, st.tau, st.k, n)
        assert not res.extra.get("exhausted", False)
        assert (res.dk, res.D) == (0, d_star)
        assert (res.W, res.dP_raw) == sec
        st1 = state_from(n, students, tau, k)
        r1 = process_event(st1, s, e, TBR)
        check_timetable(st1.enrol, st1.tau, st1.k, n)
        if d_star == 2:
            assert (r1.dk, r1.D) == (0, 2) and (r1.W, r1.dP_raw) == sec
        elif (r1.dk, r1.D) != (0, d_star):
            tbr_misses_deep += 1
        st2 = state_from(n, students, tau, k)
        r2 = process_event(st2, s, e, TBRPLUS)
        check_timetable(st2.enrol, st2.tau, st2.k, n)
        assert r2.D <= TBRPLUS.budget
    # the sample must contain repairs that are not single Kempe chains (TBR misses some of them)
    assert tbr_misses_deep > 0
    print("D* distribution:", dict(sorted(counts.items())), "TBR misses with D* >= 3:", tbr_misses_deep)
