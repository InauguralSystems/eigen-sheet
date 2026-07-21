#!/usr/bin/env python3
"""Find/replace differential oracle: eigen-sheet vs Python string ops.

Literal find/replace is deterministic and has a canonical reference in every
standard library. So we don't assert the result — Python does. We build a grid,
run find_cells / replace_cells, and compare against Python's own substring
search and literal replace (with the same case-sensitivity and "emit original
text for non-matches" rule). Pure Python + the plain eigenscript build.
"""
import os, subprocess, sys, tempfile, shutil

EIGS = os.environ.get("EIGENSCRIPT", "eigenscript")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# addr -> raw content
GRID = {
    "A1": "cat",   "B1": "concatenate", "C1": "DOG",
    "A2": "Cat food", "B2": "=A1", "C2": "catalog",
    "A3": "dog",   "B3": "scatter",  "C3": "",
}
FIND = [("cat", 1), ("cat", 0), ("DOG", 1), ("o", 0)]
REPLACE = ("cat", "CAT", 1)   # needle, replacement, case-sensitive


def col_num(letters):
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n


def rowmajor(addr):
    import re
    m = re.match(r"([A-Z]+)(\d+)", addr)
    return int(m.group(2)) * 16384 + col_num(m.group(1))


def eigs_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def run_eigs(prog):
    tmp = tempfile.mkdtemp()
    try:
        md = os.path.join(tmp, "eigs_modules", "sheet"); os.makedirs(md)
        shutil.copy(os.path.join(REPO, "sheet.eigs"), os.path.join(md, "sheet.eigs"))
        shutil.copy(os.path.join(REPO, "eigs.json"), os.path.join(md, "eigs.json"))
        app = os.path.join(tmp, "app.eigs"); open(app, "w").write(prog)
        r = subprocess.run([EIGS, app], cwd=tmp, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise RuntimeError(r.stdout + r.stderr)
        return r.stdout
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def replace_lit(text, old, new, cs):
    if not old:
        return text
    hay = text if cs else text.lower()
    ndl = old if cs else old.lower()
    out, i, lo = [], 0, len(old)
    while i < len(text):
        if hay[i:i + lo] == ndl:
            out.append(new); i += lo
        else:
            out.append(text[i]); i += 1
    return "".join(out)


def contains(text, needle, cs):
    return (needle in text) if cs else (needle.lower() in text.lower())


def build_prog():
    sets = "\n".join("sheet.set_cell of [s, %s, %s]" % (eigs_str(a), eigs_str(raw))
                     for a, raw in GRID.items())
    lines = ["import sheet", "s is sheet.new_sheet of null", sets, "sheet.recalc of s"]
    for i, (needle, cs) in enumerate(FIND):
        lines.append('print of ("<F%d " + (str of (sheet.find_cells of [s, %s, %d])))'
                     % (i, eigs_str(needle), cs))
    n, rep, cs = REPLACE
    lines.append('cnt is sheet.replace_cells of [s, %s, %s, %d]' % (eigs_str(n), eigs_str(rep), cs))
    lines.append('print of ("<CNT " + (str of cnt))')
    for a in sorted(GRID, key=rowmajor):
        lines.append('print of ("<R %s=" + s.cells[%s])' % (a, eigs_str(a)))
    return "\n".join(lines) + "\n"


def main():
    out = run_eigs(build_prog())
    got = {}
    for line in out.splitlines():
        if line.startswith("<F"):
            got.setdefault("find", []).append(line[2:].split(" ", 1)[1] if " " in line[2:] else "")
        elif line.startswith("<CNT "):
            got["cnt"] = int(line[5:])
        elif line.startswith("<R "):
            k, v = line[3:].split("=", 1)
            got.setdefault("raw", {})[k] = v

    failures = 0
    # find checks — parse eigen's list literal ["A1", ...] into a Python list
    import ast
    for i, (needle, cs) in enumerate(FIND):
        mine = ast.literal_eval(got["find"][i])
        ref = sorted([a for a, raw in GRID.items() if contains(raw, needle, cs)], key=rowmajor)
        tag = "find %r cs=%d" % (needle, cs)
        if mine != ref:
            failures += 1; print("FAIL %-16s eigen=%r python=%r" % (tag, mine, ref))
        else:
            print("PASS %-16s -> %s" % (tag, ref))
    # replace checks
    n, rep, cs = REPLACE
    exp_raw = {a: replace_lit(raw, n, rep, cs) for a, raw in GRID.items()}
    exp_cnt = sum(1 for a in GRID if exp_raw[a] != GRID[a])
    if got["cnt"] != exp_cnt:
        failures += 1; print("FAIL replace count eigen=%d python=%d" % (got["cnt"], exp_cnt))
    else:
        print("PASS replace count -> %d" % exp_cnt)
    for a in sorted(GRID, key=rowmajor):
        if got["raw"].get(a, "") != exp_raw[a]:
            failures += 1
            print("FAIL raw %-3s eigen=%r python=%r" % (a, got["raw"].get(a), exp_raw[a]))
    if failures:
        print("\n%d find/replace divergence(s) from Python" % failures); sys.exit(1)
    print("\neigen-sheet find/replace matches Python string ops")


if __name__ == "__main__":
    main()
