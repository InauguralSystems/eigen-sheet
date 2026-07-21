#!/usr/bin/env python3
"""Filter differential oracle: eigen-sheet's filter_rows vs a Python reference.

Filtering is deterministic predicate matching. We build a table, run filter_rows
for several criteria sets, and compare the matching data-row indices against a
Python reimplementation of the same rules: numeric-vs-numeric numeric compare,
text-vs-text case-insensitive, numbers-sort-before-text on a mix (matching
_compare), and case-insensitive "contains". Criteria are ANDed. Pure Python.
"""
import json, os, subprocess, sys, tempfile, shutil

EIGS = os.environ.get("EIGENSCRIPT", "eigenscript")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SOURCE = [
    ["region", "sales", "rep"],
    ["north", "10", "amy"],
    ["south", "50", "bob"],
    ["North", "30", "cara"],
    ["west",  "50", "dan"],
    ["east",  "20", "amy"],
]
# each config: list of {col, op, val}
FILTERS = [
    [{"col": 1, "op": ">=", "val": 30}],
    [{"col": 0, "op": "=", "val": "north"}],
    [{"col": 0, "op": "contains", "val": "th"}, {"col": 1, "op": ">", "val": 20}],
    [{"col": 1, "op": "<>", "val": 50}],
    [{"col": 2, "op": "=", "val": "AMY"}],
    [{"col": 1, "op": ">", "val": 100}],
]
C0, R0, C1, R1 = 0, 0, len(SOURCE[0]) - 1, len(SOURCE) - 1


def eigs_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def col_letter(c):
    s = ""; c += 1
    while c > 0:
        c, r = divmod(c - 1, 26); s = chr(65 + r) + s
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


def eigs_crit(c):
    v = c["val"]
    vs = str(v) if isinstance(v, (int, float)) else eigs_str(v)
    return '{"col": %d, "op": %s, "val": %s}' % (c["col"], eigs_str(c["op"]), vs)


def num(x):
    try:
        return float(x)
    except (ValueError, TypeError):
        return None


def cmp_sign(l, r):
    ln, rn = num(l), num(r)
    if ln is not None and rn is not None:
        return (ln > rn) - (ln < rn)
    if ln is None and rn is None:
        a, b = str(l).lower(), str(r).lower()
        return (a > b) - (a < b)
    return -1 if ln is not None else 1


def match(cellval, op, val):
    if op == "contains":
        return str(val).lower() in str(cellval).lower()
    c = cmp_sign(cellval, val)
    return {">": c > 0, "<": c < 0, ">=": c >= 0, "<=": c <= 0, "=": c == 0, "<>": c != 0}[op]


def py_filter(criteria):
    out = []
    for i, row in enumerate(SOURCE[1:]):
        if all(match(row[c["col"]], c["op"], c["val"]) for c in criteria):
            out.append(i)
    return out


def main():
    sets = "\n".join("sheet.set_cell of [s, %s, %s]" %
                     (eigs_str(col_letter(c) + str(r + 1)), eigs_str(SOURCE[r][c]))
                     for r in range(len(SOURCE)) for c in range(len(SOURCE[0])))
    calls = "\n".join(
        'print of (str of (sheet.filter_rows of [s, %d, %d, %d, %d, [%s]]))' %
        (C0, R0, C1, R1, ", ".join(eigs_crit(c) for c in f))
        for f in FILTERS)
    prog = "import sheet\ns is sheet.new_sheet of null\n" + sets + "\nsheet.recalc of s\n" + calls + "\n"
    out = [l for l in run_eigs(prog).splitlines() if l.strip().startswith("[")]

    failures = 0
    for i, f in enumerate(FILTERS):
        mine = json.loads(out[i])
        ref = py_filter(f)
        if mine != ref:
            failures += 1
            print("FAIL %-40s eigen=%r python=%r" % (json.dumps(f), mine, ref))
        else:
            print("PASS %-40s -> %s" % (json.dumps(f), ref))
    if failures:
        print("\n%d filter divergence(s) from Python" % failures); sys.exit(1)
    print("\neigen-sheet filter matches the Python reference")


if __name__ == "__main__":
    main()
