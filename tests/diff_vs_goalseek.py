#!/usr/bin/env python3
"""Goal Seek differential oracle: eigen-sheet's secant solver vs Python bisection.

Goal Seek finds the input that drives a formula to a target — root-finding.
eigen-sheet uses the secant method; here we solve the SAME equation with an
independent method (bisection) in Python. Two different algorithms landing on
the same root is strong evidence both are right (a cross-method differential,
not a golden master). The eigen formula and the Python lambda encode the same
function; we compare the solved variable within a small tolerance.

Pure Python + the plain eigenscript build; no LibreOffice.
"""
import os, subprocess, sys, tempfile, shutil

EIGS = os.environ.get("EIGENSCRIPT", "eigenscript")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (label, eigen formula, python f, target, var_init, bracket lo, hi)
CASES = [
    ("linear",     "=2*A1+3",         lambda x: 2 * x + 3,          13, 1,  0.0, 100.0),
    ("cubic",      "=A1*A1*A1",       lambda x: x ** 3,             27, 1,  0.0, 10.0),
    ("reciprocal", "=100/A1",         lambda x: 100 / x,            4,  10, 1.0, 100.0),
    ("square",     "=A1*A1",          lambda x: x * x,              16, 3,  0.0, 10.0),
    ("quadratic",  "=A1*A1-4*A1+3",   lambda x: x * x - 4 * x + 3,  0,  5,  2.5, 10.0),
]
TOL = 1e-4


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
        return r.stdout.strip()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def eigs_goal_seek(formula, target, var_init):
    prog = (
        "import sheet\ns is sheet.new_sheet of null\n"
        "sheet.set_cell of [s, \"A1\", %s]\n" % eigs_str(str(var_init)) +
        "sheet.set_cell of [s, \"B1\", %s]\n" % eigs_str(formula) +
        "sheet.recalc of s\n"
        "r is sheet.goal_seek of [s, \"B1\", %d, \"A1\"]\n" % target +
        "print of (str of r)\n")
    return float(run_eigs(prog))


def bisect(f, target, lo, hi, tol=1e-12, iters=200):
    glo = f(lo) - target
    for _ in range(iters):
        mid = (lo + hi) / 2
        gm = f(mid) - target
        if abs(gm) < tol:
            return mid
        if (glo < 0) == (gm < 0):
            lo, glo = mid, gm
        else:
            hi = mid
    return (lo + hi) / 2


def main():
    failures = 0
    for label, formula, f, target, init, lo, hi in CASES:
        mine = eigs_goal_seek(formula, target, init)
        ref = bisect(f, target, lo, hi)
        if abs(mine - ref) > TOL:
            failures += 1
            print("FAIL %-11s eigen=%.8f  bisection=%.8f" % (label, mine, ref))
        else:
            print("PASS %-11s -> %.6f  (bisection %.6f)" % (label, mine, ref))
    if failures:
        print("\n%d Goal Seek divergence(s) from Python bisection" % failures)
        sys.exit(1)
    print("\neigen-sheet Goal Seek (secant) agrees with Python bisection")


if __name__ == "__main__":
    main()
