# Evidence: the fix round of eigen-sheet#104's bar (sheet-bar4)

Worktree `/home/jon/src/wt/fleet1119/eigen-sheet`, branch `bar-104`, from `ca4fcfe`. Work began `Thu Nov 19 02:35:34 PM UTC 2026`. Runtimes: NEW `/home/jon/src/wt/briefs/local/rt/eigenscript-new`, OLD `/home/jon/src/wt/briefs/local/rt/eigenscript-old` (provenance in `tests/number_bar/BASELINE.md`). `main` as a plain tree: `/home/jon/src/wt/fleet1119/sheet-main` from `git archive origin/main` (`3d43f211`). Every LibreOffice call is `--headless` with its own profile; Calc ran with `DISPLAY=:99` (Xvfb).

## Step 1: what Calc prints under the explicit format (14:37 UTC)

A probe workbook of 20 cells (`=1=1`, `=ISERROR(1/0)`, `=TIME(8,0,0)`, `=DATE(2020,1,1)`, `=TEXT(1,"0%")`, `=0.1+0.2`, `="abc"`, `=1/0`, `=SQRT(-1)`, `=5`, an overflowing sum, `=""`, `=1E-320`, `=-0`, `=1E15+0.5`, `=NA()`, `=FALSE()`, `=0.5^-2000`, `=SUM(1E308,1E308)`, `=NOW()*0+50%`), each with `number_format = "0.00000000000000E+00"`.

