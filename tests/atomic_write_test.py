#!/usr/bin/env python3
"""Crash-safety regression for the shared save/xlsx atomic-write helper."""
import os
import shutil
import subprocess
import sys
import tempfile

EIGS = os.environ.get("EIGENSCRIPT", "eigenscript")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def eigs_str(value):
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def main():
    tmp = tempfile.mkdtemp()
    try:
        modules = os.path.join(tmp, "eigs_modules", "sheet")
        os.makedirs(modules)
        shutil.copy(os.path.join(REPO, "sheet.eigs"), os.path.join(modules, "sheet.eigs"))
        # Add a test-only public seam inside the copied module; underscore names
        # are intentionally private to importers.
        with open(os.path.join(modules, "sheet.eigs"), "a", encoding="utf-8") as module:
            module.write("\ndefine atomic_write_test(path, data, hook) as:\n"
                         "    return _atomic_write of [path, data, false, hook]\n")
        shutil.copy(os.path.join(REPO, "eigs.json"), os.path.join(modules, "eigs.json"))
        target = os.path.join(tmp, "existing.eigs")
        control = os.path.join(tmp, "control.eigs")
        marker = os.path.join(tmp, "interrupt-ran")
        with open(target, "w", encoding="utf-8") as f:
            f.write("previous contents")
        with open(control, "w", encoding="utf-8") as f:
            f.write("old control")

        program = os.path.join(tmp, "app.eigs")
        with open(program, "w", encoding="utf-8") as f:
            f.write(
                "import sheet\n"
                "define interrupt(tmp_path) as:\n"
                "    write_text of [%s, tmp_path]\n"
                "    throw of \"forced interruption after tmp write\"\n"
                "sheet.atomic_write_test of [%s, \"new control\", null]\n"
                "caught is false\n"
                "try:\n"
                "    sheet.atomic_write_test of [%s, \"replacement contents\", interrupt]\n"
                "catch err:\n"
                "    caught is true\n"
                "print of caught\n" % (eigs_str(marker), eigs_str(control), eigs_str(target))
            )
        result = subprocess.run(
            [EIGS, program], cwd=tmp, capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            print("FAIL: EigenScript errored\n" + result.stdout + result.stderr)
            return 1
        with open(control, encoding="utf-8") as f:
            if f.read() != "new control":
                print("FAIL: clean control did not replace its target")
                return 1
        print("PASS: clean atomic replacement completes without the plant")
        if not os.path.exists(marker):
            print("FAIL: planted interruption was not reached")
            return 1
        if result.stdout.strip() != "true":
            print("FAIL: forced interruption was not caught: " + repr(result.stdout))
            return 1
        with open(target, encoding="utf-8") as f:
            actual = f.read()
        if actual != "previous contents":
            print("FAIL: interrupted atomic write changed target: " + repr(actual))
            return 1
        print("PASS: forced failure after tmp write leaves previous target intact")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
