#!/usr/bin/env python3
"""CSV differential oracle: eigen-sheet's to_csv vs Python's csv module.

CSV is a well-specified format (RFC 4180) with a canonical, independent
implementation in every standard library. So — like the vim differential for
eigen-edit — we don't assert what "right" looks like: Python's csv.writer does.
We build a grid, export it with eigen-sheet's to_csv, and byte-compare against
what csv.writer produces for the same displayed values (QUOTE_MINIMAL, \\n
terminator = the RFC-4180 rules eigen-sheet targets). Then we round-trip:
from_csv(export) re-exported must equal the export (parser is the writer's
inverse).

No LibreOffice needed — pure Python + the plain eigenscript build.
"""
import csv, io, os, subprocess, sys, tempfile, shutil

EIGS = os.environ.get("EIGENSCRIPT", "eigenscript")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# INPUTS: raw cell contents to set (row-major, 0-based from A1).
INPUTS = [
    ["5",    "hello",           "a,b"],
    ["=5*2", 'he said "hi"',    "trailing,"],
    ["3.5",  "",                "plain"],
]
# EXPECTED_DISPLAY: what each cell should DISPLAY as (formula -> computed value).
EXPECTED = [
    ["5",  "hello",        "a,b"],
    ["10", 'he said "hi"', "trailing,"],
    ["3.5", "",            "plain"],
]
NROWS, NCOLS = len(INPUTS), len(INPUTS[0])


def eigs_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


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


def between(out, tag):
    """Extract the text between <<<tag and >>>tag sentinel lines."""
    start = out.index("<<<" + tag + "\n") + len("<<<" + tag + "\n")
    end = out.index(">>>" + tag, start)
    body = out[start:end]
    return body[:-1] if body.endswith("\n") else body


def eigs_export_and_roundtrip():
    sets = "\n".join(
        "sheet.set_cell of [s, %s, %s]" % (eigs_str(col_letter(c) + str(r + 1)), eigs_str(INPUTS[r][c]))
        for r in range(NROWS) for c in range(NCOLS))
    prog = (
        "import sheet\n"
        "s is sheet.new_sheet of null\n" + sets + "\n"
        "sheet.recalc of s\n"
        "out is sheet.to_csv of [s, 0, 0, %d, %d]\n" % (NCOLS - 1, NROWS - 1) +
        'print of "<<<EXPORT"\nprint of out\nprint of ">>>EXPORT"\n'
        # round-trip: import the export into a fresh sheet and re-export
        "s2 is sheet.new_sheet of null\n"
        "sheet.from_csv of [s2, out, 0, 0]\n"
        "rt is sheet.to_csv of [s2, 0, 0, %d, %d]\n" % (NCOLS - 1, NROWS - 1) +
        'print of "<<<ROUNDTRIP"\nprint of rt\nprint of ">>>ROUNDTRIP"\n')
    out = run_eigs(prog)
    return between(out, "EXPORT"), between(out, "ROUNDTRIP")


def py_reference():
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")   # QUOTE_MINIMAL, RFC-4180
    for row in EXPECTED:
        w.writerow(row)
    return buf.getvalue().rstrip("\n")


def main():
    export, roundtrip = eigs_export_and_roundtrip()
    ref = py_reference()
    ok = True
    if export != ref:
        ok = False
        print("FAIL export vs Python csv:")
        print("  eigen-sheet: %r" % export)
        print("  python csv : %r" % ref)
    else:
        print("PASS to_csv matches Python csv.writer (RFC-4180 quoting)")
    if roundtrip != export:
        ok = False
        print("FAIL round-trip (from_csv is not to_csv's inverse):")
        print("  export    : %r" % export)
        print("  roundtrip : %r" % roundtrip)
    else:
        print("PASS from_csv(to_csv(grid)) re-exports identically")
    if not ok:
        sys.exit(1)
    print("\neigen-sheet CSV matches the canonical reference")


if __name__ == "__main__":
    main()
