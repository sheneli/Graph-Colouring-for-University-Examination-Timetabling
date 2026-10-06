"""Tests for data loading, stream generation and the independent checker."""

from pathlib import Path

import pytest

from examrepair.io import (OFFICIAL_PERIODS, TORONTO_NAMES, DataFormatError, load_named,
                           load_toronto)
from examrepair.streams import holdout_stream, synthetic_instance
from examrepair.validate import IncrementalChecker, TimetableError, check_timetable

DATA = Path(__file__).resolve().parents[1] / "data" / "raw" / "toronto"

# Published statistics (University of Nottingham dataset page; Qu et al., 2009).
PUBLISHED = {
    "car-s-91": (682, 16925, 56877), "car-f-92": (543, 18419, 55522),
    "ear-f-83": (190, 1125, 8109), "hec-s-92": (81, 2823, 10632),
    "kfu-s-93": (461, 5349, 25113), "lse-f-91": (381, 2726, 10918),
    "pur-s-93": (2419, 30029, 120681), "rye-s-93": (486, 11483, 45051),
    "sta-f-83": (139, 611, 5751), "tre-s-92": (261, 4360, 14901),
    "uta-s-92": (622, 21266, 58979), "ute-s-92": (184, 2749, 11793),
    "yor-f-83": (181, 941, 6034),
}

needs_data = pytest.mark.skipif(not DATA.exists(), reason="Toronto data not downloaded")


@needs_data
@pytest.mark.parametrize("name", TORONTO_NAMES)
def test_toronto_statistics_match_published(name):
    inst = load_named(DATA, name)
    assert (inst.n_exams, inst.n_students, inst.n_enrolments) == PUBLISHED[name]
    # .crs declared counts agree with .stu enrolments
    counts = [0] * inst.n_exams
    for s in inst.students:
        for e in s:
            counts[e] += 1
    assert tuple(counts) == inst.crs_counts
    assert name in OFFICIAL_PERIODS


def _write(tmp_path, crs, stu):
    c, s = tmp_path / "x.crs", tmp_path / "x.stu"
    c.write_text(crs)
    s.write_text(stu)
    return c, s


@pytest.mark.parametrize("crs,stu", [
    ("0001 2\n0002 x\n", "0001 0002\n"),          # non-integer count
    ("0001 2\n0001 3\n", "0001\n"),               # duplicate exam id
    ("0001 2 9\n", "0001\n"),                     # wrong field count
    ("0001 2\n", "0001 0007\n"),                  # unknown exam on student line
    ("0001 2\n0002 1\n", "0001 0001\n"),          # duplicate exam on one line (strict)
    ("0001 -2\n", "0001\n"),                      # negative
    ("", "0001\n"),                               # no exams
])
def test_malformed_files_rejected(tmp_path, crs, stu):
    c, s = _write(tmp_path, crs, stu)
    with pytest.raises(DataFormatError):
        load_toronto(c, s)


def test_non_strict_removes_duplicates(tmp_path):
    c, s = _write(tmp_path, "0001 2\n0002 1\n", "0001 0001 0002\n\n0001\n")
    inst = load_toronto(c, s, strict=False)
    assert inst.students == ((0, 1), (0,))


def test_holdout_stream_reproducible_and_consistent():
    inst = synthetic_instance(60, seed=1, students_per_exam=4)
    a = holdout_stream(inst, 30, seed=3)
    b = holdout_stream(inst, 30, seed=3)
    assert a == b
    assert len(set(a.events)) == 30
    for (s, e) in a.events:
        assert e in inst.students[s] and e not in a.initial_students[s]
    removed = sum(len(x) for x in inst.students) - sum(len(x) for x in a.initial_students)
    assert removed == 30
    assert holdout_stream(inst, 30, seed=4).events != a.events


def test_holdout_too_many():
    inst = synthetic_instance(20, seed=1, students_per_exam=1)
    with pytest.raises(ValueError):
        holdout_stream(inst, 10_000, seed=0)


def test_synthetic_deterministic():
    assert synthetic_instance(50, 2).students == synthetic_instance(50, 2).students
    inst = synthetic_instance(50, 2)
    assert all(3 <= len(s) <= 7 and len(set(s)) == len(s) for s in inst.students)


def test_checker_detects_clash_and_bad_period():
    students = [(0, 1), (1, 2)]
    check_timetable(students, [0, 1, 0], 2, 3)
    with pytest.raises(TimetableError):
        check_timetable(students, [0, 0, 1], 2, 3)
    with pytest.raises(TimetableError):
        check_timetable(students, [0, 1, 2], 2, 3)
    with pytest.raises(TimetableError):
        check_timetable(students, [0, 1], 2, 3)


def test_incremental_checker_detects_injected_clash():
    students = [(0, 1), (2,)]
    chk = IncrementalChecker(students, [0, 1, 0], 2, 3)
    # student 1 enrols in exam 0 but the "algorithm" did not repair -> clash 0/2 both period 0
    with pytest.raises(TimetableError):
        chk.after_event(1, 0, [0, 1, 0], 2)
    chk2 = IncrementalChecker(students, [0, 1, 0], 2, 3)
    assert chk2.after_event(1, 0, [0, 1, 1], 2) == 1
