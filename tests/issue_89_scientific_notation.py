#!/usr/bin/env python3
"""Issue #89: scientific literals are numeric, including XLSX values."""
import os
import shutil
import subprocess
import tempfile
import zipfile

EIGS = os.environ.get("EIGENSCRIPT", "eigenscript")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(program, cwd):
    result = subprocess.run([EIGS, program], cwd=cwd, text=True,
                            capture_output=True, timeout=20)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result.stdout.strip().splitlines()


def workbook(path):
    parts = {
        "[Content_Types].xml": '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>',
        "_rels/.rels": '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        "xl/workbook.xml": '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheets><sheet name="Sheet1" sheetId="1"/></sheets></workbook>',
        "xl/worksheets/sheet1.xml": '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1"><v>1E+20</v></c><c r="B1"><f>SUM(A1:A2)</f><v>1E+20</v></c></row><row r="2"><c r="A2"><v>5</v></c><c r="B2"><f>A1*2</f><v>2E+20</v></c></row></sheetData></worksheet>',
    }
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in parts.items():
            archive.writestr(name, data)


def main():
    tmp = tempfile.mkdtemp()
    try:
        module = os.path.join(tmp, "eigs_modules", "sheet")
        os.makedirs(module)
        shutil.copy(os.path.join(ROOT, "sheet.eigs"), module)
        shutil.copy(os.path.join(ROOT, "eigs.json"), module)
        book = os.path.join(tmp, "scientific.xlsx")
        workbook(book)
        source = '''import sheet
s is sheet.new_sheet of null
vals is ["1E5", "1e+20", "2.5E-3", "-1E5", "E5", "1E", "1E+", "1e5e5"]
sheet.from_xlsx of [s, "scientific.xlsx"]
for i in range of (len of vals):
    a is "A" + (str of (i + 3))
    sheet.set_cell of [s, a, vals[i]]
    sheet.set_cell of [s, "B" + (str of (i + 3)), "=" + a + "*2"]
sheet.recalc of s
print of (sheet.display of [s, "B1"])
print of (sheet.display of [s, "B2"])
for i in range of (len of vals):
    print of (sheet.display of [s, "B" + (str of (i + 3))])
'''
        app = os.path.join(tmp, "test.eigs")
        open(app, "w", encoding="utf-8").write(source)
        got = run(app, tmp)
        expected = ["1e+20", "2e+20", "200000", "2e+20", "0.005", "-200000",
                    "#VALUE!", "#VALUE!", "#VALUE!", "#VALUE!"]
        if got != expected:
            print("FAIL: scientific notation", got, "!=", expected)
            raise SystemExit(1)
        print("PASS: typed and XLSX scientific notation; malformed forms rejected")
    finally:
        shutil.rmtree(tmp)


if __name__ == "__main__":
    main()
