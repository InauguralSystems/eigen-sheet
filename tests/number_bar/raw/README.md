# Raw material for the number-boundary bar (#104): an independent review's harness, as it was run

These files are NOT a test of this repository and nothing runs them. They are the harness and the case sets with which the third independent review of #103 compared this spreadsheet with LibreOffice Calc, cell by cell. They are here so that the bar #104 asks for can be built from them; the bar replaces this folder.

- `h.py`: runs a case file through eigen-sheet (one process for each tested cell, or one for a grid) and through LibreOffice (one `.xlsx`), and prints both. The placeholders `REVIEW_DIR`, `NEW_RUNTIME_BINARY` and `OLD_RUNTIME_BINARY` stand for paths of the machine it ran on.
- `gen2.py`: the class cells. A hand-written list of one template for each numeric argument position of the dispatcher's functions, each with seven bad arguments (`OVF`, `DIV`, `LN0`, `INF`, `INF2`, `NAN`, `SUMINF`), each bare, inside `ABS`, inside `IFERROR`, and inside both: about 2,800 cells over the seven families.
- `gen3.py` and `c3.json`: number to text (280 cells).
- `c21.json`: the wrapper set, 630 cells: 9 error sources x 10 operator shapes x 7 wrappers (bare, `IFERROR`, `IFNA`, `ISERROR`, `ISERR`, `ISNA`, and one more: read the file).
- `c20.json`, `c22.json`, `c24.json`, `c4.json` to `c10.json`: whole numbers past 2^53 and at the 64-bit limits arriving through a cell, a range, an aggregate, a criterion, a lookup key, a comparison; `c23.json`: `ROUND`, `REPT` and `SUMIF` at their edges; `c25.json` and `c-sumif.json`: three ordinary formulas the fourth repair round broke.
- `api/`: the paths outside recalc (a named range, pivot, sort and fill, goal seek, CSV in and out, save and load, the status bar), each as a program against the library.
- `probe_plus.py`, `reg.py`, `an.py`, `mkplant.py`: the review's own helpers (a probe of the repository's class probe, a regression counter between two heads, a summary, and the plants it made).
