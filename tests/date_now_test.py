#!/usr/bin/env python3
"""TODAY() / NOW() model oracle (#34).

TODAY()/NOW() read the wall clock — a *nondeterministic* input — so they are
deliberately kept OUT of the LibreOffice differential oracle (diff_vs_calc.py):
their value changes every run, so a byte-diff against Calc would flake. Instead
this pins the two properties that actually matter for eigen-sheet's observer
model:

  1. Replayability. eigen-sheet's core promise is "same edits -> same grid."
     The clock read flows through EigenScript's trace tape (clock_unix is
     tape-captured, EigenScript #688), so a recorded recalc (EIGS_TRACE) must
     reproduce byte-identically on replay (EIGS_REPLAY). This is the test that
     would fail if TODAY()/NOW() ever bypassed the tape.

  2. Internal consistency. Within one recalc the clock is snapshotted once, so
     every TODAY()/NOW() cell agrees (Calc behaves the same). TODAY() is NOW()
     floored to midnight, so NOW()-TODAY() is the fractional day in [0, 1), and
     TODAY() lands in a sane calendar range.

Pure Python; no display, no LibreOffice.
"""
import os, subprocess, sys, tempfile, shutil

EIGS = os.environ.get("EIGENSCRIPT", "eigenscript")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROG = """import sheet
s is sheet.new_sheet of null
sheet.set_cell of [s, "A1", "=NOW()"]
sheet.set_cell of [s, "A2", "=TODAY()"]
sheet.set_cell of [s, "A3", "=TODAY()"]
sheet.set_cell of [s, "A4", "=NOW()-TODAY()"]
sheet.set_cell of [s, "A5", "=YEAR(TODAY())"]
sheet.recalc of s
print of ("NOW\\t" + (str of (sheet.get of [s, "A1"])))
print of ("TODAY\\t" + (str of (sheet.get of [s, "A2"])))
print of ("TODAY2\\t" + (str of (sheet.get of [s, "A3"])))
print of ("FRAC\\t" + (str of (sheet.get of [s, "A4"])))
print of ("YEAR\\t" + (str of (sheet.get of [s, "A5"])))
"""


def run(app, env_extra):
    env = dict(os.environ)
    env.update(env_extra)
    r = subprocess.run([EIGS, app], cwd=os.path.dirname(app),
                       capture_output=True, text=True, timeout=60, env=env)
    if r.returncode != 0:
        print("FAIL: eigenscript errored\n" + r.stdout + r.stderr)
        sys.exit(1)
    return r.stdout


def parse(out):
    d = {}
    for line in out.splitlines():
        if "\t" in line:
            k, v = line.split("\t")
            d[k] = v
    return d


def main():
    tmp = tempfile.mkdtemp()
    try:
        md = os.path.join(tmp, "eigs_modules", "sheet"); os.makedirs(md)
        shutil.copy(os.path.join(REPO, "sheet.eigs"), os.path.join(md, "sheet.eigs"))
        shutil.copy(os.path.join(REPO, "eigs.json"), os.path.join(md, "eigs.json"))
        app = os.path.join(tmp, "app.eigs"); open(app, "w").write(PROG)
        tape = os.path.join(tmp, "run.tape")

        # 1) record, 2) replay — must be byte-identical (the observer property)
        first = run(app, {"EIGS_TRACE": tape})
        second = run(app, {"EIGS_REPLAY": tape})
        if first != second:
            print("FAIL: record -> replay not byte-identical (clock bypassed the tape?)")
            print("--- record ---\n" + first + "--- replay ---\n" + second)
            sys.exit(1)
        print("PASS: TODAY()/NOW() record -> replay byte-identical")

        d = parse(first)
        now, today, today2, frac, year = (
            float(d["NOW"]), float(d["TODAY"]), float(d["TODAY2"]),
            float(d["FRAC"]), float(d["YEAR"]))

        # TODAY() floors NOW() to midnight
        import math
        if today != math.floor(now):
            print("FAIL: TODAY() (%r) != floor(NOW()) (%r)" % (today, math.floor(now)))
            sys.exit(1)
        # two TODAY() cells in one recalc share the single clock snapshot
        if today != today2:
            print("FAIL: two TODAY() cells disagree (%r vs %r) — clock not snapshotted once"
                  % (today, today2))
            sys.exit(1)
        # NOW()-TODAY() is the fractional day, in [0, 1)
        if not (0.0 <= frac < 1.0):
            print("FAIL: NOW()-TODAY() = %r not in [0,1)" % frac)
            sys.exit(1)
        # sane calendar range (serial 44927 = 2023-01-01, 55153 = 2051-01-01)
        if not (44927 <= today < 55153):
            print("FAIL: TODAY() serial %r outside a sane calendar range" % today)
            sys.exit(1)
        if year < 2023 or year > 2050:
            print("FAIL: YEAR(TODAY()) = %r outside a sane range" % year)
            sys.exit(1)
        print("PASS: TODAY()=floor(NOW()), snapshot-consistent, frac in [0,1), calendar sane")
        print("ALL PASS (date_now)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
