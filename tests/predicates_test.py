#!/usr/bin/env python3
"""Information/type-predicate model oracle (#8).

Most predicates are checked against LibreOffice in diff_vs_calc.py (numeric: N,
TYPE, CELL row/col/contents) and diff_vs_calc_str.py (boolean IS*/ISEVEN/ISODD
and text T/CELL type). This file pins the handful LibreOffice can't cleanly
oracle:

  - TYPE of a logical: eigen returns 4 (the Excel spec — a comparison result is
    a logical), whereas LibreOffice reports a comparison result as a number.
  - CELL("address", ref): eigen returns Excel-style "$A$1"; LibreOffice prefixes
    the sheet name ("$Sheet1.$A$1"), so a byte-diff would spuriously fail.
  - direct cell-kind introspection (blank vs 0, an errored ref) where the value
    alone is ambiguous.

Deterministic expected values; pure Python, no LibreOffice.
"""
import os, subprocess, sys, tempfile, shutil

EIGS = os.environ.get("EIGENSCRIPT", "eigenscript")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# addr -> raw content; A1 number, A2 text, A3 a boolean formula, A4 an error,
# A5 the literal 0, A6 left blank.
GRID = {
    "A1": "42", "A2": "hello", "A3": "=1>0", "A4": "=1/0", "A5": "0",
    "B1": "=TYPE(A3)",              # 4   (logical — Excel; LibreOffice would say 1)
    "B2": '=CELL("address",A1)',   # $A$1 (Excel-style; LibreOffice adds the sheet)
    "B3": "=ISBLANK(A6)",          # TRUE  (truly empty)
    "B4": "=ISBLANK(A5)",          # FALSE (0 is not blank)
    "B5": "=ISNUMBER(A6)",         # FALSE (a blank ref is not a number)
    "B6": "=ISERROR(A4)",          # TRUE
    "B7": "=ISNA(A4)",             # FALSE (#DIV/0! is not #N/A)
    "B8": "=N(A6)",                # 0     (blank -> 0)
    "B9": '=CELL("type",A6)',      # b
    "B10": '=CELL("type",A2)',     # l
    "B11": '=CELL("type",A1)',     # v
}
EXPECT = {
    "B1": "4", "B2": "$A$1", "B3": "TRUE", "B4": "FALSE", "B5": "FALSE",
    "B6": "TRUE", "B7": "FALSE", "B8": "0", "B9": "b", "B10": "l", "B11": "v",
}


def eigs_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def main():
    tmp = tempfile.mkdtemp()
    try:
        md = os.path.join(tmp, "eigs_modules", "sheet"); os.makedirs(md)
        shutil.copy(os.path.join(REPO, "sheet.eigs"), os.path.join(md, "sheet.eigs"))
        shutil.copy(os.path.join(REPO, "eigs.json"), os.path.join(md, "eigs.json"))
        sets = "\n".join("sheet.set_cell of [s, %s, %s]" % (eigs_str(a), eigs_str(r))
                         for a, r in GRID.items())
        prints = "\n".join('print of (%s + "\\t" + (sheet.display of [s, %s]))' %
                           (eigs_str(a), eigs_str(a)) for a in EXPECT)
        prog = ("import sheet\ns is sheet.new_sheet of null\n" + sets +
                "\nsheet.recalc of s\n" + prints + "\n")
        app = os.path.join(tmp, "app.eigs"); open(app, "w").write(prog)
        r = subprocess.run([EIGS, app], cwd=tmp, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            print("FAIL: eigenscript errored\n" + r.stdout + r.stderr); sys.exit(1)
        got = {}
        for line in r.stdout.splitlines():
            if "\t" in line:
                a, v = line.split("\t", 1); got[a] = v
        failures = 0
        for a in sorted(EXPECT):
            if got.get(a) != EXPECT[a]:
                failures += 1
                print("FAIL %-4s got=%r expected=%r  (%s)" % (a, got.get(a), EXPECT[a], GRID[a]))
            else:
                print("PASS %-4s = %r  (%s)" % (a, got[a], GRID[a]))
        if failures:
            print("\n%d predicate divergence(s)" % failures); sys.exit(1)
        print("\ninformation/type predicates: model-oracle cases match")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
