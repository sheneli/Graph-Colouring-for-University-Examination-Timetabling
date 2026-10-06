"""Tests for Tiered Budgeted Repair (TBR) and the incremental baselines."""

import random

import pytest

from examrepair.model import EventError, apply_enrolment, find_clash, make_state
from examrepair.oracle import min_moves
from examrepair.proximity import raw_cost
from examrepair.repair import (ONE_BLOCKER, SINGLE, TBR, TIER_DOUBLE, TIER_KEMPE, TIER_NEW,
                               TIER_NONE, TIER_SINGLE, RepairConfig, process_event)
from examrepair.validate import check_timetable

from helpers import brute_force_repair, random_small_case, state_from

A, B_, C, D, E, F = range(6)


def rotation_example():
    students = [(A, B_, C), (D, E, F), (A, E), (C, D), (D,)]
    tau = [0, 1, 2, 0, 1, 2]
    return students, tau


def test_dry_run_rotation_example():
    """Design record section 9: TBR adds a period although D* = 3 (rotation of D-E-F)."""
    students, tau = rotation_example()
    st = make_state(6, students, tau, 3)
    res = process_event(st, 4, A, TBR)
    assert res.tier == TIER_NEW
    assert res.moves == ((A, 0, 3),)
    assert st.k == 4 and res.dk == 1 and res.D == 1
    check_timetable(st.enrol, st.tau, st.k, 6)
    # oracle on the same event from the original state: a 3-move repair exists
    st2 = make_state(6, students, tau, 3)
    others = apply_enrolment(st2, 4, A)
    assert find_clash(st2, A, others) == D
    o = min_moves(st2.adj, st2.tau, 3, time_limit=10)
    assert o.status == "OPTIMAL" and o.d_star == 3


def test_tier1_single_move():
    # path A-B with periods 0,1 and isolated C in period 2; student 1 takes C late-enrols A? use:
    students = [(A, B_), (C,)]
    tau = [0, 1, 0]
    st = make_state(3, students, tau, 3)
    res = process_event(st, 1, A, TBR)  # A (0) now conflicts with C (0)
    assert res.tier == TIER_SINGLE and res.D == 1 and res.dk == 0
    check_timetable(st.enrol, st.tau, st.k, 3)


def _tier23_instance(with_r: bool):
    """Hand-built k = 3 instance (extended report, worked examples 2 and 3).

    Exams: A0 B1 W2 Q3 C0=4 C2=5 Y6 P1a7 P1b8 P2a9 P2b10 [R11].
    Late enrolment: the student who takes only Y enrols in A -> clash A-Y (both period 0).
    """
    a, b, w, q, c0, c2, y, p1a, p1b, p2a, p2b, r = range(12)
    students = [(a, b), (a, w), (w, q), (b, c0), (b, c2), (y, p1a), (y, p1b), (y, p2a),
                (y, p2b), (y,)]
    tau = [0, 1, 2, 1, 0, 2, 0, 1, 1, 2, 2]
    n = 11
    if with_r:
        students.append((w, r))
        tau.append(0)
        n = 12
    return n, students, tau, 9  # student index 9 takes only Y


def test_tier2_double_move_known_answer():
    n, students, tau, late_student = _tier23_instance(with_r=False)
    st = make_state(n, students, tau, 3)
    res = process_event(st, late_student, 0, TBR)
    assert res.tier == TIER_DOUBLE
    assert res.moves == ((0, 0, 2), (2, 2, 0))   # A: 0 -> 2, W: 2 -> 0
    check_timetable(st.enrol, st.tau, st.k, n)
    # the single-move baseline must open a new period instead
    st2 = make_state(n, students, tau, 3)
    assert process_event(st2, late_student, 0, SINGLE).tier == TIER_NEW


