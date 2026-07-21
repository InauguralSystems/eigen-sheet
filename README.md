# eigen-sheet

A spreadsheet **recalc engine** written in [EigenScript](https://github.com/InauguralSystems/EigenScript):
A1-style cells, formulas (`=` arithmetic over numbers, cell references, parens,
and `SUM(range)`), a dependency graph, a topological recalc, and cycle
detection. It runs standalone on the desktop and is designed for EigenOS's
desktop to import — the same `sheet.eigs`, not a private copy.

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

Importable surface: `new_sheet`, `set_cell`, `recalc`, `get`, `display`, and
`draw_grid` (the gfx front-end; `run` opens a window but is never called on
import, so `import sheet` is side-effect-free and headless-testable).

## Three oracles

A byte-diff against my own expectations is a golden master — it pins
regressions but can't say what *right* looks like. So correctness rests on
three **independent** checks:

1. **Model** (`tests/test_smoke.sh`) — replays cell edits, recalcs, and
   byte-diffs displayed values. *Self-consistency:* dependency chains, SUM,
   precedence, cycle → `#CYCLE`, topological order. Headless, no display.
2. **Differential vs a real spreadsheet** (`tests/diff_vs_calc.py`) — writes
   the same formulas to an `.xlsx` and byte-diffs eigen-sheet's recalc against
   **headless LibreOffice Calc**. *External truth:* for the numeric operations
   every spreadsheet agrees on — arithmetic, precedence, cell refs, `SUM` —
   what's right is what a real, used engine computes, not our say-so.
   LibreOffice's numbers are the reference. (Error tokens like `#CYCLE` and
   div-by-zero differ across engines, so they stay with the model oracle.)
3. **Render** (`tests/ui_oracle.py`) — because it's a UI, renders through the
   real `draw_grid`, screenshots the window, and **decodes each cell's pixels
   back into text**, asserting they equal the model. *Render fidelity:* a cell
   drawn in the wrong place, a dropped value, a wrong glyph. Exact decode via
   the deterministic bitmap-font atlas (12×14 px cells; forced via a
   nonexistent `EIGS_GFX_FONT`), self-validated by a planted fault (blank a
   cell — must be caught).

```sh
EIGENSCRIPT=… bash tests/test_smoke.sh                 # model
EIGENSCRIPT=… python3 tests/diff_vs_calc.py            # needs libreoffice-calc + openpyxl
xvfb-run -a python3 tests/ui_oracle.py                 # needs gfx build + xvfb + xdotool + PIL
```

CI runs all three as jobs (`test`, `calc-oracle`, `ui-oracle`).

## Scope (v0.1)

Numbers, `+ - * /`, parens and precedence, cell references, `SUM(range)`,
multi-letter columns, dependency-ordered recalc, cycle detection. Not yet:
in-app cell editing, more functions (AVG/MIN/MAX/IF), string formulas, mouse
selection + dropdowns (which will get a mouse-driven oracle when they land).

## License

MIT — see [LICENSE](LICENSE).
