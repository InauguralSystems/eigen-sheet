#!/usr/bin/env python3
"""xlsx export + import oracle.

EXPORT: eigen-sheet builds an .xlsx from scratch — a stored (uncompressed) ZIP
of OOXML parts, CRC32 by hand. The proof it's a *valid* .xlsx is that two
independent canonical OOXML readers open it and agree with eigen-sheet's own
values: openpyxl and headless LibreOffice Calc.

IMPORT (#39): from_xlsx reads a real .xlsx back into a sheet. Real Excel/
LibreOffice files DEFLATE their entries and store text in a shared-string table,
so import uses the upstream `inflate` builtin (EigenScript #693, `make zlib`)
plus a sharedStrings pass. Three checks:
  A. round-trip — to_xlsx -> from_xlsx reproduces every displayed value (STORED
     entries; no external reader needed).
  B. a real DEFLATE-compressed file (openpyxl, ZIP_DEFLATED, live formulas)
     imports and recomputes to the same values LibreOffice shows.
  C. a shared-strings file (t="s" indices) imports with the right text.

Skips (exit 2) when openpyxl / LibreOffice are unavailable, or when the
EigenScript build lacks zlib (import needs inflate). CI builds with `make zlib`.
"""
import csv, glob, math, os, re, shutil, subprocess, sys, tempfile, zipfile

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


def run_src(src, cwd):
    """Write eigen source to a temp app and run it."""
    app = os.path.join(cwd, "_run.eigs"); open(app, "w").write(src)
    return run_eigs(app, cwd)


def parse_kv(out):
    d = {}
    for line in out.splitlines():
        if "\t" in line:
            a, v = line.split("\t", 1); d[a] = v
        elif line:
            d[line] = ""
    return d


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


def norm_csv(s):
    """A LibreOffice csv cell -> eigen display() form (round floats to 4dp)."""
    try:
        return norm(float(s))
    except (ValueError, TypeError):
        return s


def libre_csv(xlsx, tmp):
    """LibreOffice's computed values for xlsx as {addr: str} (cols A.. rows 1..)."""
    subprocess.run([SOFFICE, "--headless", "--norestore", "--nolockcheck",
                    "-env:UserInstallation=file://" + os.path.join(tmp, "pr"),
                    "--convert-to", "csv", "--outdir", tmp, xlsx],
                   capture_output=True, timeout=180)
    csvs = sorted(glob.glob(os.path.join(tmp, "*.csv")), key=os.path.getmtime)
    grid = list(csv.reader(open(csvs[-1], newline=""))) if csvs else []
    out = {}
    for r, row in enumerate(grid, start=1):
        for c, val in enumerate(row, start=1):
            out[(r, c)] = val
    return out


def import_prog(xlsx, addrs):
    """An eigen program that imports xlsx and prints display() for each addr."""
    prints = "\n".join('print of (%s + "\\t" + (sheet.display of [s, %s]))' %
                       (eigs_str(a), eigs_str(a)) for a in addrs)
    return ("import sheet\ns is sheet.new_sheet of null\n"
            "sheet.from_xlsx of [s, %s]\n" % eigs_str(xlsx) + prints + "\n")


def has_zlib(tmp):
    """True if this EigenScript build has the inflate/deflate (zlib) extension."""
    p = os.path.join(tmp, "zprobe.eigs")
    open(p, "w").write("print of (str of (len of (deflate of [104, 105])))\n")
    r = subprocess.run([EIGS, p], cwd=tmp, capture_output=True, text=True, timeout=30)
    return r.returncode == 0


