#!/usr/bin/env python3
"""xlsx export oracle: eigen-sheet's to_xlsx read back by openpyxl AND LibreOffice.

eigen-sheet builds an .xlsx from scratch — a stored (uncompressed) ZIP of OOXML
parts, CRC32 by hand, no zip/deflate library (EigenScript has none). The proof
that it's a *valid* .xlsx is that two independent, canonical OOXML readers open
it and agree with eigen-sheet's own values: openpyxl (the Python OOXML library)
and headless LibreOffice Calc (the real target). Reading arbitrary *compressed*
.xlsx back into eigen-sheet needs inflate — an upstream gap, tracked separately.

Skips (exit 2) when openpyxl / LibreOffice are unavailable; CI has both.
"""
import csv, glob, math, os, re, shutil, subprocess, sys, tempfile

EIGS = os.environ.get("EIGENSCRIPT", "eigenscript")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOFFICE = next((b for b in ("libreoffice", "soffice", "localc") if shutil.which(b)), None)

# addr -> raw content (a range A1:B3); mix of number, text, formula, comma-text,
# decimal, and a boolean formula.
GRID = {
    "A1": "5", "B1": "hello",
    "A2": "=A1*2", "B2": "a,b",
    "A3": "3.5", "B3": "=A1>A2",
}
C0, R0, C1, R1 = 0, 0, 1, 2


def eigs_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def col_letter(c):
    s = ""; c += 1
    while c > 0:
        c, r = divmod(c - 1, 26); s = chr(65 + r) + s
    return s


def addr_rc(a):
    m = re.match(r"([A-Z]+)(\d+)", a)
    col = 0
    for ch in m.group(1):
        col = col * 26 + (ord(ch) - 64)
    return int(m.group(2)), col


def run_eigs(prog, cwd):
    r = subprocess.run([EIGS, prog], cwd=cwd, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise RuntimeError(r.stdout + r.stderr)
    return r.stdout


def norm(v):
    """Normalize a reader's value to eigen-sheet's display() string form."""
    if v is None:
        return ""
    if v is True:
        return "TRUE"
    if v is False:
        return "FALSE"
    if isinstance(v, float):
        if v == int(v):
            return str(int(v))
        return str(math.floor(v * 10000 + 0.5) / 10000)
    if isinstance(v, int):
        return str(v)
    return str(v)


def main():
    try:
        import openpyxl
    except ImportError:
        print("SKIP: openpyxl not installed"); sys.exit(2)
    if not SOFFICE:
        print("SKIP: no libreoffice"); sys.exit(2)

    tmp = tempfile.mkdtemp()
    try:
        md = os.path.join(tmp, "eigs_modules", "sheet"); os.makedirs(md)
        shutil.copy(os.path.join(REPO, "sheet.eigs"), os.path.join(md, "sheet.eigs"))
        shutil.copy(os.path.join(REPO, "eigs.json"), os.path.join(md, "eigs.json"))
        xlsx = os.path.join(tmp, "out.xlsx")
        sets = "\n".join("sheet.set_cell of [s, %s, %s]" % (eigs_str(a), eigs_str(raw))
                         for a, raw in GRID.items())
        prints = "\n".join('print of (%s + "\\t" + (sheet.display of [s, %s]))' %
                           (eigs_str(a), eigs_str(a)) for a in GRID)
        prog = ("import sheet\ns is sheet.new_sheet of null\n" + sets + "\nsheet.recalc of s\n"
                "sheet.to_xlsx of [s, %s, %d, %d, %d, %d]\n" % (eigs_str(xlsx), C0, R0, C1, R1) +
                prints + "\n")
        app = os.path.join(tmp, "app.eigs"); open(app, "w").write(prog)
        out = run_eigs(app, tmp)
        mine = {}
        for line in out.splitlines():
            if "\t" in line:
                a, v = line.split("\t", 1); mine[a] = v
            elif line:
                mine[line] = ""

        # reader 1: openpyxl
        wb = __import__("openpyxl").load_workbook(xlsx)
        ws = wb.active
        px = {}
        for a in GRID:
            row, col = addr_rc(a)
            px[a] = norm(ws.cell(row=row, column=col).value)

        # reader 2: LibreOffice -> csv
        subprocess.run([SOFFICE, "--headless", "--norestore", "--nolockcheck",
                        "-env:UserInstallation=file://" + os.path.join(tmp, "pr"),
                        "--convert-to", "csv", "--outdir", tmp, xlsx],
                       capture_output=True, timeout=180)
        csvs = glob.glob(os.path.join(tmp, "*.csv"))
        grid = list(csv.reader(open(csvs[0], newline=""))) if csvs else []
        lo = {}
        for a in GRID:
            row, col = addr_rc(a)
            try:
                lo[a] = grid[row - 1][col - 1]
            except IndexError:
                lo[a] = "<oob>"

        failures = 0
        for a in sorted(GRID, key=addr_rc):
            m, p, l = mine[a], px[a], lo[a]
            if not (m == p == l):
                failures += 1
                print("FAIL %-3s eigen=%r openpyxl=%r libreoffice=%r" % (a, m, p, l))
            else:
                print("PASS %-3s = %r" % (a, m))
        if failures:
            print("\n%d xlsx divergence(s)" % failures); sys.exit(1)
        print("\neigen-sheet's xlsx reads back identically in openpyxl AND LibreOffice")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
