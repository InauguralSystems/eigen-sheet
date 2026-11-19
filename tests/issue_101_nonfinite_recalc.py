#!/usr/bin/env python3
"""Derive the dispatcher population and gate evaluator numeric/error exits.

Every dispatcher name is counted from sheet.eigs.  The generated numeric-family
cases plus focused operator, aggregate, catch, predicate, and text consumers
exercise the common formula-number boundary and first-error exit.  The local
half always runs; the Calc half exits 2 rather than claiming a pass when its
independent oracle is unavailable.
"""
import csv, glob, os, re, shutil, subprocess, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EIGS = os.environ.get("EIGENSCRIPT", "eigenscript")
SRC = open(os.path.join(ROOT, "sheet.eigs"), encoding="utf-8").read()

CLAUSE_NAMES = re.findall(r'fname == "([A-Z][A-Z0-9_.]*)"', SRC)
DERIVED_NAMES = sorted(set(CLAUSE_NAMES))
if not DERIVED_NAMES:
    raise SystemExit("FAIL: dispatcher derivation examined 0 functions")

# Architectural assertions accompany the behavioral matrix: otherwise putting
# the historical placeholder back can be masked by a later guard, and deleting
# an operator's production-time finite guard can be masked by the cell-end net.
to_num_body = SRC[SRC.index("define _to_num"):SRC.index("define _compare")]
if re.search(r'if st\.err != "":\s*return 0', to_num_body):
    raise SystemExit("FAIL: _to_num restored the historical error placeholder")
if "av > 1.7976931348623157e308 / ar" not in SRC:
    raise SystemExit("FAIL: multiplication no longer rejects overflow where produced")

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

# Keep output statements after every generated cell has been installed.
output_at = next(i for i, line in enumerate(lines) if line.startswith("print of"))
outputs = lines[output_at:]
lines = lines[:output_at]

# These rows distinguish each structural layer: int-to-double entry, first-error
# propagation, production-time finite rejection, and the sole number formatter.
TARGETS = [
    ("=Z1*Z1", "2.5e+19"),
    ("=NA()/2", "#N/A"),
    ('=MOD("a",3)', "#VALUE!"),
    ("=IFERROR(POWER(10,400),7)", "7"),
    ("=IFERROR(1E300*1E10,7)", "7"),
    ("=ISERROR(POWER(10,400))", "TRUE"),
    ('=CONCATENATE(POWER(10,400),"x")', "#NUM!"),
    ('=(-1E-300*1E-300)&""', "0"),
    ('=LEN((-1E-300*1E-300)&"")', "1"),
    ("=SUM(9223372036854775807,1)", "9.223372036854776e+18"),
    ("=PRODUCT(100000,100000,100000,100000)", "1e+20"),
    ("=STDEV(1E200,-1E200)", "#NUM!"),
]
lines.append('sheet.set_cell of [s,"Z1","5000000000"]')
for ti, (tf, _) in enumerate(TARGETS):
    lines.append("sheet.set_cell of [s,%s,%s]" % (q("D%d" % (ti+1)), q(tf)))
# Move recalc and all output to the end, after target cells.
lines.remove("sheet.recalc of s")
lines += ["sheet.recalc of s"] + outputs
for ti in range(len(TARGETS)):
    lines.append('print of ("TARGET\t" + (sheet.display of [s,%s]))' % q("D%d" % (ti+1)))

with tempfile.TemporaryDirectory() as tmp:
    md = os.path.join(tmp, "eigs_modules", "sheet"); os.makedirs(md)
    for name in ("sheet.eigs", "pdf.eigs", "eigs.json"):
        shutil.copy(os.path.join(ROOT, name), os.path.join(md, name))
    app = os.path.join(tmp, "app.eigs")
    open(app, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    run = subprocess.run([EIGS, app], cwd=tmp, text=True, capture_output=True, timeout=60)
if run.returncode:
    raise SystemExit("FAIL: recalc raised\n" + run.stdout + run.stderr)
rows = [line.split("\t") for line in run.stdout.splitlines()
        if "\t" in line and not line.startswith(("CSV\t", "TARGET\t"))]
if len(rows) != len(ordered):
    raise SystemExit("FAIL: expected %d result rows, got %d" % (len(ordered), len(rows)))
for fn, row in zip(ordered, rows):
    if row != ["#NUM!", "7101"]:
        raise SystemExit("FAIL: %s displayed %r (expected #NUM!, catchable 7101)" % (fn, row))
target_rows = [line.split("\t", 1)[1] for line in run.stdout.splitlines()
               if line.startswith("TARGET\t")]
expected_targets = [want for _, want in TARGETS]
if target_rows != expected_targets:
    raise SystemExit("FAIL: evaluator boundary targets %r expected %r" %
                     (target_rows, expected_targets))
print("PASS: examined == derived == %d dispatcher names; %d clauses" %
      (len(DERIVED_NAMES), len(CLAUSE_NAMES)))
print("PASS: %d/%d evaluator boundary targets" %
      (len(target_rows), len(TARGETS)))

csv_mark = run.stdout.find("CSV\t")
csv_rows = (run.stdout[csv_mark + 4:].splitlines()[:len(ordered)]
            if csv_mark >= 0 else [])
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
    print("SKIP: LibreOffice unavailable; external half NOT RUN")
    raise SystemExit(2)
