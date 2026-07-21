# eigen-sheet

A spreadsheet **recalc engine** written in [EigenScript](https://github.com/InauguralSystems/EigenScript):
A1-style cells, formulas (`=` arithmetic over numbers, cell references, parens,
`SUM(range)`, and text — string literals, the `&` concatenation operator, and
text functions), a dependency graph, a topological recalc, and cycle detection.
It runs standalone on the desktop and is designed for EigenOS's desktop to
import — the same `sheet.eigs`, not a private copy.

![eigen-sheet grid view](docs/screenshot.png)

A spreadsheet is the sharpest fit for EigenScript's observer niche: a cell's
value is a function of the cells it *observes*, a change propagates along the
dependency edges, and a cycle is an observation with no fixed point — reported
as `#CYCLE` instead of looping. Editing is a replayable event stream; the same
edits in the same order reconstruct the same grid.

## Run it standalone

```sh
git clone https://github.com/InauguralSystems/EigenScript.git
make -C EigenScript gfx
EigenScript/src/eigenscript main.eigs      # opens the grid (demo sheet); Escape quits
```

## Use the engine as a library

```eigenscript
import sheet
s is sheet.new_sheet of null
sheet.set_cell of [s, "A1", "5"]
sheet.set_cell of [s, "A2", "3"]
sheet.set_cell of [s, "A3", "=A1+A2"]
sheet.set_cell of [s, "A4", "=SUM(A1:A3)"]
sheet.recalc of s
print of (sheet.get of [s, "A4"])           # -> 16
```

Importable surface: `new_sheet`, `set_cell`, `define_name`, `set_format`,
`register_udf`, `recalc`, `get`, `display`, `to_csv` / `from_csv`, `to_xlsx`,
`sort_range`, `find_cells` / `replace_cells`, `pivot`, `goal_seek`, and
`draw_grid` (the gfx front-end;
`run` opens a window but is never called on import, so `import sheet` is
side-effect-free and headless-testable).

## The oracles

A byte-diff against my own expectations is a golden master — it pins
regressions but can't say what *right* looks like. So correctness rests on
several **independent** checks:

1. **Model** (`tests/test_smoke.sh`) — replays cell edits, recalcs, and
   byte-diffs displayed values. *Self-consistency:* dependency chains, SUM,
   precedence, cycle → `#CYCLE`, topological order. Headless, no display.
2. **Differential vs a real spreadsheet** (`tests/diff_vs_calc.py` for numbers,
   `tests/diff_vs_calc_str.py` for text) — writes the same formulas to an
   `.xlsx` and byte-diffs eigen-sheet's recalc against **headless LibreOffice
   Calc**. *External truth:* for the operations every spreadsheet agrees on —
   arithmetic, precedence, cell refs, `SUM`, and on the text side `&`
   concatenation, the text functions, number↔text coercion, and
   case-insensitive text comparison — what's right is what a real, used engine
   computes, not our say-so. LibreOffice's output is the reference. (Error
   tokens like `#CYCLE`, `#VALUE!`, and div-by-zero differ across engines, so
   they stay with the model oracle.)
3. **Render** (`tests/ui_oracle.py`) — because it's a UI, renders through the
   real `draw_grid`, screenshots the window, and **decodes each cell's pixels
   back into text**, asserting they equal the model. *Render fidelity:* a cell
   drawn in the wrong place, a dropped value, a wrong glyph. Exact decode via
   the deterministic bitmap-font atlas (12×14 px cells; forced via a
   nonexistent `EIGS_GFX_FONT`), self-validated by a planted fault (blank a
   cell — must be caught).
4. **Mouse** (`tests/mouse_oracle.py`) — the grid view has mouse-driven
   controls (click a cell to select; an "Insert" dropdown that edits the
   selected cell), and a dropdown isn't verified until a real click moved real
   pixels. This drives **real xdotool pointer input** through the whole flow —
   select A4 → open the dropdown → click `=A1*A2` — and decodes the grid to
   assert A4 became 15 **and** B1 recomputed 31→29 (the mouse edit propagated
   through the dependency graph). The menu item must win the click over the
   grid cell beneath it (the popup click-trap), and a no-op drive can't pass
   (the post-click grid must differ from the untouched baseline).
5. **Data-operation differentials vs Python** — deterministic data operations
   each get a canonical Python reference (like vim was for eigen-edit):
   `diff_vs_csv.py` (`to_csv`/`from_csv` vs the `csv` module + round-trip),
   `diff_vs_sort.py` (`sort_range` vs stable `sorted()`),
   `diff_vs_findreplace.py` (`find_cells`/`replace_cells` vs Python string ops),
   `diff_vs_pivot.py` (`pivot` vs a Python groupby), `diff_vs_filter.py`
   (`filter_rows` vs a Python predicate match), and `diff_vs_goalseek.py`
   (`goal_seek`'s secant vs an independent Python **bisection** — two different
   root-finders landing on the same root). *External truth:* what's right is what
   the standard library computes, not our say-so. Pure Python — no LibreOffice —
   so they run in the lightweight `test` job.

```sh
EIGENSCRIPT=… bash tests/test_smoke.sh                 # model
EIGENSCRIPT=… python3 tests/diff_vs_calc.py            # numeric diff: needs libreoffice-calc + openpyxl
EIGENSCRIPT=… python3 tests/diff_vs_calc_str.py        # string diff: same deps
EIGENSCRIPT=… python3 tests/diff_vs_csv.py             # CSV / sort / findreplace / pivot: pure Python
EIGENSCRIPT=… python3 tests/diff_vs_sort.py
EIGENSCRIPT=… python3 tests/diff_vs_findreplace.py
EIGENSCRIPT=… python3 tests/diff_vs_pivot.py
xvfb-run -a python3 tests/ui_oracle.py                 # render: needs gfx build + xvfb + xdotool + PIL
xvfb-run -a python3 tests/mouse_oracle.py              # mouse: same deps
```

