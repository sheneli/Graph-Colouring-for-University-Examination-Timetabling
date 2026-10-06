"""Loading and validating Toronto (Carter et al., 1996) examination timetabling files.

File formats (Toronto version I, as distributed by the University of Nottingham page
https://people.cs.nott.ac.uk/pszrq/data.htm):

* ``<name>.crs``: one line per exam, ``<exam id> <number of enrolled students>``.
* ``<name>.stu``: one line per student, the space-separated IDs of that student's exams.

Exam IDs in the files are 1-based and zero-padded; internally exams are re-indexed to
0..n-1 in increasing order of their file ID. Students are indexed 0..|S|-1 in file order
(blank lines are skipped). All code in this module is original.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


class DataFormatError(ValueError):
    """Raised when an input file violates the expected format."""


@dataclass(frozen=True)
class Instance:
    """An examination timetabling instance.

    Attributes
    ----------
    name:      instance name (e.g. ``"car-s-91"``).
    n_exams:   number of exams n (vertices).
    exam_ids:  original file IDs, ``exam_ids[i]`` is the file ID of internal exam ``i``.
    students:  tuple of per-student sorted tuples of internal exam indices.
    crs_counts: enrolment counts declared in the .crs file (used only for validation).
    """

    name: str
    n_exams: int
    exam_ids: tuple[int, ...]
    students: tuple[tuple[int, ...], ...]
    crs_counts: tuple[int, ...] = field(default=())

    @property
    def n_students(self) -> int:
        return len(self.students)

    @property
    def n_enrolments(self) -> int:
        return sum(len(s) for s in self.students)


def _parse_int(token: str, path: Path, lineno: int) -> int:
    try:
        value = int(token)
    except ValueError as exc:
        raise DataFormatError(f"{path}:{lineno}: non-integer token {token!r}") from exc
    if value < 0:
        raise DataFormatError(f"{path}:{lineno}: negative value {value}")
    return value


def load_toronto(crs_path: str | Path, stu_path: str | Path, *, strict: bool = True,
                 name: str | None = None) -> Instance:
    """Load and validate a Toronto instance.

    Parameters
    ----------
    crs_path, stu_path: paths to the ``.crs`` and ``.stu`` files.
    strict: if True (default) duplicate exams on one student line, unknown exam IDs,
        duplicate exam IDs in the .crs file and malformed lines raise
        :class:`DataFormatError`. If False, duplicate exams on a line are removed
        (unknown IDs and malformed lines always raise).
    name: optional instance name; defaults to the .stu file stem.

    Returns
    -------
    Instance
    """
    crs_path, stu_path = Path(crs_path), Path(stu_path)
    declared: dict[int, int] = {}
    with crs_path.open() as fh:
        for lineno, line in enumerate(fh, start=1):
            tokens = line.split()
            if not tokens:
                continue
            if len(tokens) != 2:
                raise DataFormatError(f"{crs_path}:{lineno}: expected 2 fields, got {len(tokens)}")
            exam, count = (_parse_int(t, crs_path, lineno) for t in tokens)
            if exam in declared:
                raise DataFormatError(f"{crs_path}:{lineno}: duplicate exam id {exam}")
            declared[exam] = count
    if not declared:
        raise DataFormatError(f"{crs_path}: no exams")

    exam_ids = tuple(sorted(declared))
    index = {eid: i for i, eid in enumerate(exam_ids)}

    students: list[tuple[int, ...]] = []
    with stu_path.open() as fh:
        for lineno, line in enumerate(fh, start=1):
            tokens = line.split()
            if not tokens:
                continue
            exams = [_parse_int(t, stu_path, lineno) for t in tokens]
            unknown = [x for x in exams if x not in index]
            if unknown:
                raise DataFormatError(f"{stu_path}:{lineno}: unknown exam id(s) {unknown}")
            if len(set(exams)) != len(exams):
                if strict:
                    raise DataFormatError(f"{stu_path}:{lineno}: duplicate exam on one line")
                exams = list(dict.fromkeys(exams))
            students.append(tuple(sorted(index[x] for x in exams)))

    return Instance(
        name=name or stu_path.stem,
        n_exams=len(exam_ids),
        exam_ids=exam_ids,
        students=tuple(students),
        crs_counts=tuple(declared[e] for e in exam_ids),
    )


def load_named(data_dir: str | Path, name: str, **kwargs) -> Instance:
    """Load ``<data_dir>/<name>.crs`` and ``<data_dir>/<name>.stu``."""
    data_dir = Path(data_dir)
    return load_toronto(data_dir / f"{name}.crs", data_dir / f"{name}.stu", name=name, **kwargs)


TORONTO_NAMES = (
    "car-f-92", "car-s-91", "ear-f-83", "hec-s-92", "kfu-s-93", "lse-f-91", "pur-s-93",
    "rye-s-93", "sta-f-83", "tre-s-92", "uta-s-92", "ute-s-92", "yor-f-83",
)

#: Published period counts (Qu et al., 2009; University of Nottingham dataset page).
OFFICIAL_PERIODS = {
    "car-f-92": 32, "car-s-91": 35, "ear-f-83": 24, "hec-s-92": 18, "kfu-s-93": 20,
    "lse-f-91": 18, "pur-s-93": 42, "rye-s-93": 23, "sta-f-83": 13, "tre-s-92": 23,
    "uta-s-92": 35, "ute-s-92": 10, "yor-f-83": 21,
}
