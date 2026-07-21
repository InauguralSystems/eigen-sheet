#!/usr/bin/env bash
# Model oracle for eigen-sheet: replay cell edits, recalc, and byte-diff the
# displayed values against expected output. Self-consistency / regression pin
# for the buffer+recalc logic (external correctness is checked against a real
# spreadsheet in tests/diff_vs_calc.py). Headless, no display.
set -euo pipefail

EIGS="${EIGENSCRIPT:-eigenscript}"
PKG_NAME="$(python3 -c 'import json;print(json.load(open("eigs.json"))["name"])')"
PKG_ROOT="$(pwd)"

TMP="$(mktemp -d)"
trap "rm -rf '$TMP'" EXIT

mkdir -p "$TMP/eigs_modules/$PKG_NAME"
cp -a "$PKG_ROOT/$PKG_NAME.eigs" "$TMP/eigs_modules/$PKG_NAME/"
cp -a "$PKG_ROOT/eigs.json" "$TMP/eigs_modules/$PKG_NAME/"

cat > "$TMP/app.eigs" <<EOF
import $PKG_NAME

s is $PKG_NAME.new_sheet of null
# literals + a dependency chain + a SUM range + parens/precedence
$PKG_NAME.set_cell of [s, "A1", "5"]
$PKG_NAME.set_cell of [s, "A2", "3"]
$PKG_NAME.set_cell of [s, "A3", "=A1+A2"]
$PKG_NAME.set_cell of [s, "A4", "=SUM(A1:A3)"]
$PKG_NAME.set_cell of [s, "B1", "=A4*2-1"]
$PKG_NAME.set_cell of [s, "B2", "=(A1+A2)/2"]
$PKG_NAME.set_cell of [s, "C1", "=B1"]
# a self-referential cycle must NOT loop
$PKG_NAME.set_cell of [s, "D1", "=D2+1"]
$PKG_NAME.set_cell of [s, "D2", "=D1+1"]
$PKG_NAME.recalc of s

define show(a) as:
    print of (a + "=" + ($PKG_NAME.display of [s, a]))
show of "A3"
show of "A4"
show of "B1"
show of "B2"
show of "C1"
show of "D1"
show of "D2"
print of ("order=" + (str of s.order))
# range stats (Sum/Count of numeric cells; text/empty skipped, corners any order)
define stat(label, st) as:
    print of (label + " sum=" + (str of st.sum) + " count=" + (str of st.count))