CI runs `test` (model + the Python data-op differentials), `calc-oracle`
(numeric + string vs LibreOffice), and `ui-oracle` (render + mouse).

## Scope

Numbers, `+ - * /`, `^` (exponent, left-associative like Calc), parens and
precedence, comparisons (`> < >= <= = <>`, yielding first-class `TRUE`/`FALSE` that
display as such but coerce to `1`/`0` in arithmetic and `"1"`/`"0"` in
concatenation, like Calc), cell references (relative and `$`-anchored
absolute / mixed — `$A$1`, `$A1`, `A$1`), multi-letter
columns, range aggregates `SUM` / `AVERAGE` (`AVG`) / `MIN` / `MAX` /
`PRODUCT`, `IF(cond, then, else)` (nestable, short-circuiting — the untaken
branch is never evaluated), the logical functions `AND` / `OR` / `NOT` /
`XOR` / `TRUE` / `FALSE` / `IFS` / `SWITCH`, the scalar math functions
`ABS` / `INT` / `TRUNC` / `ROUND` / `ROUNDUP` / `ROUNDDOWN` / `SIGN` / `SQRT`
/ `MOD` / `POWER` / `CEILING` / `FLOOR`, the statistical functions `COUNT` /
`COUNTA` / `COUNTBLANK` / `MEDIAN` / `MODE` / `STDEV` / `STDEVP` / `VAR` /
`VARP`, the lookup & reference functions `VLOOKUP` / `HLOOKUP` / `LOOKUP` /
`XLOOKUP` / `INDEX` / `MATCH` / `ROW` / `COLUMN` / `ROWS` / `COLUMNS`, the
date & time functions `DATE` / `YEAR` / `MONTH` / `DAY` / `WEEKDAY` /
`EDATE` / `EOMONTH` / `DATEVALUE` / `DATEDIF` / `TIME` / `HOUR` / `MINUTE` /
`SECOND` (a serial-date model on LibreOffice's epoch),
named ranges / expressions (`define_name` — `=SUM(revenue)`, `=taxrate*100`;
alpha names, resolved before recalc so dependencies are captured),
dependency-ordered recalc (an O(V+E) in-degree topological pass; a reused
evaluator state keeps a large sheet from thrashing the allocator), cycle
detection, and a sparse cell store so the full Calc addressing extent
(`XFD1048576` = 16384 × 1,048,576) costs nothing until used. **Errors** (`#DIV/0!`, `#VALUE!`,
`#NAME?`, `#REF!`, `#N/A`, `#NUM!`, `#CYCLE`) propagate through cell
references and ranges — a formula reading an errored cell yields that error,
not a silent `0` — and `IFERROR` / `IFNA` / `NA()` catch or raise them.
**Text:** string literals
(`"..."`, `""` escapes a quote), the `&` concatenation operator (looser than
arithmetic, tighter than comparison, coercing numbers to text so `=5&"x"` is
`5x`), the text functions `LEN` / `UPPER` / `LOWER` / `TRIM` / `LEFT` /
`RIGHT` / `MID` / `CONCATENATE` / `FIND` / `SEARCH` / `SUBSTITUTE` /
`REPLACE` / `REPT` / `PROPER` / `EXACT` / `TEXTJOIN` / `CHAR` / `CODE` /
`VALUE` / `TEXT` (number/date formatting), case-insensitive text comparison (`="a"="A"`
is true), and number↔text coercion (non-numeric text in arithmetic is
`#VALUE!`). Text left-aligns, numbers right-align. **I/O:** `to_csv` / `from_csv`
(RFC-4180, with quoting and round-trip) and `to_xlsx` (writes a real
`.xlsx` — a stored-ZIP of OOXML built by hand with a hand-rolled CRC32, since
EigenScript has byte I/O and bitwise ops but no zip library; opens in Excel
and LibreOffice). **Data:** `sort_range` (stable sort
of a range by a key column, ascending/descending, numbers before text),
`find_cells` / `replace_cells` (literal, case-sensitive or not, over raw
cell content), `filter_rows` (select the data rows of a range matching
per-column criteria — `= <> > < >= <=` or `contains`, ANDed), `pivot` (group a source range by a row field and aggregate a
data field — SUM/COUNT/AVERAGE/MIN/MAX — with a grand total). **What-if:**
`goal_seek` (find the input that drives a formula cell to a target — the
observer model run backward, by the secant method). **User functions:**
`register_udf` — call any EigenScript function from a formula
(`=MYFN(A1, B1:B3)`; a single cell arrives as a scalar, a range as a value
list). The host language *is* EigenScript, so this needs no separate macro
layer, and a UDF's argument cells are captured as dependencies, so it recalcs
in order and updates when its inputs change.
**Number formats:** `set_format` / `TEXT` — decimals, thousands grouping,
percent, currency, and `Y`/`M`/`D` date codes (`#,##0.00`, `0%`,
`$#,##0.00`, `YYYY-MM-DD`). Interactive: in-cell editing
with a formula bar, click-drag range selection with a live Sum/Average/Count
status bar, copy/paste with relative-reference adjustment — anchored `$` parts stay
fixed (`Ctrl+C`/`V`),
undo/redo (`Ctrl+Z`/`Y`), and delete-to-clear. Not yet: menus/toolbar,
scrollbars, sheet tabs.

## License

MIT — see [LICENSE](LICENSE).
