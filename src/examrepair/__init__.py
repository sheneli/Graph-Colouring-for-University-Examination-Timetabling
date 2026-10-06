"""examrepair: graph-colouring examination timetabling with disruption-budgeted repair.

Modules
-------
io            Load and validate Toronto (Carter) benchmark files.
model         Conflict graph and mutable timetable state; late-enrolment events.
proximity     Carter proximity cost and incremental change vectors.
constructors  Static colouring heuristics (first-fit, Welsh-Powell, smallest-last,
              DSATUR, RLF) used to build the initial published timetable.
repair        Tiered Budgeted Repair (TBR, original) and repair baselines.
recompute     Full-recomputation baseline (DSATUR + optimal period relabelling).
oracle        Exact minimum-move repair with OR-Tools CP-SAT (library solver).
streams       Late-enrolment stream generation and a synthetic instance generator.
validate      Independent timetable checker that never uses the algorithm's graph.

Original code vs library use is documented in each module docstring.
"""

__version__ = "1.0.0"