def test_tier3_kempe_known_answer():
    n, students, tau, late_student = _tier23_instance(with_r=True)
    st = make_state(n, students, tau, 3)
    res = process_event(st, late_student, 0, TBR)
    assert res.tier == TIER_KEMPE and res.D == 3 and res.dk == 0
    check_timetable(st.enrol, st.tau, st.k, n)
    st2 = make_state(n, students, tau, 3)
    assert process_event(st2, late_student, 0, ONE_BLOCKER).tier == TIER_NEW
    # exact oracle agrees that 3 moves is optimal for this event
    st3 = make_state(n, students, tau, 3)
    apply_enrolment(st3, late_student, 0)
    o = min_moves(st3.adj, st3.tau, 3, time_limit=10)
    assert o.status == "OPTIMAL" and o.d_star == 3


def _find_case(tier, seed=0, tries=20000):
    rng = random.Random(seed)
    for _ in range(tries):
        case = random_small_case(rng)
        if case is None:
            continue
        n, students, tau, k, (s, e) = case
        st = state_from(n, students, tau, k)
        res = process_event(st, s, e, TBR)
        if res.tier == tier:
            return case, res
    return None, None


@pytest.mark.parametrize("tier", [TIER_DOUBLE])
def test_random_tier2_cases_exist_and_are_valid(tier):
    """Random search finds Tier-2 cases; Tier-3 cases are rare on tiny graphs and are covered
    by the hand-built known-answer test above."""
    case, res = _find_case(tier, seed=11)
    assert case is not None, f"no {tier} case found"
    n, students, tau, k, (s, e) = case
    st = state_from(n, students, tau, k)
    res = process_event(st, s, e, TBR)
    check_timetable(st.enrol, st.tau, st.k, n)
    assert res.dk == 0 and res.D <= TBR.budget
    if tier == TIER_DOUBLE:
        assert res.D == 2
    else:
        assert res.D >= 3


def test_exhaustive_small_theorem4_and_validity():
    """300 random small instances: validity always; exactness (incl. W, dP tie-breaks)
    whenever D* <= 2 (Theorem 4); never fewer moves than the brute-force optimum."""
    rng = random.Random(2026)
    checked = 0
    tiers = {}
    while checked < 300:
        case = random_small_case(rng)
        if case is None:
            continue
        n, students, tau, k, (s, e) = case
        st = state_from(n, students, tau, k)
        apply_enrolment(st, s, e)
        d_star, sec = brute_force_repair(st.adj, st.tau, st.k, st.size)
        st2 = state_from(n, students, tau, k)
        res = process_event(st2, s, e, TBR)
        tiers[res.tier] = tiers.get(res.tier, 0) + 1
        check_timetable(st2.enrol, st2.tau, st2.k, n)
        assert res.D <= TBR.budget
        if d_star is not None and d_star <= 2:
            assert res.dk == 0 and res.D == d_star
            assert (res.W, res.dP_raw) == sec
        if res.dk == 0 and d_star is not None:
            assert res.D >= d_star
        if d_star is None:
            assert res.dk == 1
        checked += 1
    assert tiers.get(TIER_SINGLE, 0) > 0


@pytest.mark.parametrize("cfg", [TBR, SINGLE, ONE_BLOCKER,
                                 RepairConfig("TBR_NOPROX", (1, 2, 3), 8, False),
                                 RepairConfig("TBR_NOT2", (1, 3), 8, True),
                                 RepairConfig("TBR_B3", (1, 2, 3), 3, True),
                                 RepairConfig("TBR_B1", (1, 2, 3), 1, True)])
def test_random_streams_valid_and_within_budget(cfg):
    rng = random.Random(7)
    for _ in range(30):
        n = rng.randint(5, 15)
        students = [tuple(sorted(rng.sample(range(n), rng.randint(1, 4)))) for _ in range(12)]
        from examrepair.constructors import dsatur, n_colours
        from examrepair.model import build_adjacency
        tau = dsatur(build_adjacency(n, students))
        st = make_state(n, students, tau, n_colours(tau))
        for _ in range(25):
            s = rng.randrange(len(students))
            choices = [e for e in range(n) if e not in st.enrol[s]]
            if not choices:
                continue
            e = rng.choice(choices)
            res = process_event(st, s, e, cfg)
            check_timetable(st.enrol, st.tau, st.k, n)
            assert res.D <= max(cfg.budget, 1)
            if cfg.tiers == (1,):
                assert res.tier in (TIER_NONE, TIER_SINGLE, TIER_NEW)


