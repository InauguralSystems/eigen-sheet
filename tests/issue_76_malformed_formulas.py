#!/usr/bin/env python3
"""Regression coverage for issue #76's malformed/reference/overflow cases."""
import os
import shutil
import subprocess
import sys
import tempfile

EIGS = os.environ.get("EIGENSCRIPT", "eigenscript")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CASES = [
    ("=SUM(A1:)", "#ERROR"),
    ('="abc', "#NAME?"),
    ("=$$A1", "#NAME?"),
    ("=A0", "#NAME?"),
    ("=A1048577", "#NAME?"),
    ("=XFE1", "#NAME?"),
    ("=ZZZZZ1", "#NAME?"),
    ("=2^1024", "#NUM!"),
    ("=10^308*10", "#NUM!"),
    ("=10^308", "1e+308"),
    # Values between 1e308 and the double limit, and =1e309 -> #NUM!, need an
    # EigenScript pin with IEEE doubles (v0.48 clamps floats to +/-1e308):
    # tracked in #84.
    ("=1+", "#ERROR"),
    ("=A1++A2", "3"),
]

INVALID_REFS = ["=XFE1+1", "=A0", "=ZZZZZ1", "=2680922A1"]


def quote(value):
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def main():
    with tempfile.TemporaryDirectory(prefix="eigen-sheet-issue-76-") as tmp:
        module = os.path.join(tmp, "eigs_modules", "sheet")
        os.makedirs(module)
        shutil.copy(os.path.join(ROOT, "sheet.eigs"), module)
        shutil.copy(os.path.join(ROOT, "eigs.json"), module)
        lines = ["import sheet", "s is sheet.new_sheet of null",
                 'sheet.set_cell of [s, "A1", "1"]',
                 'sheet.set_cell of [s, "A2", "2"]']
        for i, (formula, _) in enumerate(CASES, 1):
            lines.append("sheet.set_cell of [s, %s, %s]" % (quote("C%d" % i), quote(formula)))
        lines.append("sheet.recalc of s")
        for i in range(1, len(CASES) + 1):
            lines.append('print of ("C%d\\t" + (sheet.display of [s, "C%d"]))' % (i, i))
        for i, formula in enumerate(INVALID_REFS, 1):
            lines.append("sheet.set_cell of [s, %s, %s]" % (quote("E%d" % i), quote(formula)))
            lines.append("clip is sheet.copy_block of [s, 4, %d, 4, %d]" % (i - 1, i - 1))
            lines.append("sheet.paste_block of [s, clip, 5, %d]" % (i - 1))
            lines.append('print of ("P%d\\t" + s.cells["F%d"] + "\\t" + (sheet.display of [s, "F%d"]))' % (i, i, i))
        app = os.path.join(tmp, "app.eigs")
        with open(app, "w") as f:
            f.write("\n".join(lines) + "\n")
        run = subprocess.run([EIGS, app], cwd=tmp, text=True, capture_output=True, timeout=15)
        if run.returncode:
            print("FAIL: recalc exited %d (malformed input must not abort or hang)" % run.returncode)
            print(run.stdout + run.stderr)
            return 1
        got = dict(line.split("\t", 1) for line in run.stdout.splitlines() if "\t" in line)
        failures = 0
        for i, (formula, expected) in enumerate(CASES, 1):
            actual = got.get("C%d" % i)
            if actual != expected:
                failures += 1
                print("FAIL: %s -> %r, expected %r" % (formula, actual, expected))
            else:
                print("PASS: %s -> %s" % (formula, actual))
        for i, formula in enumerate(INVALID_REFS, 1):
            actual = got.get("P%d" % i, "").split("\t")
            if actual != [formula, "#NAME?"]:
                failures += 1
                print("FAIL: copy/paste %s -> %r, expected unchanged #NAME?" % (formula, actual))
            else:
                print("PASS: copy/paste preserved %s" % formula)
        if failures:
            print("FAIL: %d issue #76 case(s) diverged" % failures)
            return 1
        print("PASS: malformed formulas stopped with errors and recalc completed")
        return 0


if __name__ == "__main__":
    sys.exit(main())
