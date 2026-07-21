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
order=["A3", "A4", "B1", "B2", "C1"]
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