def main():
    try:
        import openpyxl
    except ImportError:
        print("SKIP: openpyxl not installed"); sys.exit(2)
    if not SOFFICE:
        print("SKIP: no libreoffice"); sys.exit(2)

    tmp = tempfile.mkdtemp()
    failures = 0
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
        mine = parse_kv(run_eigs(app, tmp))

        # ---- EXPORT: eigen's .xlsx reads back in openpyxl AND LibreOffice ----
        wb = openpyxl.load_workbook(xlsx); ws = wb.active
        px = {a: norm(ws.cell(row=addr_rc(a)[0], column=addr_rc(a)[1]).value) for a in GRID}
        lo_grid = libre_csv(xlsx, tmp)
        for a in sorted(GRID, key=addr_rc):
            row, col = addr_rc(a)
            m, p, l = mine[a], px[a], norm_csv(lo_grid.get((row, col), "<oob>"))
            if not (m == p == l):
                failures += 1
                print("FAIL export %-3s eigen=%r openpyxl=%r libreoffice=%r" % (a, m, p, l))
            else:
                print("PASS export %-3s = %r" % (a, m))

        # ---- IMPORT (#39). Needs inflate for B/C; A is stored-only. ----
        if not has_zlib(tmp):
            print("SKIP import: EigenScript built without zlib (inflate)");
            if failures:
                print("\n%d xlsx divergence(s)" % failures); sys.exit(1)
            print("\nexport OK; import skipped (no zlib)"); sys.exit(0)

        # A. round-trip: to_xlsx (from the export above) -> from_xlsx == mine
        rt = parse_kv(run_src(import_prog(xlsx, list(GRID)), tmp))
        for a in sorted(GRID, key=addr_rc):
            if rt.get(a) != mine[a]:
                failures += 1
                print("FAIL rndtrip %-3s from_xlsx=%r orig=%r" % (a, rt.get(a), mine[a]))
            else:
                print("PASS rndtrip %-3s = %r" % (a, rt.get(a)))

        # B. a real DEFLATE-compressed file (openpyxl), formulas live, vs LibreOffice
        real = os.path.join(tmp, "real.xlsx")
        wb2 = openpyxl.Workbook(); w2 = wb2.active
        w2["A1"] = 5; w2["A2"] = 3; w2["A3"] = "=A1+A2"
        w2["B1"] = "widget"; w2["B2"] = "=A3*2"; w2["C1"] = 3.14159; w2["C2"] = True
        wb2.save(real)  # openpyxl writes ZIP_DEFLATED
        assert 8 in {i.compress_type for i in zipfile.ZipFile(real).infolist()}, "not deflated"
        addrs_b = ["A1", "A2", "A3", "B1", "B2", "C1", "C2"]
        eig_b = parse_kv(run_src(import_prog(real, addrs_b), tmp))
        lo_b = libre_csv(real, tmp)
        for a in addrs_b:
            row, col = addr_rc(a)
            e, l = eig_b.get(a, "<none>"), norm_csv(lo_b.get((row, col), "<oob>"))
            if e != l:
                failures += 1
                print("FAIL deflate %-3s eigen=%r libreoffice=%r" % (a, e, l))
            else:
                print("PASS deflate %-3s = %r" % (a, e))

        # C. a shared-strings file (t="s") — hand-built, deflated. Deterministic
        # expected values (no external reader needed for the string table).
        shared = os.path.join(tmp, "shared.xlsx")
        _build_shared_strings_xlsx(shared)
        exp_c = {"A1": "Gross & Net", "A2": "widget", "B1": "42", "B2": "widget", "C1": "84"}
        eig_c = parse_kv(run_src(import_prog(shared, list(exp_c)), tmp))
        for a in sorted(exp_c, key=addr_rc):
            if eig_c.get(a) != exp_c[a]:
                failures += 1
                print("FAIL shared %-3s eigen=%r expected=%r" % (a, eig_c.get(a), exp_c[a]))
            else:
                print("PASS shared %-3s = %r" % (a, eig_c.get(a)))

        if failures:
            print("\n%d xlsx divergence(s)" % failures); sys.exit(1)
        print("\neigen-sheet .xlsx export reads back in openpyxl + LibreOffice, and "
              "from_xlsx imports stored, DEFLATE, and shared-string files")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _build_shared_strings_xlsx(path):
    CT = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
          '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
          '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/></Types>')
    RELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
    WB = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
          '<sheets><sheet name="Sheet1" sheetId="1"/></sheets></workbook>')
    SST = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="3" uniqueCount="2">'
           '<si><t>Gross &amp; Net</t></si><si><t>widget</t></si></sst>')
    SHEET = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
             '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1"><v>42</v></c>'
             '<c r="C1"><f>B1*2</f><v>84</v></c></row>'
             '<row r="2"><c r="A2" t="s"><v>1</v></c><c r="B2" t="s"><v>1</v></c></row>'
             '</sheetData></worksheet>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CT)
        z.writestr("_rels/.rels", RELS)
        z.writestr("xl/workbook.xml", WB)
        z.writestr("xl/sharedStrings.xml", SST)
        z.writestr("xl/worksheets/sheet1.xml", SHEET)


if __name__ == "__main__":
    main()
