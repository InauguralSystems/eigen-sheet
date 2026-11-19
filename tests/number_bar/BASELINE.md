# Number-boundary bar baseline for #104

This is measured output, not an expected-value source. LibreOffice Calc decides every expected answer.

## The rule

Calc is given every judged cell with the number format `0.00000000000000E+00` (fifteen significant digits, scientific) and converts the sheet to CSV with "save cell contents as shown", so C, Calc's text for a cell, is a number in one spelling whatever Calc would have auto-formatted (a time, a date, a percent, a logical). The same sheet without the format is converted in the same call and read only for the shape of a result whose C has that spelling: `TRUE` or `FALSE` there is a logical; the same text there is a text that only looks like a number. A sentinel text on every row must come back; a missing Calc row is the tool's error, never an expectation of blank. For one cell, with C and this spreadsheet's VALUE (`sheet.get`, a logical read as its number) and DISPLAY (`sheet.display`):

- **C is a number.** The cell matches when the VALUE is a number that agrees with C to within one unit in the fifteenth significant digit of the larger of the two in size (both zero agree), and the DISPLAY reads as a decimal number that agrees with C by the same rule and, when the VALUE is whole and below 1e15 in size, is plain digits with an optional minus sign (no `.0` ending, no exponent). When Calc's result is a logical, the VALUE must be a logical of that value and the DISPLAY `TRUE` or `FALSE` as Calc's is. Anything else differs: an error, a text, `#ERROR`, a crash.
- **C is an error** (it starts with `#`, or is `Err:<digits>`). The cell matches when this spreadsheet's cell holds an error value other than `#ERROR` (its marker that the evaluation itself failed), and, where C is one of Excel's seven names (`#DIV/0!`, `#N/A`, `#NAME?`, `#NULL!`, `#NUM!`, `#REF!`, `#VALUE!`) or another `#` name, the same name; where C is `Err:<digits>`, any of the seven.
- **C is anything else** (a text result, an empty result): the DISPLAY equals C exactly, and the cell holds no error.

A cell the per-cell net in recalc caught (`sheet.net_caught`) counts as differing whatever its text. No other tolerance exists in the tool.

`differ` counts every cell that does not match: no cell is set apart. `before` subtracts nothing: of the formula cells that differ now, it counts those whose answer on this repository's `main` with the OLD runtime was the same (the same number by the rule's agreement, the same error name, the same text, or the same CRASH or TIMEOUT). `before.json` holds that run's answers keyed by set, formula text and the set's input cells, is written whole by `--write-before`, and a key no present cell has is the tool's error. The api set has no `before`.

Exit 0 only when `differ`, `net`, `crash` and `rule_differ` are all 0 and every set ran; 1 when any is not; 2 for the tool's own errors.

## The api set

Each program under `api/` prints, through `api/bar_api.eigs`, every cell's raw content and the defined names at each stage, and its judged answers; `api/expectations.json` lists 49 items:

- 36 `calc=cell`: Calc evaluates the same cell of the same sheet (named ranges 5, sort and fill 10, goal seek's sheet before and after 4, CSV in 8, save and load 6, canonical formulas 3). The CSV stage of `sc-6` starts from Calc's own read of `big.csv` (formulas evaluated) and adds the program's `D1` and `D2`; the `loaded` stage of `sc-7` starts from Calc's read of the CSV Calc wrote for the `saved` stage.
- 8 Calc formulas over the stage's cells: the pivot's SUM rows (2, `=SUM(L2:L3)`), the pivot's AVERAGE rows (3, `=AVERAGE(...)` of each key's source cells and of all), the status bar's Sum, Average and Count (3, `=SUM(A1:A2)`, `=AVERAGE(A1:A2)`, `=COUNT(A1:A2)`).
- 3 `calc=csv-out`: each field of the CSV this spreadsheet wrote, against Calc's value for that cell of the range.
- 2 `reference=rule`, counted apart: goal seek of `A1=B1*B1` to `1E20` by `B1` has the root `1E10` (`goal:x`, the value goal seek returns, and `after:B1`, the root it leaves in the cell). No Calc conversion answers a goal seek.

