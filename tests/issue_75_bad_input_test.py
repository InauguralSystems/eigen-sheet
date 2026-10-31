#!/usr/bin/env python3
"""Issue #75: corrupt imports must fail before changing a sheet."""
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

EIGS = os.environ.get("EIGENSCRIPT", "eigenscript")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def quoted(value):
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def run(source, tmp):
    app = os.path.join(tmp, "case.eigs")
    with open(app, "w") as stream:
        stream.write(source)
    return subprocess.run([EIGS, app], cwd=tmp, text=True, capture_output=True, timeout=30)


def main():
    tmp = tempfile.mkdtemp()
    failures = 0
    try:
        modules = os.path.join(tmp, "eigs_modules", "sheet")
        os.makedirs(modules)
        shutil.copy(os.path.join(REPO, "sheet.eigs"), modules)
        shutil.copy(os.path.join(REPO, "eigs.json"), modules)

        bad = {}
        bad["not.xlsx"] = b"a,b\n1,2\n"
        bad["rand.xlsx"] = bytes(range(256)) + b"x" * 44
        with zipfile.ZipFile(os.path.join(tmp, "noworksheet.xlsx"), "w") as archive:
            archive.writestr("hello.txt", "hi")

        with zipfile.ZipFile(os.path.join(tmp, "good.xlsx"), "w") as archive:
            archive.writestr("xl/worksheets/sheet1.xml",
                             '<worksheet><sheetData><row><c r="A1"><v>5</v></c></row></sheetData></worksheet>')
        good = open(os.path.join(tmp, "good.xlsx"), "rb").read()
        bad["trunc.xlsx"] = good[:len(good) // 2]
        for name, payload in bad.items():
            open(os.path.join(tmp, name), "wb").write(payload)

        # A syntactically located central-directory record whose declared name
        # crosses the archive boundary exercises the separate bounds check.
        overrun = bytearray(good)
        cd = overrun.find(b"PK\x01\x02")
        overrun[cd + 28:cd + 30] = (65535).to_bytes(2, "little")
        open(os.path.join(tmp, "overrun.xlsx"), "wb").write(overrun)

        for name in ("not.xlsx", "rand.xlsx", "trunc.xlsx", "noworksheet.xlsx", "overrun.xlsx"):
            result = run("import sheet\ns is sheet.new_sheet of null\nsheet.from_xlsx of [s, %s]\n" % quoted(name), tmp)
            output = result.stdout + result.stderr
            if result.returncode == 0 or name not in output:
                failures += 1
                print("FAIL: %s rc=%d output=%r" % (name, result.returncode, output))
            else:
                print("PASS: %s rejected with a filename-bearing error" % name)

        result = run('import sheet\ns is sheet.new_sheet of null\nsheet.from_xlsx of [s, "good.xlsx"]\nprint of (sheet.display of [s, "A1"])\n', tmp)
        if result.returncode or result.stdout.strip() != "5":
            failures += 1
            print("FAIL: good.xlsx rc=%d output=%r" % (result.returncode, result.stdout + result.stderr))
        else:
            print("PASS: good.xlsx imports A1=5")

        invalid = {"missing.json": '{"foo":1}', "list.json": '[1,2,3]', "cells.json": '{"cells":5}'}
        for name, payload in invalid.items():
            open(os.path.join(tmp, name), "w").write(payload)
            loud = run('import sheet\ns is sheet.new_sheet of null\nsheet.load of [s, %s]\n' % quoted(name), tmp)
            if loud.returncode == 0 or name not in loud.stdout + loud.stderr:
                failures += 1
                print("FAIL: %s did not raise a filename-bearing error" % name)
            source = ('import sheet\ns is sheet.new_sheet of null\nsheet.set_cell of [s, "A1", "keep"]\n'
                      'try:\n    sheet.load of [s, %s]\n    print of "NOT_CAUGHT"\n'
                      'catch err:\n    print of ("CAUGHT " + (json_encode of err))\n'
                      'print of ("AFTER " + (sheet.display of [s, "A1"]))\n') % quoted(name)
            result = run(source, tmp)
            output = result.stdout + result.stderr
            if result.returncode or "CAUGHT " not in output or name not in output or "AFTER keep" not in output or "NOT_CAUGHT" in output:
                failures += 1
                print("FAIL: %s validation/atomicity rc=%d output=%r" % (name, result.returncode, output))
            else:
                print("PASS: %s rejected before mutation" % name)

        open(os.path.join(tmp, "legacy.json"), "w").write('{"cells":{"A1":"old"}}')
        result = run('import sheet\ns is sheet.new_sheet of null\nsheet.load of [s, "legacy.json"]\nprint of ((sheet.display of [s, "A1"]) + " " + (str of (len of (keys of s.names))) + " " + (str of (len of (keys of s.formats))) + " " + (str of (len of (keys of s.styles))) + " " + (str of (len of s.conditionals)))\n', tmp)
        if result.returncode or result.stdout.strip() != "old 0 0 0 0":
            failures += 1
            print("FAIL: legacy defaults rc=%d output=%r" % (result.returncode, result.stdout + result.stderr))
        else:
            print("PASS: legacy save loads with empty optional collections")
        return failures
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
