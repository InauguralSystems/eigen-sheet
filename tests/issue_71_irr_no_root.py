#!/usr/bin/env python3
"""Regression coverage for issue #71: IRR must reject a missing root."""
import os
import shutil
import subprocess
import tempfile


EIGS = os.environ.get("EIGENSCRIPT", "eigenscript")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    with tempfile.TemporaryDirectory() as tmp:
        module_dir = os.path.join(tmp, "eigs_modules", "sheet")
        os.makedirs(module_dir)
        shutil.copy(os.path.join(REPO, "sheet.eigs"), module_dir)
        shutil.copy(os.path.join(REPO, "eigs.json"), module_dir)
        source = """import sheet
s is sheet.new_sheet of null
sheet.set_cell of [s, "A1", "100"]
sheet.set_cell of [s, "A2", "200"]
sheet.set_cell of [s, "A3", "300"]
sheet.set_cell of [s, "B1", "=IRR(A1:A3)"]
sheet.set_cell of [s, "C1", "-1000"]
sheet.set_cell of [s, "C2", "300"]
sheet.set_cell of [s, "C3", "400"]
sheet.set_cell of [s, "C4", "500"]
sheet.set_cell of [s, "C5", "600"]
sheet.set_cell of [s, "D1", "=IRR(C1:C5)"]
sheet.set_cell of [s, "E1", "-100"]
sheet.set_cell of [s, "E2", "1000000"]
sheet.set_cell of [s, "F1", "=IRR(E1:E2)"]
sheet.set_cell of [s, "G1", "-800"]
sheet.set_cell of [s, "G2", "-400"]
sheet.set_cell of [s, "G3", "400"]
sheet.set_cell of [s, "H1", "=IRR(G1:G3)"]
sheet.set_cell of [s, "I1", "-100"]
sheet.set_cell of [s, "I2", "60"]
sheet.set_cell of [s, "I3", "60"]
sheet.set_cell of [s, "J1", "=IRR(I1:I3)"]
sheet.recalc of s
print of (sheet.display of [s, "B1"])
print of (sheet.display of [s, "D1"])
print of (sheet.display of [s, "F1"])
print of (sheet.display of [s, "H1"])
print of (sheet.display of [s, "J1"])
"""
        app = os.path.join(tmp, "issue_71.eigs")
        with open(app, "w", encoding="utf-8") as f:
            f.write(source)
        result = subprocess.run(
            [EIGS, app], cwd=tmp, capture_output=True, text=True, timeout=60
        )
        if result.returncode:
            print("FAIL: interpreter exited %d: %s" %
                  (result.returncode, result.stdout + result.stderr))
            raise SystemExit(1)
        got = result.stdout.splitlines()

        # Malformed ranges may be rejected by recalc or stored as a cell error;
        # either outcome is valid, but the timeout makes failure to progress a
        # hard regression rather than hanging the suite.
        malformed = os.path.join(tmp, "issue_71_malformed.eigs")
        with open(malformed, "w", encoding="utf-8") as f:
            f.write("""import sheet
s is sheet.new_sheet of null
sheet.set_cell of [s, "A1", "1"]
sheet.set_cell of [s, "B1", "=IRR(A1:)"]
sheet.recalc of s
print of (sheet.display of [s, "B1"])
""")
        malformed_result = subprocess.run(
            [EIGS, malformed], cwd=tmp, capture_output=True, text=True, timeout=60
        )

    failures = 0
    if len(got) >= 1 and got[0] == "#NUM!":
        print("PASS: same-sign IRR -> #NUM!")
    else:
        failures += 1
        print("FAIL: same-sign IRR -> %s (expected #NUM!)" %
              (got[0] if got else "<no output>"))
    try:
        converged = float(got[1])
    except (IndexError, ValueError):
        converged = None
    # display() uses the sheet's default four-decimal formatting.
    if converged is not None and abs(converged - 0.2488833566) < 1e-4:
        print("PASS: ordinary IRR converges -> %s" % got[1])
    else:
        failures += 1
        print("FAIL: ordinary IRR -> %s (expected about 0.2488833566)" %
              (got[1] if len(got) >= 2 else "<no output>"))
    expected = [(2, 9999.0, "large-rate"), (3, -0.5, "damped"),
                (4, 0.1307, "ordinary two-return")]
    for index, want, label in expected:
        try:
            actual = float(got[index])
        except (IndexError, ValueError):
            actual = None
        if actual is not None and abs(actual - want) < 1e-4:
            print("PASS: %s IRR converges -> %s" % (label, got[index]))
        else:
            failures += 1
            detail = got[index] if len(got) > index else "<no output>"
            print("FAIL: %s IRR -> %s (expected about %s)" %
                  (label, detail, want))
    malformed_lines = malformed_result.stdout.splitlines()
    malformed_display = malformed_lines[-1] if malformed_lines else ""
    if malformed_result.returncode != 0 or malformed_display.startswith("#"):
        detail = ("interpreter error" if malformed_result.returncode != 0
                  else malformed_display)
        print("PASS: malformed IRR stops with error -> %s" % detail)
    else:
        failures += 1
        print("FAIL: malformed IRR -> %s (expected an error)" %
              (malformed_display or "<no output>"))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
