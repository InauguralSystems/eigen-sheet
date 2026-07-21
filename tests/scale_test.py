#!/usr/bin/env python3
"""Scale correctness: a large grid recalcs to the right values.

Not a perf gate (wall-clock is too flaky for CI, and recalc has a known
upstream cycle-collector scaling ceiling — EigenScript #685). This checks that
the O(V+E) in-degree recalc stays CORRECT at size: a long dependency chain, a
wide SUM, and a reference at the far corner of the addressable range (the full
Calc extent, XFD1048576 = 16384 cols x 1048576 rows, sparse so it costs
nothing). Pure Python + the plain eigenscript build.
"""
import os, subprocess, sys, tempfile, shutil

EIGS = os.environ.get("EIGENSCRIPT", "eigenscript")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
N = 1000


def main():
    tmp = tempfile.mkdtemp()
    try:
        md = os.path.join(tmp, "eigs_modules", "sheet"); os.makedirs(md)
        shutil.copy(os.path.join(REPO, "sheet.eigs"), os.path.join(md, "sheet.eigs"))
        shutil.copy(os.path.join(REPO, "eigs.json"), os.path.join(md, "eigs.json"))
        prog = (
            "import sheet\ns is sheet.new_sheet of null\n"
            'sheet.set_cell of [s, "A1", "1"]\n'
            "for i in range of %d:\n" % N +
            "    if i >= 1:\n"
            '        sheet.set_cell of [s, "A" + (str of (i + 1)), "=A" + (str of i) + "+1"]\n'
            'sheet.set_cell of [s, "C1", "=SUM(A1:A%d)"]\n' % N +
            'sheet.set_cell of [s, "XFD1048576", "=A%d*2"]\n' % N +
            "sheet.recalc of s\n"
            'print of ("chain=" + (sheet.display of [s, "A%d"]))\n' % N +
            'print of ("sum=" + (sheet.display of [s, "C1"]))\n'
            'print of ("far=" + (sheet.display of [s, "XFD1048576"]))\n')
        app = os.path.join(tmp, "app.eigs"); open(app, "w").write(prog)
        r = subprocess.run([EIGS, app], cwd=tmp, capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            print("FAIL: eigenscript errored\n" + r.stdout + r.stderr); sys.exit(1)
        got = dict(line.split("=", 1) for line in r.stdout.splitlines() if "=" in line)
        expect = {"chain": str(N), "sum": str(N * (N + 1) // 2), "far": str(2 * N)}
        failures = 0
        for k, want in expect.items():
            if got.get(k) != want:
                failures += 1
                print("FAIL %-6s eigen=%r want=%r" % (k, got.get(k), want))
            else:
                print("PASS %-6s = %s" % (k, want))
        if failures:
            sys.exit(1)
        print("\nrecalc stays correct at scale (%d-cell chain + wide SUM + far corner)" % N)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