def test_budget_one_means_single_moves_only():
    students, tau = rotation_example()
    st = make_state(6, students, tau, 3)
    res = process_event(st, 4, A, RepairConfig("B1", (1, 2, 3), 1, True))
    assert res.D == 1


def test_invalid_events_leave_state_unchanged():
    students, tau = rotation_example()
    st = make_state(6, students, tau, 3)
    snapshot = (st.copy().adj, list(st.tau), st.k, [set(x) for x in st.enrol], list(st.size))
    for bad in [(99, A), (0, 99), (0, A), (-1, A), (0, -2), ("0", 1), (0, 1.5), (True, 1)]:
        with pytest.raises(EventError):
            process_event(st, *bad)
        assert (st.adj, st.tau, st.k, st.enrol, st.size) == snapshot


def test_no_clash_event_changes_nothing():
    students, tau = rotation_example()
    st = make_state(6, students, tau, 3)
    before = list(st.tau)
    res = process_event(st, 3, B_, TBR)  # student 3 (C,D) adds B: B=1, C=2, D=0 -> no clash
    assert res.tier == TIER_NONE and st.tau == before


def test_event_with_no_other_exams():
    st = make_state(3, [(), (0, 1)], [0, 1, 0], 2)
    res = process_event(st, 0, 2, TBR)
    assert res.tier == TIER_NONE and st.adj[2] == {}


def test_determinism():
    rng_events = random.Random(5)
    n = 12
    students = [tuple(sorted(random.Random(i).sample(range(n), 3))) for i in range(15)]
    from examrepair.constructors import dsatur, n_colours
    from examrepair.model import build_adjacency
    tau = dsatur(build_adjacency(n, students))
    events = []
    probe = make_state(n, students, tau, n_colours(tau))
    for _ in range(40):
        s = rng_events.randrange(len(students))
        opts = [e for e in range(n) if e not in probe.enrol[s]]
        if opts:
            e = rng_events.choice(opts)
            probe.enrol[s].add(e)
            events.append((s, e))

    def run():
        st = make_state(n, students, tau, n_colours(tau))
        return [(r.tier, r.moves) for r in (process_event(st, s, e, TBR) for s, e in events)]

    assert run() == run()


def test_proximity_change_reported_matches_recomputed_cost():
    rng = random.Random(3)
    for _ in range(100):
        case = random_small_case(rng)
        if case is None:
            continue
        n, students, tau, k, (s, e) = case
        st = state_from(n, students, tau, k)
        apply_enrolment(st, s, e)
        before = raw_cost(st.adj, st.tau)
        st2 = state_from(n, students, tau, k)
        res = process_event(st2, s, e, TBR)
        after = raw_cost(st2.adj, st2.tau)
        assert after - before == res.dP_raw


def _students_from_graph(g):
    import networkx as nx
    g = nx.convert_node_labels_to_integers(g)
    return g.number_of_nodes(), [tuple(sorted(e)) for e in g.edges()]


@pytest.mark.parametrize("family", ["empty0", "isolated5", "single", "path7", "cycle8",
                                    "cycle9", "K6", "K3,4", "disconnected", "star"])