stat of ["A1:A4", $PKG_NAME.range_stats of [s, 0, 0, 0, 3]]
stat of ["A1:B2", $PKG_NAME.range_stats of [s, 0, 0, 1, 1]]
stat of ["B2:A1", $PKG_NAME.range_stats of [s, 1, 1, 0, 0]]
# copy A3 (=A1+A2) and paste to B3: relative refs shift to =B1+B2 = 31+4
cp1 is $PKG_NAME.copy_block of [s, 0, 2, 0, 2]
$PKG_NAME.paste_block of [s, cp1, 1, 2]
print of ("paste B3=" + ($PKG_NAME.display of [s, "B3"]) + " raw=" + s.cells["B3"])
# functions: AVG / MIN / MAX / IF (with comparison + nesting). A1..A4 = 5,3,8,16
$PKG_NAME.set_cell of [s, "E1", "=AVG(A1:A4)"]
$PKG_NAME.set_cell of [s, "E2", "=MIN(A1:A4)"]
$PKG_NAME.set_cell of [s, "E3", "=MAX(A1:A4)"]
$PKG_NAME.set_cell of [s, "E4", "=IF(A1>A2,MAX(A1:A4),MIN(A1:A4))"]
$PKG_NAME.recalc of s
print of ("E1=" + ($PKG_NAME.display of [s, "E1"]) + " E2=" + ($PKG_NAME.display of [s, "E2"]) + " E3=" + ($PKG_NAME.display of [s, "E3"]) + " E4=" + ($PKG_NAME.display of [s, "E4"]))
# string formulas: literals, & concat (with number coercion), text functions,
# and case-insensitive text comparison. F-cells hold text-literal inputs.
$PKG_NAME.set_cell of [s, "F1", "hi"]
$PKG_NAME.set_cell of [s, "F2", "World"]
$PKG_NAME.set_cell of [s, "S1", "=F1&\" \"&F2"]
$PKG_NAME.set_cell of [s, "S2", "=UPPER(F1)&\"!\""]
$PKG_NAME.set_cell of [s, "S3", "=LEN(F2)"]
$PKG_NAME.set_cell of [s, "S4", "=MID(F2,2,3)"]
$PKG_NAME.set_cell of [s, "S5", "=A1&A2"]
$PKG_NAME.set_cell of [s, "S6", "=IF(F1=\"HI\",\"yes\",\"no\")"]
$PKG_NAME.set_cell of [s, "S7", "=\"a\"+1"]
$PKG_NAME.recalc of s
print of ("S1=" + ($PKG_NAME.display of [s, "S1"]) + " S2=" + ($PKG_NAME.display of [s, "S2"]) + " S3=" + ($PKG_NAME.display of [s, "S3"]) + " S4=" + ($PKG_NAME.display of [s, "S4"]) + " S5=" + ($PKG_NAME.display of [s, "S5"]) + " S6=" + ($PKG_NAME.display of [s, "S6"]) + " S7=" + ($PKG_NAME.display of [s, "S7"]))
# emptied cell reads as 0 in arithmetic (like a spreadsheet), NOT #VALUE!:
# clear A2 (was 3) and A3 (=A1+A2) must fall to 5, not error.
$PKG_NAME.set_cell of [s, "A2", ""]
$PKG_NAME.recalc of s
print of ("cleared A3=" + ($PKG_NAME.display of [s, "A3"]) + " A2=[" + ($PKG_NAME.display of [s, "A2"]) + "]")
$PKG_NAME.set_cell of [s, "A2", "3"]
$PKG_NAME.recalc of s
# absolute/mixed refs: copy =\$A\$1+\$A2+A\$1 from N10 to O11 (delta col+1,row+1).
# Anchored column/row (\$) stay put; only the relative parts shift:
#   \$A\$1 -> \$A\$1 (both anchored), \$A2 -> \$A3 (row rel), A\$1 -> B\$1 (col rel).
# Value = A1 + A3 + B1 = 5 + 8 + 31 = 44.
$PKG_NAME.set_cell of [s, "N10", "=\$A\$1+\$A2+A\$1"]
$PKG_NAME.recalc of s
ab is $PKG_NAME.copy_block of [s, 13, 9, 13, 9]
$PKG_NAME.paste_block of [s, ab, 14, 10]
print of ("abs O11=" + ($PKG_NAME.display of [s, "O11"]) + " raw=" + s.cells["O11"])
# lookup: XLOOKUP is pinned HERE (LibreOffice 24.2 predates it, so the Calc
# oracle can't check it); VLOOKUP/HLOOKUP/MATCH/INDEX/LOOKUP go to the Calc
# oracle. Also no-arg ROW()/COLUMN() (current cell).
$PKG_NAME.set_cell of [s, "L1", "10"]
$PKG_NAME.set_cell of [s, "L2", "20"]
$PKG_NAME.set_cell of [s, "L3", "30"]
$PKG_NAME.set_cell of [s, "M1", "100"]
$PKG_NAME.set_cell of [s, "M2", "200"]
$PKG_NAME.set_cell of [s, "M3", "300"]
$PKG_NAME.set_cell of [s, "K5", "=XLOOKUP(20,L1:L3,M1:M3)"]
$PKG_NAME.set_cell of [s, "K6", "=XLOOKUP(99,L1:L3,M1:M3,-1)"]
$PKG_NAME.set_cell of [s, "K7", "=ROW()"]
$PKG_NAME.set_cell of [s, "K8", "=COLUMN()"]
$PKG_NAME.recalc of s
print of ("xlookup=" + ($PKG_NAME.display of [s, "K5"]) + "," + ($PKG_NAME.display of [s, "K6"]) + " selfrc=" + ($PKG_NAME.display of [s, "K7"]) + "," + ($PKG_NAME.display of [s, "K8"]))
# error propagation: an error in a referenced cell / range flows to dependents
# (was silently 0). P2 references the errored P1; P3 sums a range containing it.
$PKG_NAME.set_cell of [s, "P1", "=1/0"]
$PKG_NAME.set_cell of [s, "P2", "=P1+1"]
$PKG_NAME.set_cell of [s, "P3", "=SUM(P1:P2)"]
$PKG_NAME.recalc of s
print of ("prop P2=" + ($PKG_NAME.display of [s, "P2"]) + " P3=" + ($PKG_NAME.display of [s, "P3"]))
# per-cell number formats: set_format changes DISPLAY (not the stored value).
# Q1 a literal, Q2 a formula result; the format logic itself is Calc-checked
# via TEXT() in the string oracle.
$PKG_NAME.set_cell of [s, "Q1", "1234.5"]
$PKG_NAME.set_format of [s, "Q1", "#,##0.00"]
$PKG_NAME.set_cell of [s, "Q2", "=1/8"]
$PKG_NAME.set_format of [s, "Q2", "0.00%"]
$PKG_NAME.recalc of s
print of ("fmt Q1=" + ($PKG_NAME.display of [s, "Q1"]) + " Q2=" + ($PKG_NAME.display of [s, "Q2"]) + " val=" + (str of ($PKG_NAME.get of [s, "Q1"])))
# user-defined functions: register EigenScript fns callable from formulas — the
# differentiator (Calc needs a separate macro layer). A scalar-arg UDF used in
# arithmetic, and a range-arg UDF receiving the values as a list. A1=5,A2=3,A3=8.
define udf_double(ua) as:
    return ua[0] * 2
