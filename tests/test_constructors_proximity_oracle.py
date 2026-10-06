"""Tests for static constructors, proximity cost, recomputation baseline and the oracle."""

import itertools
import random

import networkx as nx
import pytest

from examrepair.constructors import (CONSTRUCTORS, dsatur, greedy_clique_lower_bound,
                                     is_proper, n_colours, smallest_last_order)
from examrepair.model import apply_enrolment, build_adjacency, make_state
from examrepair.oracle import min_moves
from examrepair.proximity import delta_moves, delta_vector, pi, raw_cost
from examrepair.recompute import process_event_recompute, relabel_to_periods
from examrepair.validate import check_timetable

from helpers import brute_force_repair, random_small_case, state_from


def adj_of(g: nx.Graph):
    g = nx.convert_node_labels_to_integers(g)
    return [{u: 1 for u in g[v]} for v in range(g.number_of_nodes())]


FAMILIES = {
    "empty0": (nx.empty_graph(0), 0),
    "isolated5": (nx.empty_graph(5), 1),
    "single": (nx.empty_graph(1), 1),
    "path7": (nx.path_graph(7), 2),
    "cycle8": (nx.cycle_graph(8), 2),
    "cycle9": (nx.cycle_graph(9), 3),
    "K6": (nx.complete_graph(6), 6),
    "K3,4": (nx.complete_bipartite_graph(3, 4), 2),
    "disconnected": (nx.disjoint_union(nx.complete_graph(4), nx.cycle_graph(5)), 4),
    "star": (nx.star_graph(6), 2),
}


@pytest.mark.parametrize("fam", list(FAMILIES))
@pytest.mark.parametrize("name", list(CONSTRUCTORS))
def test_constructors_proper_on_families(fam, name):
    g, chi = FAMILIES[fam]
    adj = adj_of(g)
    col = CONSTRUCTORS[name](adj)
    assert len(col) == len(adj)
    assert is_proper(adj, col)
    assert n_colours(col) >= chi
    if name in ("dsatur",) and fam in ("path7", "cycle8", "K3,4", "star", "K6", "cycle9",
                                       "isolated5", "single", "empty0"):
        # DSATUR is exact on bipartite graphs (Brelaz, 1979), complete graphs and odd cycles
        assert n_colours(col) == chi


@pytest.mark.parametrize("name", list(CONSTRUCTORS))
def test_constructors_proper_on_random_graphs(name):
    rng = random.Random(1)
    for _ in range(40):
        n = rng.randint(1, 40)
        g = nx.gnp_random_graph(n, rng.random() * 0.5, seed=rng.randint(0, 10**6))
        adj = adj_of(g)
        col = CONSTRUCTORS[name](adj)
        assert is_proper(adj, col)
        assert n_colours(col) >= greedy_clique_lower_bound(adj)


def test_smallest_last_is_permutation():
    g = nx.gnp_random_graph(30, 0.2, seed=4)
    order = smallest_last_order(adj_of(g))
    assert sorted(order) == list(range(30))


def test_dsatur_against_networkx_quality_band():
    """Cross-check with the NetworkX library implementation (not used by our algorithm)."""
    rng = random.Random(9)
    for _ in range(20):
        g = nx.gnp_random_graph(60, 0.15, seed=rng.randint(0, 10**6))
        ours = n_colours(dsatur(adj_of(g)))
        lib = max(nx.greedy_color(g, strategy="DSATUR").values()) + 1
        assert abs(ours - lib) <= 2


def test_pi_values():
    assert [pi(d) for d in range(8)] == [0, 16, 8, 4, 2, 1, 0, 0]
    assert pi(-3) == 4


def test_delta_vector_and_moves_match_bruteforce():
    rng = random.Random(5)
    for _ in range(200):
        n = rng.randint(2, 12)
        students = [tuple(sorted(rng.sample(range(n), rng.randint(1, min(4, n)))))
                    for _ in range(10)]
        adj = build_adjacency(n, students)
        k = rng.randint(2, 9)
        tau = [rng.randrange(k) for _ in range(n)]
        base = raw_cost(adj, tau)
        x = rng.randrange(n)
        vec = delta_vector(adj, tau, x, k)
        for p in range(k):
            t2 = list(tau)
            t2[x] = p
            assert raw_cost(adj, t2) - base == vec[p]
        moves = {v: rng.randrange(k + 1) for v in rng.sample(range(n), rng.randint(1, n))}
        t3 = list(tau)
        for v, p in moves.items():
            t3[v] = p
        assert raw_cost(adj, t3) - base == delta_moves(adj, tau, moves)


def test_delta_vector_override():
    rng = random.Random(6)
    for _ in range(100):
        n = rng.randint(3, 10)
        students = [tuple(sorted(rng.sample(range(n), rng.randint(2, min(4, n)))))
                    for _ in range(8)]
        adj = build_adjacency(n, students)
        k = 6
        tau = [rng.randrange(k) for _ in range(n)]
        x, w = rng.sample(range(n), 2)
        px = rng.randrange(k)
        t1 = list(tau)
        t1[x] = px
        base = raw_cost(adj, t1)
        vec = delta_vector(adj, tau, w, k, override={x: px})
        for q in range(k):
            t2 = list(t1)
            t2[w] = q
            assert raw_cost(adj, t2) - base == vec[q]


def test_relabel_maximises_agreement():
    rng = random.Random(8)
    for _ in range(100):
        n, k = rng.randint(2, 9), rng.randint(1, 4)
        old = [rng.randrange(k) for _ in range(n)]
        c = rng.randint(1, 5)
        new = [rng.randrange(c) for _ in range(n)]
        new = [sorted(set(new)).index(x) for x in new]  # compact colours
        out = relabel_to_periods(new, old, k)
        agree = sum(a == b for a, b in zip(out, old))
        cc = max(new) + 1
        best = 0
        for perm in itertools.permutations(range(max(cc, k)), cc):
            best = max(best, sum(perm[new[v]] == old[v] for v in range(n)))
        assert agree == best
        # injective mapping of colour classes
        assert len({(new[v], out[v]) for v in range(n)}) == len(set(new))


def test_recompute_valid():
    rng = random.Random(10)
    for _ in range(60):
        case = random_small_case(rng)
        if case is None:
            continue
        n, students, tau, k, (s, e) = case
        st = state_from(n, students, tau, k)
        res = process_event_recompute(st, s, e)
        check_timetable(st.enrol, st.tau, st.k, n)
        assert st.k >= k and res.dk == st.k - k


def test_oracle_matches_bruteforce():
    rng = random.Random(12)
    done = 0
    while done < 40:
        case = random_small_case(rng)
        if case is None:
            continue
        n, students, tau, k, (s, e) = case
        st = state_from(n, students, tau, k)
        apply_enrolment(st, s, e)
        d_star, _ = brute_force_repair(st.adj, st.tau, st.k, st.size)
        o = min_moves(st.adj, st.tau, st.k, time_limit=10)
        if d_star is None:
            assert o.status == "INFEASIBLE"
        else:
            assert o.status == "OPTIMAL" and o.d_star == d_star
        done += 1


def test_oracle_infeasible_k4_in_3():
    adj = adj_of(nx.complete_graph(4))
    o = min_moves(adj, [0, 1, 2, 0], 3, time_limit=5)
    assert o.status == "INFEASIBLE"
