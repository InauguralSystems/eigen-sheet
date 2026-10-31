#!/usr/bin/env python3
"""Regression tests for issue #70: approximate lookups skip blank cells."""
import os
import shutil
import subprocess
import tempfile

EIGS = os.environ.get("EIGENSCRIPT", "eigenscript")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CASES = [
    # The reported trailing-blank reproducer.
    ("VLOOKUP(6,A1:A4,1)", "5"),
    ("MATCH(6,A1:A4,1)", "3"),
    ("LOOKUP(6,A1:A4)", "5"),
    # Interior blanks, including the horizontal lookup path.
    ("VLOOKUP(6,A1:A5,1)", "5"),
    ("MATCH(6,A1:A5,1)", "3"),
    ("LOOKUP(6,A1:A5)", "5"),
    ("HLOOKUP(6,C1:F1,1)", "5"),
    # Descending approximate MATCH must skip a trailing blank too.
    ("MATCH(-1,H1:H4,-1)", "3"),
]

MALFORMED = [
    "MATCH(6,A1:A4,)",
    "VLOOKUP(6,A1:A4,1,)",
    "LOOKUP(6,A1:A4,)",
    "HLOOKUP(6,C1:F1,1,)",
]


def quote(value):
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def run(source, tmp):
    app = os.path.join(tmp, "issue_70.eigs")
    with open(app, "w", encoding="utf-8") as stream:
        stream.write(source)
    return subprocess.run(
        [EIGS, app], cwd=tmp, capture_output=True, text=True, timeout=20
    )


def main():
    failures = 0
    with tempfile.TemporaryDirectory(prefix="eigen-sheet-issue-70-") as tmp:
        module = os.path.join(tmp, "eigs_modules", "sheet")
        os.makedirs(module)
        shutil.copy(os.path.join(ROOT, "sheet.eigs"), module)
        shutil.copy(os.path.join(ROOT, "eigs.json"), module)
        lines = ["import sheet", "s is sheet.new_sheet of null"]
        # A1:A4 is the issue repro; A1:A5 moves that blank inside the range.
        for addr, value in {
            "A1": "1", "A2": "3", "A3": "5", "A5": "7",
            "C1": "1", "D1": "3", "E1": "5",
            "H1": "5", "H2": "3", "H3": "1",
        }.items():
            if value:
                lines.append("sheet.set_cell of [s, %s, %s]" % (quote(addr), quote(value)))
        for row, (formula, _) in enumerate(CASES, 1):
            lines.append("sheet.set_cell of [s, %s, %s]" % (quote("J%d" % row), quote("=" + formula)))
        lines.append("sheet.recalc of s")
        for row in range(1, len(CASES) + 1):
            lines.append('print of (sheet.display of [s, %s])' % quote("J%d" % row))
        result = run("\n".join(lines) + "\n", tmp)
        if result.returncode:
            print("FAIL: regression program exited %d" % result.returncode)
            print(result.stdout + result.stderr)
            failures += 1
        else:
            actual = result.stdout.splitlines()
            for (formula, expected), got in zip(CASES, actual):
                if got == expected:
                    print("PASS: =%s -> %s" % (formula, got))
                else:
                    print("FAIL: =%s -> %s (Calc: %s)" % (formula, got, expected))
                    failures += 1

        # Each malformed call runs alone under a timeout so parser non-progress
        # is reported as a failure rather than hanging recalc or the suite.
        for formula in MALFORMED:
            source = "\n".join([
                "import sheet", "s is sheet.new_sheet of null",
                'sheet.set_cell of [s, "A1", "1"]',
                'sheet.set_cell of [s, "B1", %s]' % quote("=" + formula),
                "sheet.recalc of s", 'print of (sheet.display of [s, "B1"])', "",
            ])
            try:
                malformed = run(source, tmp)
            except subprocess.TimeoutExpired:
                print("FAIL: =%s hung recalc" % formula)
                failures += 1
                continue
            got = malformed.stdout.splitlines()[-1] if malformed.stdout.splitlines() else ""
            if malformed.returncode == 0 and got.startswith("#"):
                print("PASS: =%s stopped with %s" % (formula, got))
            else:
                print("FAIL: =%s did not stop with an error (rc=%d, output=%r)" %
                      (formula, malformed.returncode, got))
                failures += 1
    if failures:
        print("FAIL: %d issue #70 regression(s)" % failures)
        return 1
    print("PASS: all issue #70 regressions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
