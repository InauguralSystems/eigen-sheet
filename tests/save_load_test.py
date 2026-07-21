#!/usr/bin/env python3
"""Native save/load round-trip oracle.

save() writes the whole sheet (raw cell contents + named ranges + number
formats) as JSON; load() reads it into a fresh sheet and recomputes. This
checks two things: (1) the file is valid JSON (an independent reader — Python's
json — parses it and sees the cells), and (2) a save -> load round-trip
reconstructs every displayed value identically, including formulas, a named
range, a number format, and text with delimiters/quotes. Pure Python.
"""
import json, os, subprocess, sys, tempfile, shutil

EIGS = os.environ.get("EIGENSCRIPT", "eigenscript")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# addr -> raw content
GRID = {
    "A1": "5", "A2": "3", "A3": "=A1+A2",
    "B1": "=SUM(revenue)", "B2": "=A1*taxrate",
    "C1": 'hi, "world"', "C2": "plain text",
    "D1": "3.14159",
}
NAMES = {"revenue": "A1:A3", "taxrate": "0.5"}
FORMATS = {"A1": "#,##0.00", "D1": "0.00%"}
STYLES = {"A1": '{"bg": [180,40,40], "color": [255,255,200], "align": "right", "bold": 1}'}


def eigs_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def main():
    tmp = tempfile.mkdtemp()
    try:
        md = os.path.join(tmp, "eigs_modules", "sheet"); os.makedirs(md)
        shutil.copy(os.path.join(REPO, "sheet.eigs"), os.path.join(md, "sheet.eigs"))
        shutil.copy(os.path.join(REPO, "eigs.json"), os.path.join(md, "eigs.json"))
        path = os.path.join(tmp, "s.json")

        body = "\n".join("sheet.set_cell of [s, %s, %s]" % (eigs_str(a), eigs_str(r)) for a, r in GRID.items())
        body += "\n" + "\n".join("sheet.define_name of [s, %s, %s]" % (eigs_str(n), eigs_str(d)) for n, d in NAMES.items())
        body += "\n" + "\n".join("sheet.set_format of [s, %s, %s]" % (eigs_str(a), eigs_str(c)) for a, c in FORMATS.items())
        body += "\n" + "\n".join("sheet.set_style of [s, %s, %s]" % (eigs_str(a), lit) for a, lit in STYLES.items())
        orig = "\n".join('print of ("O\\t" + %s + "\\t" + (sheet.display of [s, %s]))' % (eigs_str(a), eigs_str(a)) for a in GRID)
        load = "\n".join('print of ("L\\t" + %s + "\\t" + (sheet.display of [s2, %s]))' % (eigs_str(a), eigs_str(a)) for a in GRID)
        prog = (
            "import sheet\ns is sheet.new_sheet of null\n" + body + "\nsheet.recalc of s\n" +
            "sheet.save of [s, %s]\n" % eigs_str(path) + orig + "\n"
            "s2 is sheet.new_sheet of null\nsheet.load of [s2, %s]\n" % eigs_str(path) + load + "\n")
        app = os.path.join(tmp, "app.eigs"); open(app, "w").write(prog)
        r = subprocess.run([EIGS, app], cwd=tmp, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            print("FAIL: eigenscript errored\n" + r.stdout + r.stderr); sys.exit(1)

        orig_d, load_d = {}, {}
        for line in r.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) == 3 and parts[0] == "O":
                orig_d[parts[1]] = parts[2]
            elif len(parts) == 3 and parts[0] == "L":
                load_d[parts[1]] = parts[2]

        failures = 0
        # (1) valid JSON, independently parsed
        try:
            data = json.load(open(path))
            assert set(data["cells"]) == set(GRID), "cells mismatch"
            assert data["names"], "names missing"
            assert data["formats"], "formats missing"
            assert data["styles"].get("A1", {}).get("bg") == [180, 40, 40], "style not saved"
            print("PASS file is valid JSON with all %d cells + names + formats + styles" % len(GRID))
        except Exception as e:
            failures += 1
            print("FAIL JSON validity: %r" % e)
        # (2) round-trip: every displayed value identical
        for a in sorted(GRID):
            if orig_d.get(a) != load_d.get(a):
                failures += 1
                print("FAIL round-trip %-3s orig=%r loaded=%r" % (a, orig_d.get(a), load_d.get(a)))
        if not failures:
            print("PASS save -> load reconstructs every value (%d cells, incl. named range + format)" % len(GRID))
        if failures:
            sys.exit(1)
        print("\nnative save/load round-trips identically")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
