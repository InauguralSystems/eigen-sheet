# Number bar baseline

BASE is `93ab47c21e9e30eeb09e9d6bfd0accb3762fd28e`. The tool derives 115
formula-reachable dispatcher names by deduplicating `fname == "NAME"` clauses;
the 229 clause occurrences repeat names across parser paths and include aliases.

Displays follow `tests/diff_vs_calc.py`: exact text first, otherwise finite numeric
values within absolute `1e-9`. Calc is the reference. The containment net is not
observable and is therefore `unknown`, never silently counted as a match.

## BASE tree with NEW (`phase2-consumers-1`)

The setup/build completed, but the full run was NOT-RUN before the task clock.
These are population sizes, explicitly not verdicts:

- `SET class examined=5418 match=NOT-RUN differ=NOT-RUN net=unknown`
- `SET wrappers examined=630 match=NOT-RUN differ=NOT-RUN net=unknown`
- `SET number-text examined=280 match=NOT-RUN differ=NOT-RUN net=unknown`
- `SET c-sumif examined=7 match=NOT-RUN differ=NOT-RUN net=unknown`
- `SET c1 examined=12 match=NOT-RUN differ=NOT-RUN net=unknown`
- `SET c10 examined=22 match=NOT-RUN differ=NOT-RUN net=unknown`
- `SET c20 examined=114 match=NOT-RUN differ=NOT-RUN net=unknown`
- `SET c22 examined=56 match=NOT-RUN differ=NOT-RUN net=unknown`
- `SET c23 examined=19 match=NOT-RUN differ=NOT-RUN net=unknown`
- `SET c24 examined=16 match=NOT-RUN differ=NOT-RUN net=unknown`
- `SET c25 examined=3 match=NOT-RUN differ=NOT-RUN net=unknown`
- `SET c4 examined=46 match=NOT-RUN differ=NOT-RUN net=unknown`
- `SET c5 examined=14 match=NOT-RUN differ=NOT-RUN net=unknown`
- `SET c6 examined=18 match=NOT-RUN differ=NOT-RUN net=unknown`
- `SET c7 examined=12 match=NOT-RUN differ=NOT-RUN net=unknown`
- `SET c8 examined=6 match=NOT-RUN differ=NOT-RUN net=unknown`
- `SET c9 examined=6 match=NOT-RUN differ=NOT-RUN net=unknown`

- `NUMBER-BAR examined=6679 differ=NOT-RUN net=unknown`

## main tree with OLD (`v0.48.0`)

NOT-REACHED. Consequently there is no defensible before-runtime difference count
or exclusion list yet; `known_before.json` is an empty, machine-readable list,
not a claim that the before population had zero differences.

## Cost and scheduling

The complete bar is enrolled in the `calc-oracle` job only for manual workflow
dispatch; its fast fault plants run on every calc-oracle job. Runtime remains to
be measured by a completed run; no minute estimate is asserted without one.
