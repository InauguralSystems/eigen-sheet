#!/usr/bin/env python3
"""Issue #90: exact lookup functions must not treat blank cells as numeric zero."""
import os
import shutil
import subprocess
import tempfile

EIGS = os.environ.get("EIGENSCRIPT", "eigenscript")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Every exact-match caller of _match, derived from sheet.eigs. LOOKUP is excluded:
# it calls only the approximate (match type 1) branch and issue #70 covers it.
CASES = [
    ("MATCH(0,A1:A3,0)", "#N/A"),
    ("VLOOKUP(0,A1:B3,2,0)", "#N/A"),
    ("HLOOKUP(0,D1:F2,2,0)", "#N/A"),
    ("XLOOKUP(0,A1:A3,B1:B3)", "#N/A"),
    # Blank positions precede real numeric zero positions: zero must still match.
    ("MATCH(0,A1:A4,0)", "4"),
    ("VLOOKUP(0,A1:B4,2,0)", "44"),
    ("HLOOKUP(0,D1:G2,2,0)", "44"),
    ("XLOOKUP(0,A1:A4,B1:B4)", "44"),
    # Measured with LibreOffice Calc: empty text is distinct from a blank and
    # matches the cell containing =\"\" at position 2.
    ('MATCH("",J1:J3,0)', "2"),
    ('VLOOKUP("",J1:K3,2,0)', "22"),
    ('HLOOKUP("",M1:O2,2,0)', "22"),
    ('XLOOKUP("",J1:J3,K1:K3)', "22"),
]

MALFORMED = [
    "MATCH(0,A1:A3,)",
    "VLOOKUP(0,A1:B3,2,)",
    "HLOOKUP(0,D1:F2,2,)",
    "XLOOKUP(0,A1:A3,B1:B3,)",
]


def quote(value):
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def run(source, tmp):
    app = os.path.join(tmp, "issue_90.eigs")
    with open(app, "w", encoding="utf-8") as stream:
        stream.write(source)
    return subprocess.run([EIGS, app], cwd=tmp, capture_output=True,
                          text=True, timeout=20)


def main():
    failures = 0
    with tempfile.TemporaryDirectory(prefix="eigen-sheet-issue-90-") as tmp:
        module = os.path.join(tmp, "eigs_modules", "sheet")
        os.makedirs(module)
        shutil.copy(os.path.join(ROOT, "sheet.eigs"), module)
        shutil.copy(os.path.join(ROOT, "eigs.json"), module)
        lines = ["import sheet", "s is sheet.new_sheet of null"]
        values = {
            "A4": "0", "B1": "11", "B2": "22", "B3": "33", "B4": "44",
            "G1": "0", "D2": "11", "E2": "22", "F2": "33", "G2": "44",
            "J2": '=\"\"', "K1": "11", "K2": "22", "K3": "33",
            "N1": '=\"\"', "M2": "11", "N2": "22", "O2": "33",
        }
        for addr, value in values.items():
            lines.append("sheet.set_cell of [s, %s, %s]" % (quote(addr), quote(value)))
        for row, (formula, _) in enumerate(CASES, 1):
            lines.append("sheet.set_cell of [s, %s, %s]" %
                         (quote("Q%d" % row), quote("=" + formula)))
        lines.append("sheet.recalc of s")
        for row in range(1, len(CASES) + 1):
            lines.append("print of (sheet.display of [s, %s])" % quote("Q%d" % row))
        result = run("\n".join(lines) + "\n", tmp)
        actual = result.stdout.splitlines()
        for index, (formula, expected) in enumerate(CASES):
            got = actual[index] if index < len(actual) else "<no output>"
            if result.returncode == 0 and got == expected:
                print("PASS: =%s -> %s" % (formula, got))
            else:
                print("FAIL: =%s -> %s (Calc: %s)" % (formula, got, expected))
                failures += 1

        # Run each malformed exact lookup separately under a hard timeout. This
        # exercises every relevant parser route and proves it makes progress or errors.
        for formula in MALFORMED:
            source = "\n".join(["import sheet", "s is sheet.new_sheet of null",
                'sheet.set_cell of [s, "A1", "1"]',
                'sheet.set_cell of [s, "B1", %s]' % quote("=" + formula),
                "sheet.recalc of s", 'print of (sheet.display of [s, "B1"])', ""])
            try:
                malformed = run(source, tmp)
            except subprocess.TimeoutExpired:
                print("FAIL: =%s hung recalc" % formula)
                failures += 1
                continue
            got = malformed.stdout.splitlines()[-1] if malformed.stdout.splitlines() else ""
            if malformed.returncode == 0 and got.startswith("#"):
                print("PASS: =%s stopped with %s" % (formula, got))
            else:
                print("FAIL: =%s did not stop with an error (rc=%d, output=%r)" %
                      (formula, malformed.returncode, got))
                failures += 1
    if failures:
        print("FAIL: %d issue #90 regression(s)" % failures)
        return 1
    print("PASS: all issue #90 regressions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
