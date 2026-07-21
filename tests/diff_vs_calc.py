#!/usr/bin/env python3
"""Differential oracle: eigen-sheet vs a real spreadsheet (LibreOffice Calc).

For the numeric operations every spreadsheet agrees on — arithmetic with
precedence, cell references, SUM over a range — "what right looks like" is not
ours to assert. It's what a real, used spreadsheet computes. So we write the
SAME cells and formulas into an .xlsx (fullCalcOnLoad, so no stale cached
values), convert it to CSV with headless LibreOffice Calc, and float-diff its
computed values against eigen-sheet's recalc. LibreOffice's numbers are the
reference.

Error semantics (#CYCLE, div-by-zero) and cursor/selection behavior differ
across engines, so they are NOT checked here — they live in the model oracle.
This oracle owns the numeric consensus only.

Skips (exit 2) when openpyxl or a working LibreOffice *Calc* is unavailable —
e.g. a box with libreoffice-core but not libreoffice-calc. CI installs both
and treats a skip as failure, so the check is never silently dropped there.
"""
import csv, glob, os, re, shutil, subprocess, sys, tempfile

EIGS = os.environ.get("EIGENSCRIPT", "eigenscript")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOFFICE = next((b for b in ("libreoffice", "soffice", "localc") if shutil.which(b)), None)

# Test grid: address -> raw cell content (numbers and formulas). Numeric only.
CELLS = {
    "A1": "5",    "A2": "3",    "A3": "8",     "A4": "-2",
    "B1": "=A1+A2",         # 8
    "B2": "=A1*A2-A4",      # 17
    "B3": "=(A1+A2)*A3",    # 64
    "B4": "=A1/A2",         # 1.666...
    "C1": "=SUM(A1:A4)",    # 14
    "C2": "=SUM(A1:A3)/2",  # 8
    "C3": "=B1+C1",         # 22   (formula referencing formulas)
    "C4": "=-A1+A3*2",      # 11   (unary minus + precedence)
    "D1": "=SUM(A1:C1)",    # 27   (A1+B1+C1 = 5+8+14)
    "E1": "=AVERAGE(A1:A4)",             # 3.5  (5+3+8-2)/4
    "E2": "=MIN(A1:A4)",                 # -2
    "E3": "=MAX(A1:A4)",                 # 8
    "E4": "=IF(A1>A2,100,200)",          # 100  (5 > 3)
    "F1": "=IF(A1<A2,10,20)",            # 20   (5 < 3 false)
    "F2": "=IF(SUM(A1:A4)>10,MAX(A1:A4),MIN(A1:A4))",  # 8 (14>10 -> MAX)
    "F3": "=IF(A2=3,A3*2,0)",            # 16   (equality)
}


def col_to_num(letters):
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n


def addr_parts(a):
    m = re.match(r"([A-Z]+)([0-9]+)", a)
    return m.group(1), int(m.group(2))


def eigs_values():
    """eigen-sheet's computed value for every formula cell: {addr: float}."""
    body = "\n".join('sheet.set_cell of [s, "%s", "%s"]' % (a, raw)
                     for a, raw in CELLS.items())
    prints = "\n".join(
        'print of ("%s\\t" + (str of (sheet.get of [s, "%s"])))' % (a, a)
        for a, raw in CELLS.items() if raw.startswith("="))
    prog = ("import sheet\ns is sheet.new_sheet of null\n%s\nsheet.recalc of s\n%s\n"
            % (body, prints))
    tmp = tempfile.mkdtemp()
    try:
        md = os.path.join(tmp, "eigs_modules", "sheet"); os.makedirs(md)
        shutil.copy(os.path.join(REPO, "sheet.eigs"), os.path.join(md, "sheet.eigs"))
        shutil.copy(os.path.join(REPO, "eigs.json"), os.path.join(md, "eigs.json"))
        app = os.path.join(tmp, "app.eigs"); open(app, "w").write(prog)
        r = subprocess.run([EIGS, app], cwd=tmp, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise RuntimeError(r.stdout + r.stderr)
        out = {}
        for line in r.stdout.splitlines():
            if "\t" in line:
                a, v = line.split("\t")
                out[a] = float(v)
        return out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def write_xlsx(path):
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    for a, raw in CELLS.items():
        ws[a] = raw if raw.startswith("=") else float(raw)
    wb.calculation.fullCalcOnLoad = True   # force Calc to recompute on load
    wb.save(path)


def calc_values():
    """LibreOffice's computed value for every formula cell: {addr: float}, or None to skip."""
    try:
        import openpyxl  # noqa: F401
    except ImportError:
        print("SKIP: openpyxl not installed")
        return None
    tmp = tempfile.mkdtemp()
    try:
        xlsx = os.path.join(tmp, "grid.xlsx"); write_xlsx(xlsx)
        profile = "file://" + os.path.join(tmp, "profile")
        subprocess.run([SOFFICE, "--headless", "--norestore", "--nolockcheck",
                        "-env:UserInstallation=" + profile,
                        "--convert-to", "csv", "--outdir", tmp, xlsx],
                       capture_output=True, timeout=180)
        csvs = glob.glob(os.path.join(tmp, "*.csv"))
        if not csvs:
            print("SKIP: LibreOffice produced no CSV (is libreoffice-calc installed?)")
            return None
        grid = list(csv.reader(open(csvs[0], newline="")))
        out = {}
        for a, raw in CELLS.items():
            if not raw.startswith("="):
                continue
            col, row = addr_parts(a)
            out[a] = float(grid[row - 1][col_to_num(col) - 1])
        return out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    if not SOFFICE:
        print("SKIP: no libreoffice/soffice found — external oracle needs one")
        sys.exit(2)
    print("reference engine: %s" % SOFFICE)
    ref = calc_values()
    if ref is None:
        sys.exit(2)
    mine = eigs_values()
    failures = 0
    for a in sorted(CELLS):
        if not CELLS[a].startswith("="):
            continue
        m, r = mine.get(a), ref.get(a)
        if m is None or r is None or abs(m - r) > 1e-9:
            failures += 1
            print("FAIL %-4s eigen-sheet=%r  libreoffice=%r  (%s)" % (a, m, r, CELLS[a]))
        else:
            print("PASS %-4s %-14s = %g" % (a, CELLS[a], r))
    if failures:
        print("\n%d divergence(s) from LibreOffice" % failures)
        sys.exit(1)
    print("\neigen-sheet matches LibreOffice on every numeric formula")


if __name__ == "__main__":
    main()
