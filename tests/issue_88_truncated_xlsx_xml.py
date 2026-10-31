#!/usr/bin/env python3
"""Issue #88: truncated XLSX XML must fail atomically, never hang."""
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

EIGS = os.environ.get("EIGENSCRIPT", "eigenscript")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def write_xlsx(path, worksheet, shared=None):
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("xl/worksheets/sheet1.xml", worksheet)
        if shared is not None:
            archive.writestr("xl/sharedStrings.xml", shared)


def run_case(tmp, filename):
    source = (
        "import sheet\n"
        "s is sheet.new_sheet of null\n"
        'sheet.set_cell of [s, "A1", "keep"]\n'
        "try:\n"
        "    sheet.from_xlsx of [s, \"%s\"]\n"
        '    print of "NOT_CAUGHT"\n'
        "catch err:\n"
        '    print of ("CAUGHT " + (json_encode of err))\n'
        'print of ("AFTER " + (sheet.display of [s, "A1"]))\n' % filename
    )
    app = os.path.join(tmp, "case.eigs")
    with open(app, "w") as stream:
        stream.write(source)
    return subprocess.run(
        [EIGS, app], cwd=tmp, text=True, capture_output=True, timeout=10
    )


def imported(output, expected):
    """Whether a valid control imported and left A1 at expected display text."""
    return "NOT_CAUGHT" in output and "AFTER " + expected + "\n" in output


def main():
    failures = 0
    with tempfile.TemporaryDirectory(prefix="eigen-sheet-issue-88-") as tmp:
        module = os.path.join(tmp, "eigs_modules", "sheet")
        os.makedirs(module)
        shutil.copy(os.path.join(ROOT, "sheet.eigs"), module)
        shutil.copy(os.path.join(ROOT, "eigs.json"), module)

        good_ws = ('<worksheet><sheetData><row><c r="A1" t="n"><v>1</v></c>'
                   '</row></sheetData></worksheet>')
        fixtures = {
            "truncated-sheet.xlsx": (
                '<worksheet><sheetData><row><c r="A1" t="n"><v>1</v></row>'
                '</sheetData></worksheet>', None
            ),
            "truncated-shared-strings.xlsx": (
                '<worksheet><sheetData><row><c r="A1" t="s"><v>0</v></c>'
                '</row></sheetData></worksheet>',
                '<sst><si><t>shared</si></sst>'
            ),
            "truncated-cell-tag.xlsx": (
                '<worksheet><sheetData><row><c r="A1"', None
            ),
            "truncated-cell-attribute.xlsx": (
                '<worksheet><sheetData><row><c r="A1><v>1</v></c></row>'
                '</sheetData></worksheet>', None
            ),
            "truncated-cell-value.xlsx": (
                '<worksheet><sheetData><row><c r="A1"><v>1</c></row>'
                '</sheetData></worksheet>', None
            ),
            "truncated-shared-item.xlsx": (
                good_ws, '<sst><si><t>shared</t></sst>'
            ),
            "truncated-formula.xlsx": (
                '<worksheet><sheetData><row><c r="A1"><f>1+1</c></row>'
                '</sheetData></worksheet>', None
            ),
            "truncated-inline-string.xlsx": (
                '<worksheet><sheetData><row><c r="A1" t="inlineStr"><is>'
                '</c></row></sheetData></worksheet>', None
            ),
        }
        valid_controls = {
            "self-closing-shared-item.xlsx": (
                '<worksheet><sheetData><row><c r="A1" t="s"><v>0</v></c>'
                '</row></sheetData></worksheet>', '<sst><si/></sst>', ""
            ),
            "self-closing-attributed-shared-item.xlsx": (
                '<worksheet><sheetData><row><c r="A1" t="s"><v>0</v></c>'
                '</row></sheetData></worksheet>',
                '<sst><si xml:space="preserve"/></sst>', ""
            ),
            "self-closing-text.xlsx": (
                '<worksheet><sheetData><row><c r="A1" t="s"><v>0</v></c>'
                '</row></sheetData></worksheet>', '<sst><si><t/></si></sst>', ""
            ),
            "self-closing-cell.xlsx": (
                '<worksheet><sheetData><row><c r="A1"/></row>'
                '</sheetData></worksheet>', None, "keep"
            ),
            "self-closing-value.xlsx": (
                '<worksheet><sheetData><row><c r="A1"><v/></c></row>'
                '</sheetData></worksheet>', None, ""
            ),
            "self-closing-formula.xlsx": (
                '<worksheet><sheetData><row><c r="A1"><f/><v>2</v></c>'
                '</row></sheetData></worksheet>', None, "2"
            ),
            "self-closing-inline-string.xlsx": (
                '<worksheet><sheetData><row><c r="A1" t="inlineStr"><is/>'
                '</c></row></sheetData></worksheet>', None, ""
            ),
        }
        if len(fixtures) != len(set(fixtures)):
            print("FAIL: duplicate fixture keys")
            return 1

        write_xlsx(os.path.join(tmp, "good.xlsx"), good_ws)
        good = run_case(tmp, "good.xlsx")
        if good.returncode or "NOT_CAUGHT" not in good.stdout or "AFTER 1" not in good.stdout:
            failures += 1
            print("FAIL: clean control did not import: %r" % (good.stdout + good.stderr))
        else:
            print("PASS: clean worksheet control imports")

        for name, (worksheet, shared, expected) in valid_controls.items():
            write_xlsx(os.path.join(tmp, name), worksheet, shared)
            result = run_case(tmp, name)
            output = result.stdout + result.stderr
            if result.returncode or not imported(output, expected) or "CAUGHT " in output:
                failures += 1
                print("FAIL: %s valid self-closing XML did not import: %r" %
                      (name, output))
            else:
                print("PASS: %s valid self-closing XML imports" % name)

        for name, (worksheet, shared) in fixtures.items():
            write_xlsx(os.path.join(tmp, name), worksheet, shared)
            try:
                result = run_case(tmp, name)
            except subprocess.TimeoutExpired:
                failures += 1
                print("FAIL: %s hung past 10-second timeout" % name)
                continue
            output = result.stdout + result.stderr
            if (result.returncode or "CAUGHT " not in output or name not in output
                    or "AFTER keep" not in output or "NOT_CAUGHT" in output):
                failures += 1
                print("FAIL: %s was not rejected atomically: %r" % (name, output))
            else:
                print("PASS: %s rejected atomically with filename" % name)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