- Converted with the bare `--convert-to csv` (the previous tool's call), the format is not applied: `=1=1` gives `1`, `=TIME(8,0,0)` gives `0.333333333333333`, the sum gives `1.84467440737096E+019`.
- Converted with `csv:Text - txt - csv (StarCalc):44,34,76,1,,0,false,true,true` ("save cell contents as shown"), every numeric result has one spelling: `=1=1` `1.00000000000000E+00`, `=TIME(8,0,0)` `3.33333333333333E-01`, `=DATE(2020,1,1)` `4.38310000000000E+04`, `=0.1+0.2` `3.00000000000000E-01`, `=5` `5.00000000000000E+00`, the sum `1.84467440737096E+19`, `=-0` `-0.00000000000000E+00`, `=1E15+0.5` `1.00000000000000E+15`, `=FALSE()` `0.00000000000000E+00`, 50% `5.00000000000000E-01`; text stays text (`=TEXT(1,"0%")` `100%`, `="abc"` `abc`, `=""` empty), errors stay errors (`#DIV/0!`, `Err:502`, `#N/A`, `#NUM!`).
- The same workbook without the format, same options: `=1=1` `TRUE`, `=FALSE()` `FALSE`, `=TIME(8,0,0)` `08:00:00 AM`. The tool reads this copy only for TRUE/FALSE (a logical) and for a text that equals the formatted text (a text result in the number spelling, found in the api run: `=A1&""` of a big number is the text `9.22337203685478E+018` in Calc).

## Steps 1, 2, 5 (commit `85dc3f0`)

`before.json` (Step 2), written by the tool's own command from `main` on OLD:

```text
$ python3 tests/number_bar.py --write-before --old-tree /home/jon/src/wt/fleet1119/sheet-main --old-runtime /home/jon/src/wt/briefs/local/rt/eigenscript-old
Thu Nov 19 02:42:07 PM UTC 2026
BEFORE written=10201 path=/home/jon/src/wt/fleet1119/eigen-sheet/tests/number_bar/before.json wall=2733.4s
SHELLWALL 2733.90 s
DONE rc=0
Thu Nov 19 03:27:40 PM UTC 2026
```

Kinds in it: N 3337, E 2909, L 2574, CRASH 925, S 425, TIMEOUT 31 (all 31 are `REPT` with an enormous count).

Quick run with the Step 1/2/5 tool (`85dc3f0`'s `tests/number_bar.py`, run on the tree with the Step 3 edit present but not yet committed, since that tool refuses a tree without `net_caught`), 15:27:59 UTC:

```text
$ python3 tests/number_bar.py --set wrappers --runtime .../eigenscript-new
SET wrappers examined=630 match=368 differ=262 before=114 net=0 crash=0
NUMBER-BAR examined=630 differ=262 before=114 net=0 crash=0 rule_examined=0 rule_differ=0 wall=23.9s
rc=1
```

Exit 2 for the tool's own errors (15:49 UTC, final tool):

```text
$ python3 tests/number_bar.py --set c9 --before <before.json plus the key 'c9\t=NOT_A_CELL()'> ...
NUMBER-BAR TOOL-ERROR before.json has 1 keys no present cell has, first 'c9\t=NOT_A_CELL()'
rc=2
$ python3 tests/number_bar.py --tree <sheet.eigs as at ca4fcfe> --set c9 ...
NUMBER-BAR TOOL-ERROR the tree has no `define net_caught(sheet)`: the net cannot be counted
rc=2
$ python3 tests/number_bar.py --set c9 ...
NUMBER-BAR examined=6 differ=0 before=0 net=0 crash=0 rule_examined=0 rule_differ=0 wall=8.1s
rc=0
```

## Step 3 (commit `79a660f`): the net is counted

The whole diff of `sheet.eigs`:

```diff
diff --git a/sheet.eigs b/sheet.eigs
index 7901ed8..19d173d 100644
--- a/sheet.eigs
+++ b/sheet.eigs
@@ -2743,6 +2743,7 @@ define recalc(sheet) as:
     sheet.vals is {}
     sheet.err is {}
     sheet.order is []
+    sheet.net is []
     local addrs is keys of sheet.cells
     local formula_toks is {}
     local formula_deps is {}
@@ -2811,6 +2812,7 @@ define recalc(sheet) as:
             # in this program and is raised again, so that a test sees it.
             if (type of eval_error) == "dict" and eval_error.kind == "value":
                 st.err is "#NUM!"
+                append of [sheet.net, addr]
             else:
                 throw of eval_error
         if st.err != "":
@@ -2832,6 +2834,13 @@ define recalc(sheet) as:
             dict_set of [sheet.vals, pending[i], 0]
     return sheet
 
+# The addresses whose evaluation the per-cell net in recalc caught (each shows
+# #NUM!), in evaluation order, since the last recalc began; [] before any.
+define net_caught(sheet) as:
+    if (has_key of [sheet, "net"]):
+        return sheet.net
+    return []
+
 define get(sheet, addr) as:
     local a is _upper of addr
     if (has_key of [sheet.vals, a]):
```

No value or display changes. The tool's own runner (`run_chunks`, net not read) dumped every cell's answer (kind, value, display) of each formula set on NEW, with `sheet.eigs` as at `ca4fcfe` and with the edit (15:29 UTC). The `--out` records of the final tool carry `net` and `verdict`, which the edit changes by design, so the comparison is of the answers:

```text
class: cells 8940, pre3 wall 11.78 s, post3 wall 11.42 s
BYTE-IDENTICAL
92c257fa471b1f67fe187d576f0d33f09d501c6d36cb43b36d6e5ae7b8b790f7  class-pre3.json
92c257fa471b1f67fe187d576f0d33f09d501c6d36cb43b36d6e5ae7b8b790f7  class-post3.json
wrappers identical 630
number-text identical 280
c-sumif identical 7
c1 identical 12
c10 identical 22
c20 identical 114
c22 identical 56
c23 identical 19
c24 identical 16
c25 identical 3
c4 identical 46
c5 identical 14
c6 identical 18
c7 identical 12
c8 identical 6
c9 identical 6
```

Plants on copies of `sheet.eigs`, every formula set run one `--set` at a time with the Step 1/2/5 tool on NEW (15:30 to 15:37 UTC), summed:

```text
clean tree                                          SUM examined=10201 differ=3099 before=1611 net=80 crash=0
net widened to every error kind (`if 1 == 1:`)      SUM examined=10201 differ=3099 before=1611 net=80 crash=0
catch keeps #NUM! but records nothing               SUM examined=10201 differ=3076 before=1609 net=0 crash=0
```

The brief's plant (widen the net) does NOT raise `net` or `differ`: every SET line of the widened copy equals the clean one. On NEW no cell of the population, and none of 17 extra probes (`REPT`, `MID`, `CHAR`, `DATE`, `INDEX`, `ROUND`, `FACT`, `CHOOSE`, `EDATE`, `LARGE` and others with `1E300` arguments), raises anything but the runtime's `value` kind, so a wider net has nothing more to catch (`crash=0` in the clean run says the same). Had such a cell existed, it would differ either way: CRASH without the net, net-caught with it. The second plant shows the count matters: dropping the record takes `net` from 80 to 0 and `differ` from 3099 to 3076 (23 net-caught cells whose `#NUM!` matches Calc's error class).

## Step 6 (commit `0fc705f`, extended in `74dbfad`): the self-test

`python3 tests/number_bar.py --selftest` with the final tool, whole output (no LibreOffice; stand-ins for the runtime and Calc runners, one real api run through a stand-in runtime that exits 1):

```text
PASS: control a 17th-digit difference matches: examined=1 differ=0 before=0 net=0 crash=0 status=0
PASS: control Err:502 matches #NUM!: examined=1 differ=0 before=0 net=0 crash=0 status=0
PASS: control a text in the number spelling matches only as that text: ('examined=1 differ=0 before=0 net=0 crash=0 status=0', 'examined=1 differ=1 before=0 net=0 crash=0 status=1')
PASS: control a logical matches only as a logical: ('examined=1 differ=0 before=0 net=0 crash=0 status=0', 'examined=1 differ=1 before=0 net=0 crash=0 status=1')
PASS: number rule widened: a 13th-digit difference accepted: clean examined=1 differ=1 before=0 net=0 crash=0 status=1; mutant examined=1 differ=0 before=0 net=0 crash=0 status=0
PASS: #ERROR accepted as a match for a Calc error: clean examined=1 differ=1 before=0 net=0 crash=0 status=1; mutant examined=1 differ=0 before=0 net=0 crash=0 status=0
PASS: an Err:502 expectation refused for #NUM!: clean examined=1 differ=0 before=0 net=0 crash=0 status=0; mutant examined=1 differ=1 before=0 net=0 crash=0 status=1
PASS: a different error name accepted where Calc names one: clean examined=1 differ=1 before=0 net=0 crash=0 status=1; mutant examined=1 differ=0 before=0 net=0 crash=0 status=0
PASS: a whole number displayed with .0 accepted: clean examined=1 differ=1 before=0 net=0 crash=0 status=1; mutant examined=1 differ=0 before=0 net=0 crash=0 status=0
PASS: a net-caught cell counted as a match: clean examined=1 differ=1 before=0 net=1 crash=0 status=1; mutant examined=1 differ=0 before=0 net=1 crash=0 status=1
PASS: run_chunks gives every cell of a failed chunk a value: clean examined=2 differ=1 before=0 net=0 crash=1 status=1; mutant examined=2 differ=0 before=0 net=0 crash=0 status=0
PASS: an empty set accepted: clean TOOL-ERROR; mutant examined=0 differ=0 before=0 net=0 crash=0 status=0
PASS: a missing Calc answer read as blank: clean TOOL-ERROR; mutant examined=1 differ=0 before=0 net=0 crash=0 status=0
PASS: a short Calc CSV row read: clean TOOL-ERROR; mutant read
PASS: an aborted api program counted as zero differing lines: clean examined=3 differ=3 crash=1 status=1; mutant examined=0 differ=0 crash=1 status=1
PASS: a before.json key matched by address instead of formula: clean examined=2 differ=2 before=2 net=0 crash=0 status=1; mutant examined=2 differ=2 before=0 net=0 crash=0 status=1
SELFTEST examined=16 of 16 failed=0
rc=0
```

At `0fc705f` the same command printed 14 cases (`SELFTEST examined=14 of 14 failed=0`); `74dbfad` added the api abort plant and the text-shape control. Each plant is one edit of a copy of the tool, its anchor found exactly once above the self-test section; the clean tool must give the stated outcome and the mutant another one; a case that raises is BROKEN and fails the self-test.

## Step 4 (commit `74dbfad`): the api paths against Calc

```text
$ python3 tests/number_bar.py --set api --runtime .../eigenscript-new        (15:40:53 UTC)
SET api examined=47 match=31 differ=16 crash=3 rule_examined=2 rule_differ=0
NUMBER-BAR examined=47 differ=16 before=0 net=0 crash=3 rule_examined=2 rule_differ=0 wall=39.9s
rc=1
$ python3 tests/number_bar.py --set api --runtime .../eigenscript-old        (15:41:44 UTC, same tree)
SET api examined=47 match=42 differ=5 crash=0 rule_examined=2 rule_differ=0
NUMBER-BAR examined=47 differ=5 before=0 net=0 crash=0 rule_examined=2 rule_differ=0 wall=48.9s
rc=1
```

On NEW the pivot (sum), the pivot (average) and the status bar abort (`integer overflow in '+'` in `_aggregate` and `range_stats`): their 8 items differ and `crash=3`. The OLD run is shown only because it reaches those programs, so Calc's answers for them are visible: pivot `O2` and `O3` `1.84467440737096E+19`, average rows `5.00000000000000E+09`, `4.61168601842739E+18`, `3.07445734728493E+18`, status Sum `1.84467440737096E+19`, Average `9.22337203685478E+18`, Count `2.00000000000000E+00`, all from Calc formulas over the source cells in the run.

`c20:A1` and the api item for the same sum agree in verdict (full run records):

```text
{'set': 'c20', 'address': 'A1', 'formula': '=SUM(D1:D2)', 'calc': '1.84467440737096E+19', 'calc_shape': None, 'kind': 'E', 'value': '', 'display': '#NUM!', 'net': True, 'verdict': 'differ', 'before': False}
{'set': 'api', 'program': 'sc-1-named.eigs', 'id': 'named:A1', 'reference': 'calc', 'calc': '1.84467440737096E+19', 'calc_shape': None, 'kind': 'E', 'value': '', 'display': '#NUM!', 'verdict': 'differ'}
```

## The count (15:43:14 to 15:45:47 UTC)

```text
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
Command exited with non-zero status 1
SHELLWALL 153.12 s
```

The previous tool, run again from `git archive ca4fcfe` on NEW at 15:46:27 UTC, printed `NUMBER-BAR examined=10201 differ=3775 known_before=2188 new=1587 net=unknown rule_examined=21 rule_differ=10 wall=94.6s`. Cell by cell against it (same 10,201 cells, same formulas): 6426 match in both, 3099 differ in both, 676 differ before and match now (389 Calc `Err:<n>` against one of the seven names; 270 the same number with Calc's three-digit exponent, `9.22337203700025E+018` against `9.22337203700025e+18`; 17 other spellings of the same number, such as `1E+300` against `1e+300`), and none match before and differ now.

## Findings (cells listed, none removed)

Cells that differ because Calc's TEXT result uses Calc's own number-to-text spelling (a three-digit exponent), which a spreadsheet with Excel's conventions would not print; under the rule a text result is exact text, so each counts:

- `class:A385` `=CONCATENATE(3037000500*3037000500,"x")`: Calc `9.22337203700025E+018x`, this spreadsheet `9.22337203700025e+18x`
- `class:A386` `=IFERROR(CONCATENATE(3037000500*3037000500,"x"),7101)`: Calc `9.22337203700025E+018x`, this spreadsheet `9.22337203700025e+18x`
- `class:I81` `=PROPER(3037000500*3037000500)`: Calc `9.22337203700025E+018`, this spreadsheet `9.22337203700025E+18`
- `class:I82` `=IFERROR(PROPER(3037000500*3037000500),7101)`: Calc `9.22337203700025E+018`, this spreadsheet `9.22337203700025E+18`
- `class:L177` `=TRIM(3037000500*3037000500)`: Calc `9.22337203700025E+018`, this spreadsheet `9.22337203700025e+18`
- `class:L178` `=IFERROR(TRIM(3037000500*3037000500),7101)`: Calc `9.22337203700025E+018`, this spreadsheet `9.22337203700025e+18`
- `class:L303` `=UPPER(3037000500*3037000500)`: Calc `9.22337203700025E+018`, this spreadsheet `9.22337203700025E+18`
- `class:L304` `=IFERROR(UPPER(3037000500*3037000500),7101)`: Calc `9.22337203700025E+018`, this spreadsheet `9.22337203700025E+18`
- `wrappers:A484` `=3037000500*3037000500&"x"`: Calc `9.22337203700025E+018x`, this spreadsheet `9.22337203700025e+18x`
- `wrappers:A485` `=IFERROR(3037000500*3037000500&"x",7)`: Calc `9.22337203700025E+018x`, this spreadsheet `9.22337203700025e+18x`
- `wrappers:A486` `=IFNA(3037000500*3037000500&"x",7)`: Calc `9.22337203700025E+018x`, this spreadsheet `9.22337203700025e+18x`
- `number-text:A72` `=(1E21)&""`: Calc `1E+021`, this spreadsheet `1e+21`
- `number-text:A74` `=LEFT((1E21),30)`: Calc `1E+021`, this spreadsheet `1e+21`
- `number-text:A76` `=MID((1E21),1,30)`: Calc `1E+021`, this spreadsheet `1e+21`
- `number-text:A81` `=CONCATENATE((1E21))`: Calc `1E+021`, this spreadsheet `1e+21`
- `number-text:A86` `=(10^21)&""`: Calc `1E+021`, this spreadsheet `1e+21`
- `number-text:A88` `=LEFT((10^21),30)`: Calc `1E+021`, this spreadsheet `1e+21`
- `number-text:A90` `=MID((10^21),1,30)`: Calc `1E+021`, this spreadsheet `1e+21`
- `number-text:A95` `=CONCATENATE((10^21))`: Calc `1E+021`, this spreadsheet `1e+21`
- `number-text:A170` `=(2^53+1)&""`: Calc `9.00719925474099E+015`, this spreadsheet `9007199254740992`
- `number-text:A172` `=LEFT((2^53+1),30)`: Calc `9.00719925474099E+015`, this spreadsheet `9007199254740992`
- `number-text:A174` `=MID((2^53+1),1,30)`: Calc `9.00719925474099E+015`, this spreadsheet `9007199254740992`
- `number-text:A179` `=CONCATENATE((2^53+1))`: Calc `9.00719925474099E+015`, this spreadsheet `9007199254740992`
- `number-text:A184` `=(9007199254740993)&""`: Calc `9.00719925474099E+015`, this spreadsheet `9007199254740992`
- `number-text:A186` `=LEFT((9007199254740993),30)`: Calc `9.00719925474099E+015`, this spreadsheet `9007199254740992`
- `number-text:A188` `=MID((9007199254740993),1,30)`: Calc `9.00719925474099E+015`, this spreadsheet `9007199254740992`
- `number-text:A193` `=CONCATENATE((9007199254740993))`: Calc `9.00719925474099E+015`, this spreadsheet `9007199254740992`
- `number-text:A198` `=(123456789012345678)&""`: Calc `1.23456789012346E+017`, this spreadsheet `1.2345678901234568e+17`
- `number-text:A200` `=LEFT((123456789012345678),30)`: Calc `1.23456789012346E+017`, this spreadsheet `1.2345678901234568e+17`
- `number-text:A202` `=MID((123456789012345678),1,30)`: Calc `1.23456789012346E+017`, this spreadsheet `1.2345678901234568e+17`
- `number-text:A207` `=CONCATENATE((123456789012345678))`: Calc `1.23456789012346E+017`, this spreadsheet `1.2345678901234568e+17`
- `number-text:A212` `=(123456789012345678*1)&""`: Calc `1.23456789012346E+017`, this spreadsheet `1.2345678901234568e+17`
- `number-text:A214` `=LEFT((123456789012345678*1),30)`: Calc `1.23456789012346E+017`, this spreadsheet `1.2345678901234568e+17`
- `number-text:A216` `=MID((123456789012345678*1),1,30)`: Calc `1.23456789012346E+017`, this spreadsheet `1.2345678901234568e+17`
- `number-text:A221` `=CONCATENATE((123456789012345678*1))`: Calc `1.23456789012346E+017`, this spreadsheet `1.2345678901234568e+17`
- `number-text:A240` `=(2^53)&""`: Calc `9.00719925474099E+015`, this spreadsheet `9007199254740992`
- `number-text:A242` `=LEFT((2^53),30)`: Calc `9.00719925474099E+015`, this spreadsheet `9007199254740992`
- `number-text:A244` `=MID((2^53),1,30)`: Calc `9.00719925474099E+015`, this spreadsheet `9007199254740992`
- `number-text:A249` `=CONCATENATE((2^53))`: Calc `9.00719925474099E+015`, this spreadsheet `9007199254740992`
- `number-text:A254` `=(1E15+0.5)&""`: Calc `1E+015`, this spreadsheet `1000000000000000.5`
- `number-text:A256` `=LEFT((1E15+0.5),30)`: Calc `1E+015`, this spreadsheet `1000000000000000.5`
- `number-text:A258` `=MID((1E15+0.5),1,30)`: Calc `1E+015`, this spreadsheet `1000000000000000.5`
- `number-text:A263` `=CONCATENATE((1E15+0.5))`: Calc `1E+015`, this spreadsheet `1000000000000000.5`
- `c20:A26` `=E1&""`: Calc `9.22337203685478E+018`, this spreadsheet `9.223372036854776e+18`
- `c22:A10` `=B3&""`: Calc `1.23456789012346E+017`, this spreadsheet `1.2345678901234568e+17`
- `c22:A12` `=B4&""`: Calc `9.22337203685478E+018`, this spreadsheet `9.223372036854776e+18`
- `c22:A2` `=B1&""`: Calc `9.00719925474099E+015`, this spreadsheet `9007199254740992`
- `c5:A11` `=SUM(B3:B4)&""`: Calc `3E+300`, this spreadsheet `3e+300`

Other differing kinds in the full run (formula sets, 3099): 1260 Calc logical with `#ERROR` here, 1186 Calc number with `#ERROR` here, 145 Calc number with another error here, 101 Calc error with another error name here, 94 Calc number with another number here (80 values disagree, 14 displays round to `0`, for example `=NPV(3037000500*3037000500,100,200)`: Calc `1.08420217246840E-17`, value `1.0842021724684042e-17`, display `0`), 89 Calc text with another text here, 43 Calc logical with the other logical here, 80 net-caught (any text), 30 Calc text in the number spelling with another text here, 28 Calc error with a number here, 16 Calc error with a text here, 10 Calc text with an error here, 9 Calc text with a number here, 7 Calc number with a text here, 1 Calc text with `#ERROR` here.
