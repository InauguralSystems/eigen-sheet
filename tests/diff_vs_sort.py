#!/usr/bin/env python3
"""Sort differential oracle: eigen-sheet's sort_range vs Python's sorted().

Sorting is deterministic and has a canonical reference in every standard
library. So we don't assert the order — Python's stable sorted() does. We build
a table, sort it with sort_range, export the result with to_csv, and compare
against sorted(rows) under the same key: numbers sort before text (like Calc's
ascending order), the sort is stable (equal keys keep original order, including
under reverse), and text compares case-insensitively.

Pure Python + the plain eigenscript build; no LibreOffice.
"""
import csv, io, os, subprocess, sys, tempfile, shutil

EIGS = os.environ.get("EIGENSCRIPT", "eigenscript")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# A table with a numeric key column (1) and a text key column (0), plus equal
# keys (two 50s, two "mid"s) to exercise stability, and a mixed-type column (2).
TABLE = [
    ["cara", "30", "9"],
    ["alan", "50", "apple"],
    ["bob",  "10", "2"],
    ["dave", "50", "banana"],
    ["erin", "20", "5"],
]
# (keycol within range, descending) configurations to check
CONFIGS = [(1, 0), (1, 1), (0, 0), (0, 1), (2, 0)]
NROWS, NCOLS = len(TABLE), len(TABLE[0])


def eigs_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def col_letter(c):
    s = ""
    c += 1
    while c > 0:
        c, r = divmod(c - 1, 26)
        s = chr(65 + r) + s
    return s


def run_eigs(prog):
    tmp = tempfile.mkdtemp()
    try:
        md = os.path.join(tmp, "eigs_modules", "sheet"); os.makedirs(md)
        shutil.copy(os.path.join(REPO, "sheet.eigs"), os.path.join(md, "sheet.eigs"))
        shutil.copy(os.path.join(REPO, "eigs.json"), os.path.join(md, "eigs.json"))
        app = os.path.join(tmp, "app.eigs"); open(app, "w").write(prog)
        r = subprocess.run([EIGS, app], cwd=tmp, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise RuntimeError(r.stdout + r.stderr)
        return r.stdout
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def eigs_sort(keycol, desc):
    sets = "\n".join(
        "sheet.set_cell of [s, %s, %s]" % (eigs_str(col_letter(c) + str(r + 1)), eigs_str(TABLE[r][c]))
        for r in range(NROWS) for c in range(NCOLS))
    prog = (
        "import sheet\ns is sheet.new_sheet of null\n" + sets + "\nsheet.recalc of s\n"
        "sheet.sort_range of [s, 0, 0, %d, %d, %d, %d]\n" % (NCOLS - 1, NROWS - 1, keycol, desc) +
        'print of "<<<S"\nprint of (sheet.to_csv of [s, 0, 0, %d, %d])\nprint of ">>>S"\n' % (NCOLS - 1, NROWS - 1))
    out = run_eigs(prog)
    body = out[out.index("<<<S\n") + 5: out.index(">>>S")]
    if body.endswith("\n"):
        body = body[:-1]
    return list(csv.reader(io.StringIO(body)))


def sortkey(cell):
    # numbers before text; text case-insensitive
    try:
        return (0, float(cell))
    except ValueError:
        return (1, cell.lower())


def py_sort(keycol, desc):
    return sorted(TABLE, key=lambda row: sortkey(row[keycol]), reverse=bool(desc))


def main():
    failures = 0
    for keycol, desc in CONFIGS:
        mine = eigs_sort(keycol, desc)
        ref = py_sort(keycol, desc)
        tag = "col %d %s" % (keycol, "desc" if desc else "asc")
        if mine != ref:
            failures += 1
            print("FAIL %-12s eigen=%r  python=%r" % (tag, mine, ref))
        else:
            print("PASS %-12s -> %s" % (tag, [r[keycol] for r in ref]))
    if failures:
        print("\n%d sort divergence(s) from Python sorted()" % failures)
        sys.exit(1)
    print("\neigen-sheet sort matches Python's stable sorted() on every config")


if __name__ == "__main__":
    main()
