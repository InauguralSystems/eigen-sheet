#!/usr/bin/env python3
"""Issue #78: error-producing formulas must not escape recalc or become values."""
import os, shutil, subprocess, sys, tempfile

EIGS = os.environ.get("EIGENSCRIPT", "eigenscript")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# A hand-picked sample of the dispatcher's error branches (`git grep -n
# 'st.err is' sheet.eigs`), each checked for its error token. The derived,
# every-function population lives in tests/issue_78_incomplete_range_recalc.py.
CASES = {
    "D1": "=VLOOKUP(2,A1:B2,3,0)",
    "D2": "=HLOOKUP(10,A1:C2,3,0)",
    "D3": '=AVERAGEIF(A1:A2,">5")',
    "D4": '=AVERAGEIFS(B1:B2,A1:A2,">5")',
    "D5": "=INDEX(A1:B2,3,1)",
    "D6": "=MATCH(99,A1:A2,0)",
    "D7": "=XLOOKUP(99,A1:A2,B1:B2)",
    "D8": "=LOOKUP(2,A1:A2,B1:B1)",
    "D9": "=SQRT(-1)",
    "D10": "=1/0",
    "D11": "=NA()",
    "D12": "=RATE(10,100,800)",
    "D13": "=PERCENTILE(A1:A2,2)",
    "D14": "=FOO(1)",
    "D15": "=1+",
}

def quote(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'

def main():
    tmp = tempfile.mkdtemp(prefix="eigen-sheet-issue-78-")
    try:
        mod = os.path.join(tmp, "eigs_modules", "sheet")
        os.makedirs(mod)
        shutil.copy(os.path.join(ROOT, "sheet.eigs"), mod)
        shutil.copy(os.path.join(ROOT, "eigs.json"), mod)
        lines = ["import sheet", "s is sheet.new_sheet of null"]
        for addr, raw in {"A1":"1", "A2":"2", "B1":"10", "B2":"20", "C1":"99", "C2":"98"}.items():
            lines.append("sheet.set_cell of [s, %s, %s]" % (quote(addr), quote(raw)))
        for addr, formula in CASES.items():
            lines.append("sheet.set_cell of [s, %s, %s]" % (quote(addr), quote(formula)))
        lines.append("sheet.recalc of s")
        for addr in CASES:
            lines.append('print of (%s + "\\t" + (sheet.display of [s, %s]))' % (quote(addr), quote(addr)))
        app = os.path.join(tmp, "app.eigs")
        open(app, "w").write("\n".join(lines) + "\n")
        run = subprocess.run([EIGS, app], cwd=tmp, text=True, capture_output=True, timeout=60)
        if run.returncode:
            print("FAIL: recalc raised/aborted (rc=%d)" % run.returncode)
            print(run.stdout + run.stderr)
            return 1
        got = dict(line.split("\t", 1) for line in run.stdout.splitlines() if "\t" in line)
        failures = 0
        for addr, formula in CASES.items():
            value = got.get(addr, "")
            if not value.startswith("#"):
                failures += 1
                print("FAIL: %s displayed %r, expected an error token (%s)" % (addr, value, formula))
            else:
                print("PASS: %s -> %s" % (formula, value))
        if failures:
            print("FAIL: %d error path(s) returned a value" % failures)
            return 1
        print("PASS: recalc completed and every error-provoking function displayed an error token")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

if __name__ == "__main__":
    sys.exit(main())
