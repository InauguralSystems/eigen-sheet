#!/usr/bin/env python3
"""Every numeric dispatcher rejects an errored/non-finite argument safely.

The population is extracted from sheet.eigs' dispatcher clauses.  Direct cells
prove recalc cannot raise and retains #NUM!; IFERROR cells prove the error is
catchable.  The latter are ordinary numeric formulas suitable for the Calc
oracle method used by diff_vs_calc.py.
"""
import csv, glob, os, re, shutil, subprocess, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EIGS = os.environ.get("EIGENSCRIPT", "eigenscript")
SRC = open(os.path.join(ROOT, "sheet.eigs"), encoding="utf-8").read()

# Derive, rather than hand-maintain, the function population from dispatcher
# clauses whose arguments are numeric. The assertion makes a newly added
# numeric family fail this test until its formula shape is represented.
clauses = re.findall(r'if fname == "([A-Z]+)"(?: or fname == "([A-Z]+)")+', SRC)
NUMERIC = set()
for match in re.finditer(r'if fname == "ABS".*?\n\s*local nargs', SRC, re.S):
    NUMERIC.update(re.findall(r'fname == "([A-Z]+)"', match.group(0)))
for anchor in ('if fname == "DATE"', 'if fname == "ISEVEN"'):
    start = SRC.index(anchor)
    end = SRC.index(':', start)
    NUMERIC.update(re.findall(r'fname == "([A-Z]+)"', SRC[start:end]))
NUMERIC.add("TEXT")

one = {"ABS", "INT", "TRUNC", "SIGN", "SQRT", "YEAR", "MONTH", "DAY",
       "WEEKDAY", "DATEVALUE", "HOUR", "MINUTE", "SECOND", "ISEVEN", "ISODD"}
two = {"ROUND", "ROUNDUP", "ROUNDDOWN", "MOD", "POWER", "CEILING", "FLOOR",
       "EDATE", "EOMONTH", "DATEDIF", "TEXT"}
three = {"DATE", "TIME"}
assert NUMERIC == one | two | three, "unrepresented numeric dispatcher(s): %r" % sorted(NUMERIC - one - two - three)

def formula(fn):
    bad = "1E300*1E10"
    if fn == "DATEVALUE":
        return "DATEVALUE(%s)" % bad
    if fn == "TEXT":
        return 'TEXT(%s,"0.00")' % bad
    args = [bad]
    if fn in two:
        args += ['"d"' if fn == "DATEDIF" else "1"]
    if fn in three:
        args += ["1", "1"]
    return "%s(%s)" % (fn, ",".join(args))

def q(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'

ordered = sorted(NUMERIC)
lines = ["import sheet", "s is sheet.new_sheet of null"]
for i, fn in enumerate(ordered):
    lines.append("sheet.set_cell of [s,%s,%s]" % (q("A%d" % (i+1)), q("=" + formula(fn))))
    lines.append("sheet.set_cell of [s,%s,%s]" % (q("B%d" % (i+1)), q("=IFERROR(" + formula(fn) + ",7101)")))
lines += ["sheet.recalc of s"]
for i in range(len(ordered)):
    lines.append('print of ((sheet.display of [s,%s]) + "\\t" + (sheet.display of [s,%s]))' % (q("A%d"%(i+1)), q("B%d"%(i+1))))
lines.append('print of ("CSV\\t" + (sheet.to_csv of [s,0,0,1,%d]))' % (len(ordered)-1))

with tempfile.TemporaryDirectory() as tmp:
    md = os.path.join(tmp, "eigs_modules", "sheet"); os.makedirs(md)
    for name in ("sheet.eigs", "pdf.eigs", "eigs.json"):
        shutil.copy(os.path.join(ROOT, name), os.path.join(md, name))
    app = os.path.join(tmp, "app.eigs")
    open(app, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    run = subprocess.run([EIGS, app], cwd=tmp, text=True, capture_output=True, timeout=60)
if run.returncode:
    raise SystemExit("FAIL: recalc raised\n" + run.stdout + run.stderr)
rows = [line.split("\t") for line in run.stdout.splitlines() if "\t" in line and not line.startswith("CSV\t")]
if len(rows) != len(ordered):
    raise SystemExit("FAIL: expected %d result rows, got %d" % (len(ordered), len(rows)))
for fn, row in zip(ordered, rows):
    if row != ["#NUM!", "7101"]:
        raise SystemExit("FAIL: %s displayed %r (expected #NUM!, catchable 7101)" % (fn, row))
csv_mark = run.stdout.find("CSV\t")
csv_rows = run.stdout[csv_mark + 4:].splitlines() if csv_mark >= 0 else []
if csv_rows != ["#NUM!,7101"] * len(ordered):
    raise SystemExit("FAIL: CSV numeric/error text %r" % csv_rows)
print("PASS: %d/%d derived numeric dispatchers reject overflow without aborting recalc" % (len(rows), len(ordered)))
print("PASS: %d/%d CSV rows preserve the same error and number text" % (len(csv_rows), len(ordered)))

# External oracle: compare the catchability result using the same XLSX ->
# headless-Calc -> CSV method as tests/diff_vs_calc.py. Error token spellings
# differ, so IFERROR's numeric sentinel is the portable semantic comparison.
soffice = next((x for x in ("libreoffice", "soffice", "localc") if shutil.which(x)), None)
if soffice:
    try:
        import openpyxl
    except ImportError:
        raise SystemExit("FAIL: openpyxl missing while LibreOffice is available")
    with tempfile.TemporaryDirectory() as tmp:
        book = os.path.join(tmp, "nonfinite.xlsx")
        wb = openpyxl.Workbook(); ws = wb.active
        for i, fn in enumerate(ordered, 1):
            ws.cell(i, 1).value = "=IFERROR(%s,7101)" % formula(fn)
        wb.calculation.fullCalcOnLoad = True; wb.save(book)
        profile = "file://" + os.path.join(tmp, "profile")
        subprocess.run([soffice, "--headless", "--norestore", "--nolockcheck",
                        "-env:UserInstallation=" + profile, "--convert-to", "csv",
                        "--outdir", tmp, book], check=True, capture_output=True, timeout=180)
        files = glob.glob(os.path.join(tmp, "*.csv"))
        vals = [row[0] for row in csv.reader(open(files[0], newline=""))] if files else []
    if vals != ["7101"] * len(ordered):
        raise SystemExit("FAIL: LibreOffice non-finite catch results %r" % vals)
    print("PASS: %d/%d derived numeric dispatcher errors agree with LibreOffice IFERROR" % (len(vals), len(ordered)))
else:
    print("SKIP: LibreOffice unavailable; external half runs in calc-oracle CI")