define udf_sumsq(ua) as:
    local rr is ua[0]
    local acc is 0
    for ui in range of (len of rr):
        acc is acc + rr[ui] * rr[ui]
    return acc
$PKG_NAME.register_udf of [s, "DOUBLE", udf_double]
$PKG_NAME.register_udf of [s, "SUMSQ", udf_sumsq]
$PKG_NAME.set_cell of [s, "R1", "=DOUBLE(A1)+1"]
$PKG_NAME.set_cell of [s, "R2", "=SUMSQ(A1:A3)"]
$PKG_NAME.recalc of s
print of ("udf R1=" + ($PKG_NAME.display of [s, "R1"]) + " R2=" + ($PKG_NAME.display of [s, "R2"]))
# structural: a formula using EVERY token type — including a string literal and
# the & operator — copied+pasted in place (delta 0) must reconstruct
# byte-identically, guarding _shift_formula against any dropped-token class.
$PKG_NAME.set_cell of [s, "Y1", "=IF(A1&\"x\"=\"5x\",SUM(A1:A3)+1,MIN(A1:A2)*2)"]
$PKG_NAME.recalc of s
rt is $PKG_NAME.copy_block of [s, 24, 0, 24, 0]
$PKG_NAME.paste_block of [s, rt, 24, 0]
print of ("roundtrip=" + s.cells["Y1"])
# error channel: unknown function, div-by-zero, scientific-notation garbage,
# trailing operator, and an aggregate over a gap (empty cell skipped)
$PKG_NAME.set_cell of [s, "X1", "=FOO(A1:A2)"]
$PKG_NAME.set_cell of [s, "X2", "=A1/0"]
$PKG_NAME.set_cell of [s, "X3", "=1E5"]
$PKG_NAME.set_cell of [s, "X4", "=A1+"]
$PKG_NAME.set_cell of [s, "G1", "10"]
$PKG_NAME.set_cell of [s, "G3", "20"]
$PKG_NAME.set_cell of [s, "X5", "=AVERAGE(G1:G3)"]
$PKG_NAME.recalc of s
print of ("errs=" + ($PKG_NAME.display of [s, "X1"]) + "," + ($PKG_NAME.display of [s, "X2"]) + "," + ($PKG_NAME.display of [s, "X3"]) + "," + ($PKG_NAME.display of [s, "X4"]) + " gapavg=" + ($PKG_NAME.display of [s, "X5"]))
EOF

OUT="$("$EIGS" "$TMP/app.eigs" 2>&1)"
EXPECT="$(cat <<'EOF'
A3=8
A4=16
B1=31
B2=4
C1=31
D1=#CYCLE
D2=#CYCLE
order=["A3", "B2", "A4", "B1", "C1"]
A1:A4 sum=32 count=4
A1:B2 sum=43 count=4
B2:A1 sum=43 count=4
paste B3=35 raw==B1+B2
E1=8 E2=3 E3=16 E4=16
S1=hi World S2=HI! S3=5 S4=orl S5=53 S6=yes S7=#VALUE!
cleared A3=5 A2=[]
abs O11=44 raw==$A$1+$A3+B$1
xlookup=200,-1 selfrc=7,11
prop P2=#DIV/0! P3=#DIV/0!
fmt Q1=1,234.50 Q2=12.50% val=1234.5
udf R1=11 R2=98
roundtrip==IF(A1&"x"="5x",SUM(A1:A3)+1,MIN(A1:A2)*2)
errs=#NAME?,#DIV/0!,#ERROR,#ERROR gapavg=15
EOF
)"

if [ "$OUT" != "$EXPECT" ]; then
    echo "FAIL: recalc did not match expectation"
    diff <(printf '%s\n' "$EXPECT") <(printf '%s\n' "$OUT") || true
    exit 1
fi
echo "PASS: recalc model (chain, SUM, precedence, cycle, topo order) byte-exact"

# private helpers (leading _) must not leak to importers
cat > "$TMP/keys.eigs" <<EOF
import $PKG_NAME
ks is keys of $PKG_NAME
for i in range of (len of ks):
    if (starts_with of [ks[i], "_"]) == 1:
        print of ("LEAKED " + ks[i])
print of "ok"
EOF
if "$EIGS" "$TMP/keys.eigs" 2>&1 | grep -q "LEAKED"; then
    echo "FAIL: private helper visible to importers"; exit 1
fi
echo "PASS: private helpers stay out of the import surface"