A program that aborts counts every one of its items as differing and adds one to `crash`.

## The count

NEW is the binary behind `/home/jon/src/wt/briefs/local/rt/eigenscript-new`: `/home/jon/src/wt/es-2407/src/eigenscript`, file time 2026-11-18 16:42 -06:00, in a checkout whose HEAD is `d3b483630dc0d55c837c8ac165fd644adcd2ebca` (`phase2-consumers-1-5-gd3b48363`; the tag `phase2-consumers-1` is `b9881574b20503c5cfbdb6d80a5e6008e7501e15`). The checkout carries commits that touch `src/` after the file time, so this run does not pin the binary's source commit. OLD is tag `v0.48.0`, commit `546848c0a7123ea7066923ebadb06f0af29af953`. LibreOffice 24.2.

`before.json` was written from this repository's `main` at `3d43f211130d02774159e287a7cf84986639a1a3` (a plain tree) on OLD: `BEFORE written=10201 ... wall=2733.4s` (45.6 minutes; 2733.90 s shell wall). 31 cells do not finish on OLD, all `REPT` with an enormous count (such as `REPT("a",D1)` with `D1` 9223372036854775807, or `0.5^-2000`): each is run alone and recorded TIMEOUT after 60 s, which is 31 of the 45.6 minutes.

The full run on NEW, on this branch at `74dbfad`, took 152.8 s of tool wall time (153.12 s shell wall), exit 1:

```text
DISPATCHER names=115 rule=One Calc-valid call per dispatcher function. arguments labels every position; each number position is expanded to one marked template by the tool. Calc signatures decide membership.
TEMPLATES functions=115 positions=149
SET class examined=8940 match=6313 differ=2627 before=1337 net=60 crash=0
SET wrappers examined=630 match=368 differ=262 before=114 net=0 crash=0
SET number-text examined=280 match=159 differ=121 before=111 net=0 crash=0
SET c-sumif examined=7 match=7 differ=0 before=0 net=0 crash=0
SET c1 examined=12 match=12 differ=0 before=0 net=0 crash=0
SET c10 examined=22 match=17 differ=5 before=5 net=0 crash=0
SET c20 examined=114 match=66 differ=48 before=28 net=17 crash=0
SET c22 examined=56 match=48 differ=8 before=8 net=0 crash=0
SET c23 examined=19 match=10 differ=9 before=0 net=0 crash=0
SET c24 examined=16 match=11 differ=5 before=1 net=0 crash=0
SET c25 examined=3 match=1 differ=2 before=0 net=0 crash=0
SET c4 examined=46 match=42 differ=4 before=2 net=0 crash=0
SET c5 examined=14 match=13 differ=1 before=1 net=0 crash=0
SET c6 examined=18 match=15 differ=3 before=3 net=0 crash=0
SET c7 examined=12 match=9 differ=3 before=1 net=2 crash=0
SET c8 examined=6 match=5 differ=1 before=0 net=1 crash=0
SET c9 examined=6 match=6 differ=0 before=0 net=0 crash=0
SET api examined=47 match=31 differ=16 crash=3 rule_examined=2 rule_differ=0
NUMBER-BAR examined=10248 differ=3115 before=1611 net=80 crash=3 rule_examined=2 rule_differ=0 wall=152.8s
```

How the count moved: the previous tool's `examined=10201 differ=3775` covered the formula cells only; on the same 10,201 cells this rule gives `differ=3099` because 676 cells the old exact-text rule called different now match (389 where Calc prints `Err:<n>` and this spreadsheet shows one of the seven names, 287 where both give the same number in two spellings, such as `9.22337203700025E+018` against `9.22337203700025e+18`) and no cell moved the other way; the 47 api items Calc now answers add 16 (the two pivots and the status bar abort on NEW: `crash=3`). `c20:A1` (`=SUM(D1:D2)`) and the api item `named:A1` (`=SUM(big)` over the same two cells) both differ: Calc `1.84467440737096E+19`, this spreadsheet `#NUM!`.
