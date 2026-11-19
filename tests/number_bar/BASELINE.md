# Number-boundary bar baseline for #104

This is measured output, not an expected-value source. LibreOffice Calc decides every expected answer.

## The rule

Calc is given every judged cell with the number format `0.00000000000000E+00` (fifteen significant digits, scientific) and converts the sheet to CSV with "save cell contents as shown", so C, Calc's text for a cell, is a number in one spelling whatever Calc would have auto-formatted (a time, a date, a percent, a logical). The same sheet without the format is converted in the same call and read only for the shape of a result whose C has that spelling: `TRUE` or `FALSE` there is a logical; the same text there is a text that only looks like a number. A sentinel text on every row must come back; a missing Calc row is the tool's error, never an expectation of blank. For one cell, with C and this spreadsheet's VALUE (`sheet.get`, a logical read as its number) and DISPLAY (`sheet.display`):

- **C is a number.** The cell matches when the VALUE is a number that agrees with C to within one unit in the fifteenth significant digit of the larger of the two in size (both zero agree), and the DISPLAY reads as a decimal number that agrees with C by the same rule and, when the VALUE is whole and below 1e15 in size, is plain digits with an optional minus sign (no `.0` ending, no exponent). When Calc's result is a logical, the VALUE must be a logical of that value and the DISPLAY `TRUE` or `FALSE` as Calc's is. Anything else differs: an error, a text, `#ERROR`, a crash.
- **C is an error** (it starts with `#`, or is `Err:<digits>`). The cell matches when this spreadsheet's cell holds an error value other than `#ERROR` (its marker that the evaluation itself failed), and, where C is one of Excel's seven names (`#DIV/0!`, `#N/A`, `#NAME?`, `#NULL!`, `#NUM!`, `#REF!`, `#VALUE!`) or another `#` name, the same name; where C is `Err:<digits>`, any of the seven.
- **C is anything else** (a text result, an empty result): the DISPLAY equals C exactly, and the cell holds no error.

A cell the per-cell net in recalc caught (`sheet.net_caught`) counts as differing whatever its text. No other tolerance exists in the tool.

`differ` counts every cell that does not match: no cell is set apart. `before` subtracts nothing: of the formula cells that differ now, it counts those whose answer on this repository's `main` with the OLD runtime was the same (the same number by the rule's agreement, the same error name, the same text, or the same CRASH or TIMEOUT). `before.json` holds that run's answers keyed by set, formula text and the set's input cells, is written whole by `--write-before`, and a key no present cell has is the tool's error. A failed chunk is retried cell by cell; an OLD cell that does not finish is recorded `TIMEOUT` after the fixed 10-second per-cell limit. The api set has no `before`.

Exit 0 only when `differ`, `net`, `crash` and `rule_differ` are all 0 and every set ran; 1 when any is not; 2 for the tool's own errors.

## The population

Every run derives 115 dispatcher rows from `sheet.eigs`. Each row contains Calc's fullest valid implemented call, a source citation, a label for every argument position, and the applicable generated arrival paths for every position. Every scalar position is expanded regardless of whether its label is number, logical, text, or criterion. Reference-only range positions cannot receive a single inline scalar, are printed in `left_out`, and receive generated inside-range cells instead. `AVG` is given to Calc as its `AVERAGE` equivalent. Calc 24.2's missing exact `XLOOKUP(k,keys,values,missing)` is given as the equivalent `IFERROR(INDEX(values,MATCH(k,keys,0)),missing)`. These are formula equivalents, never hand-written answers.

There are 12 bad-value kinds. `--sources` independently asks Calc and this spreadsheet for each source alone. In particular, the nonfinite function is dispatcher function `POWER`; `0.5^-2000` is named floating overflow; `3037000500*3037000500` is named an inline large double; and typed integer product, sum, and negative-end difference arrive through references to typed cells.

Arrival cells are generated from every row's per-position path metadata for every source: formula-cell reference, inside-range, criterion, lookup key, and either side of a comparison where applicable. `arrival_cases.json` retains only compound/cross-cell regression formulas that are not textually generated, and each retained set states that purpose.

## Provenance and count

LibreOffice Calc 24.2. NEW is EigenScript tag `phase2-consumers-1`, commit `b9881574b20503c5cfbdb6d80a5e6008e7501e15`, built exactly as `calc-oracle` builds it with `make -s zlib`. OLD is tag `v0.48.0`, commit `546848c0a7123ea7066923ebadb06f0af29af953`, built outside this checkout with the same target. The delivered tree starts at `36dd8059a305970405541fe4d3eae28c7b45d222`; the plain main tree used for OLD is `3d43f211130d02774159e287a7cf84986639a1a3`.

The tool reports:

```text
TEMPLATES functions=115 positions=208 left_out=26
ARRIVALS generated=7920 hand=351
```

The `--sources` table on NEW is:

```text
SOURCE floating-overflow/operator formula=1E300*1E10 calc=#NUM! sheet=#NUM!
SOURCE large-double/inline-product formula=3037000500*3037000500 calc=9.22337203700025E+18 sheet=9.22337203700025e+18
SOURCE nonfinite/dispatcher-function formula=POWER(10,400) calc=#NUM! sheet=#NUM!
SOURCE nan formula=POWER(-1,0.5) calc=#NUM! sheet=#NUM!
SOURCE na formula=NA() calc=#N/A sheet=#N/A
SOURCE division-zero formula=1/0 calc=#DIV/0! sheet=#DIV/0!
SOURCE text formula="not a number" calc=not a number sheet=not a number
SOURCE floating-overflow/power formula=0.5^-2000 calc=#NUM! sheet=#NUM!
SOURCE floating-overflow/sum formula=SUM(1E308,1E308) calc=#NUM! sheet=#NUM!
SOURCE typed-int64/product formula=B10*B10 calc=9.22337203700025E+18 sheet=9.22337203700025e+18
SOURCE typed-int64/sum formula=B11+B11 calc=1.84467440737096E+19 sheet=1.8446744073709552e+19
SOURCE typed-int64/difference formula=B12-B11 calc=-1.84467440737096E+19 sheet=-1.8446744073709552e+19
SOURCES kinds=12
```

The NEW quick class run before the fourth XLOOKUP position was found was `SET class examined=14904 match=10020 differ=4884 before=0 net=234 crash=0`, tool wall 28.2 s and shell wall 29.178 s. Because the final population has 72 additional class cells, this is explicitly not the final class line.

The final OLD derivation was started at 16:07 UTC, before minute 25, using the final formulas and the 10-second per-cell limit. It was stopped after 23 minutes because sequential slow cells meant it could not complete within the task's 50-minute delivery limit. `before.json` therefore remains the predecessor's byte-for-byte file and is not claimed as a baseline for this population. **NOT-REACHED — Thu Nov 19 16:31:04 UTC 2026:** the final `BEFORE` line and OLD wall time. **NOT-REACHED — Thu Nov 19 16:31:04 UTC 2026:** every final `SET` line, the final `NUMBER-BAR` line, and NEW full-run wall time, because the tool correctly refuses the predecessor `before.json` whose inputs and keys describe the old population.

Consequently no final movement in `examined` or `differ` is asserted. Structurally, `examined` must increase from the recorded predecessor line `NUMBER-BAR examined=10248 differ=3115 before=1611 net=80 crash=3 rule_examined=2 rule_differ=0`: the final class generator alone has 72 more cells than the measured quick class run, and the new generated-arrival set has 7,920 cells. The corresponding `differ` movement is deliberately not inferred without Calc's completed run.
