# Number-boundary bar baseline for #104

This is measured output, not an expected-value source. LibreOffice Calc decides every expected answer.

## The rule

Calc is given every formula cell with the number format `0.00000000000000E+00` (fifteen significant digits, scientific) and converts the sheet to CSV with "save cell contents as shown", so C, Calc's text for a cell, is a number in one spelling whatever Calc would have auto-formatted (a time, a date, a percent, a logical). The same sheet without the format is converted in the same call and read only to learn whether Calc's result is a logical (it shows `TRUE` or `FALSE` there). A sentinel text on every row must come back; a missing Calc row is the tool's error, never an expectation of blank. For one cell, with C and this spreadsheet's VALUE (`sheet.get`, a logical read as its number) and DISPLAY (`sheet.display`):

- **C is a number.** The cell matches when the VALUE is a number that agrees with C to within one unit in the fifteenth significant digit of the larger of the two in size (both zero agree), and the DISPLAY reads as a decimal number that agrees with C by the same rule and, when the VALUE is whole and below 1e15 in size, is plain digits with an optional minus sign (no `.0` ending, no exponent). When Calc's unformatted display is `TRUE` or `FALSE`, the result is a logical: the VALUE must then be a logical of that value and the DISPLAY must be `TRUE` or `FALSE` as Calc's is. Anything else differs: an error, a text, `#ERROR`, a crash.
- **C is an error** (it starts with `#`, or is `Err:<digits>`). The cell matches when this spreadsheet's cell holds an error value other than `#ERROR` (its marker that the evaluation itself failed), and, where C is one of Excel's seven names (`#DIV/0!`, `#N/A`, `#NAME?`, `#NULL!`, `#NUM!`, `#REF!`, `#VALUE!`) or another `#` name, the same name; where C is `Err:<digits>`, any of the seven.
- **C is anything else** (a text result, an empty result): the DISPLAY equals C exactly, and the cell holds no error.

A cell the per-cell net in recalc caught counts as differing whatever its text. No other tolerance exists in the tool.

`differ` counts every cell that does not match: no cell is set apart. `before` subtracts nothing: of the cells that differ now, it counts those whose answer on this repository's `main` with the OLD runtime was the same (the same number by the rule's agreement, the same error name, or the same text). `before.json` holds that run's answers keyed by set, formula text and the set's input cells, and is written whole by `--write-before`.

## Counts

The counts below this line were measured by the previous tool (exact display-text equality and a `known_before` set apart by address); they are replaced by the next full run.

```text
NUMBER-BAR examined=10201 differ=3775 known_before=2188 new=1587 net=unknown rule_examined=21 rule_differ=10 wall=116.3s
```
