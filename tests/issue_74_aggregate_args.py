#!/usr/bin/env python3
"""Regression coverage for issue #74: aggregate argument lists and xlsx import."""
import os
import shutil
import subprocess
import tempfile


EIGS = os.environ.get("EIGENSCRIPT", "eigenscript")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


FORMULAS = [
    ("SUM(1,2)", "3"),
    ("SUM(A1,A2)", "3"),
    ("SUM(A1:A2,5)", "8"),
    ("SUM(A1:A2,B1:B1)", "7"),
    ("SUM(5)", "5"),
    ("MAX(1,2)", "2"),
    ("MIN(A1,B1)", "1"),
    ("PRODUCT(A1,B1)", "4"),
    ("AVERAGE(A1,B1)", "2.5"),
    ("COUNT(A1,B1)", "2"),
    ("COUNTA(A1,B1)", "2"),
    ("MEDIAN(A1,A2,B1)", "2"),
    ("STDEV(A1,A2,B1)", "1.5275"),
    # Expressions and direct numbers must participate, not merely parse.
    ("VAR(A1:A2,3+1)", "2.3333"),
    ("STDEVP(A1:A2,3+1)", "1.2472"),
    ("SUM(A1+1,2)", "4"),
    # COUNTBLANK shares the parser even though Calc itself only accepts one arg.
    ("COUNTBLANK(A1:A2,B1:B1)", "0"),
]


def eigs_string(value):
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def run_program(source, workdir):
    app = os.path.join(workdir, "issue_74.eigs")
    with open(app, "w", encoding="utf-8") as f:
        f.write(source)
    result = subprocess.run(
        [EIGS, app], cwd=workdir, capture_output=True, text=True, timeout=60
    )
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result.stdout.splitlines()


def main():
    failures = 0
    with tempfile.TemporaryDirectory() as tmp:
        module_dir = os.path.join(tmp, "eigs_modules", "sheet")
        os.makedirs(module_dir)
        shutil.copy(os.path.join(REPO, "sheet.eigs"), module_dir)
        shutil.copy(os.path.join(REPO, "eigs.json"), module_dir)

        setup = [
            "import sheet",
            "s is sheet.new_sheet of null",
            'sheet.set_cell of [s, "A1", "1"]',
            'sheet.set_cell of [s, "A2", "2"]',
            'sheet.set_cell of [s, "B1", "4"]',
        ]
        for row, (formula, _) in enumerate(FORMULAS, 1):
            setup.append(
                'sheet.set_cell of [s, "C%d", "=%s"]' % (row, formula)
            )
        setup.append("sheet.recalc of s")
        for row in range(1, len(FORMULAS) + 1):
            setup.append('print of (sheet.display of [s, "C%d"])' % row)
        actual = run_program("\n".join(setup) + "\n", tmp)

        for (formula, expected), got in zip(FORMULAS, actual):
            if got == expected:
                print("PASS: =%s -> %s" % (formula, got))
            else:
                failures += 1
                print("FAIL: =%s -> %s (expected %s)" % (formula, got, expected))

        try:
            import openpyxl
        except ImportError:
            print("FAIL: openpyxl is required for the issue #74 import regression")
            failures += 1
        else:
            xlsx = os.path.join(tmp, "issue_74.xlsx")
            workbook = openpyxl.Workbook()
            worksheet = workbook.active
            worksheet["A1"] = 1
            worksheet["A2"] = 2
            worksheet["B1"] = "=SUM(A1,A2)"
            workbook.save(xlsx)
            imported = run_program(
                "import sheet\n"
                "s is sheet.new_sheet of null\n"
                "sheet.from_xlsx of [s, %s]\n"
                'print of (sheet.display of [s, "B1"])\n' % eigs_string(xlsx),
                tmp,
            )
            got = imported[-1] if imported else "<no output>"
            if got == "3":
                print("PASS: from_xlsx =SUM(A1,A2) -> 3")
            else:
                failures += 1
                print("FAIL: from_xlsx =SUM(A1,A2) -> %s (expected 3)" % got)

    if failures:
        print("%d issue #74 regression(s) failed" % failures)
        raise SystemExit(1)
    print("All issue #74 regressions passed")


if __name__ == "__main__":
    main()