def test_tbr_on_graph_families(family):
    """R1: TBR stays valid on edge-case structures. Each edge is one student taking both
    exams; one extra student per exam enables late enrolments."""
    import networkx as nx
    from examrepair.constructors import dsatur, n_colours
    from examrepair.model import build_adjacency
    graphs = {
        "empty0": nx.empty_graph(0), "isolated5": nx.empty_graph(5), "single": nx.empty_graph(1),
        "path7": nx.path_graph(7), "cycle8": nx.cycle_graph(8), "cycle9": nx.cycle_graph(9),
        "K6": nx.complete_graph(6), "K3,4": nx.complete_bipartite_graph(3, 4),
        "disconnected": nx.disjoint_union(nx.complete_graph(4), nx.cycle_graph(5)),
        "star": nx.star_graph(6),
    }
    n, students = _students_from_graph(graphs[family])
    students = students + [(v,) for v in range(n)]
    tau = dsatur(build_adjacency(n, students))
    k = n_colours(tau)
    st = make_state(n, students, tau, k)
    if n == 0:
        assert st.is_proper() and st.k == 0
        return
    rng = random.Random(sum(map(ord, family)))  # stable seed (str hash is salted)
    for _ in range(3 * n):
        s = rng.randrange(len(students))
        opts = [e for e in range(n) if e not in st.enrol[s]]
        if not opts:
            continue
        res = process_event(st, s, rng.choice(opts), TBR)
        check_timetable(st.enrol, st.tau, st.k, n)
        assert res.D <= TBR.budget


# ---------------------------------------------------------------- TBR+ (addendum A)
from examrepair.repair import TBRPLUS, TIER_SEARCH  # noqa: E402


def test_tbrplus_solves_rotation_example():
    students, tau = rotation_example()
    st = make_state(6, students, tau, 3)
    res = process_event(st, 4, A, TBRPLUS)
    assert res.tier == TIER_SEARCH and res.D == 3 and res.dk == 0
    # rotating either triangle (A,B,C) or (D,E,F) is a 3-move optimum (W ties at 6)
    assert {m[0] for m in res.moves} in ({A, B_, C}, {D, E, F})
    check_timetable(st.enrol, st.tau, st.k, 6)


def test_tbrplus_exact_lexicographic_on_small_instances():
    """Theorem 5: with an unexhausted node budget TBR+ returns the lexicographic optimum
    (dk, D, W, dP) under budget B, checked against brute force on 300 random cases."""
    rng = random.Random(4242)
    cfg = RepairConfig("TBRPLUS_BIG", (1, 2, 3, 4), 8, True, 10**7)
    checked = 0
    while checked < 300:
        case = random_small_case(rng)
        if case is None:
            continue
        n, students, tau, k, (s, e) = case
        ref = state_from(n, students, tau, k)
        apply_enrolment(ref, s, e)
        d_star, sec = brute_force_repair(ref.adj, ref.tau, ref.k, ref.size)
        st = state_from(n, students, tau, k)
        res = process_event(st, s, e, cfg)
        check_timetable(st.enrol, st.tau, st.k, n)
        assert not res.extra.get("exhausted", False)
        if d_star is not None and d_star <= cfg.budget:
            assert (res.dk, res.D) == (0, d_star)
            assert (res.W, res.dP_raw) == sec
        else:
            assert res.dk == 1
        checked += 1


def test_tbrplus_valid_and_deterministic_on_streams():
    rng = random.Random(77)
    for _ in range(20):
        n = rng.randint(6, 16)
        students = [tuple(sorted(rng.sample(range(n), rng.randint(1, 4)))) for _ in range(14)]
        from examrepair.constructors import dsatur, n_colours
        from examrepair.model import build_adjacency
        tau = dsatur(build_adjacency(n, students))
        events = []
        probe = make_state(n, students, tau, n_colours(tau))
        for _ in range(30):
            s = rng.randrange(len(students))
            opts = [e for e in range(n) if e not in probe.enrol[s]]
            if opts:
                e = rng.choice(opts)
                probe.enrol[s].add(e)
                events.append((s, e))

        def run():
            st = make_state(n, students, tau, n_colours(tau))
            out = []
            for s, e in events:
                r = process_event(st, s, e, TBRPLUS)
                check_timetable(st.enrol, st.tau, st.k, n)
                assert r.D <= TBRPLUS.budget
                out.append((r.tier, r.moves))
            return out

        assert run() == run()


def test_search_respects_node_budget():
    from examrepair.search import bounded_repair_search
    students, tau = rotation_example()
    st = make_state(6, students, tau, 3)
    apply_enrolment(st, 4, A)
    out = bounded_repair_search(st, A, D, 3, 8, node_budget=1)
    assert out.exhausted and out.nodes == 2
