#!/usr/bin/env python3
"""Pivot differential oracle: eigen-sheet's pivot vs a Python groupby reference.

A pivot is a group-by plus an aggregate — deterministic, with a canonical
reference in plain Python. So we don't assert the table; Python does. We build a
source range, run pivot for several aggregations, read the result back with
to_csv, and compare against Python's own grouping/aggregation (keys sorted
numbers-before-text, a Total row). Pure Python + the plain eigenscript build.
"""
import csv, io, math, os, subprocess, sys, tempfile, shutil

EIGS = os.environ.get("EIGENSCRIPT", "eigenscript")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# source: header row + data rows (chosen so every aggregate is an integer)
SOURCE = [
    ["region", "sales"],
    ["north", "10"], ["south", "30"], ["north", "20"],
    ["west", "40"],  ["south", "50"], ["north", "30"],
]
CONFIGS = ["SUM", "COUNT", "AVERAGE", "MAX", "MIN"]
ROW_COL, DATA_COL = 0, 1
TC, TR = 3, 0   # target top-left (D1)


def col_letter(c):
    s = ""; c += 1
    while c > 0:
        c, r = divmod(c - 1, 26); s = chr(65 + r) + s
    return s


def eigs_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


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


def fmt(n):
    if n == int(n):
        return str(int(n))
    return str(math.floor(n * 10000 + 0.5) / 10000)


def num(x):
    try:
        return float(x)
    except ValueError:
        return None


def pivot_ref(aggfn):
    hdr = SOURCE[0]
    groups, allvals = {}, []
    order = []
    for row in SOURCE[1:]:
        k, v = row[ROW_COL], row[DATA_COL]
        if k not in groups:
            groups[k] = []; order.append(k)
        groups[k].append(v); allvals.append(v)

    def agg(vals):
        nums = [num(x) for x in vals if num(x) is not None]
        if aggfn == "COUNT":
            return len(nums)
        if aggfn == "SUM":
            return sum(nums)
        if aggfn == "AVERAGE":
            return sum(nums) / len(nums)
        if aggfn == "MAX":
            return max(nums)
        if aggfn == "MIN":
            return min(nums)

    def sortkey(k):
        n = num(k)
        return (0, n) if n is not None else (1, k.lower())

    out = [[hdr[ROW_COL], aggfn + " of " + hdr[DATA_COL]]]
    for k in sorted(groups, key=sortkey):
        out.append([k, fmt(agg(groups[k]))])
    out.append(["Total", fmt(agg(allvals))])
    return out


def eigs_pivot(aggfn, nrows):
    sets = "\n".join("sheet.set_cell of [s, %s, %s]" %
                     (eigs_str(col_letter(c) + str(r + 1)), eigs_str(SOURCE[r][c]))
                     for r in range(len(SOURCE)) for c in range(len(SOURCE[0])))
    prog = (
        "import sheet\ns is sheet.new_sheet of null\n" + sets + "\nsheet.recalc of s\n"
        "sheet.pivot of [s, 0, 0, %d, %d, %d, %d, %s, %d, %d]\n" %
        (len(SOURCE[0]) - 1, len(SOURCE) - 1, ROW_COL, DATA_COL, eigs_str(aggfn), TC, TR) +
        'print of "<<<P"\nprint of (sheet.to_csv of [s, %d, %d, %d, %d])\nprint of ">>>P"\n' %
        (TC, TR, TC + 1, TR + nrows - 1))
    out = run_eigs(prog)
    body = out[out.index("<<<P\n") + 5: out.index(">>>P")]
    if body.endswith("\n"):
        body = body[:-1]
    return list(csv.reader(io.StringIO(body)))


def main():
    failures = 0
    for aggfn in CONFIGS:
        ref = pivot_ref(aggfn)
        mine = eigs_pivot(aggfn, len(ref))
        if mine != ref:
            failures += 1
            print("FAIL %-8s\n  eigen : %r\n  python: %r" % (aggfn, mine, ref))
        else:
            print("PASS %-8s -> %s" % (aggfn, [r[1] for r in ref[1:]]))
    if failures:
        print("\n%d pivot divergence(s) from Python groupby" % failures)
        sys.exit(1)
    print("\neigen-sheet pivot matches the Python groupby reference")


if __name__ == "__main__":
    main()
