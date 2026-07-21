#!/usr/bin/env python3
"""Data-validation differential oracle: eigen-sheet's is_valid vs Python.

Validation is deterministic predicate matching. We set rules on cells and check
a matrix of candidate values with is_valid, comparing accept/reject against a
Python reimplementation of the same rules (list membership with numeric/
case-insensitive-text equality, whole-number range, decimal range, text-length
range, and a comparison). Pure Python.
"""
import os, subprocess, sys, tempfile, shutil

EIGS = os.environ.get("EIGENSCRIPT", "eigenscript")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RULES = {
    "A1": {"type": "whole", "min": 1, "max": 10},
    "B1": {"type": "list", "values": ["red", "green", "blue"]},
    "C1": {"type": "textlen", "min": 2, "max": 5},
    "D1": {"type": "cmp", "op": ">", "value": 100},
    "E1": {"type": "decimal", "min": 0, "max": 1},
    "F1": {"type": "list", "values": [10, 20, 30]},
}
# (addr, value) candidates
CASES = [
    ("A1", 5), ("A1", 11), ("A1", 2.5), ("A1", 0), ("A1", 10),
    ("B1", "green"), ("B1", "GREEN"), ("B1", "yellow"), ("B1", "Red"),
    ("C1", "ab"), ("C1", "a"), ("C1", "toolong"), ("C1", "hello"),
    ("D1", 150), ("D1", 50), ("D1", 100),
    ("E1", 0.5), ("E1", 1), ("E1", 1.5), ("E1", -0.1),
    ("F1", 20), ("F1", 25),
    ("Z9", "anything"),   # no rule -> always valid
]


def eigs_val(v):
    return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"' if isinstance(v, str) else str(v)


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


def rule_lit(rule):
    parts = []
    for k, v in rule.items():
        if isinstance(v, list):
            vv = "[" + ", ".join(eigs_val(x) for x in v) + "]"
        else:
            vv = eigs_val(v)
        parts.append('%s: %s' % (eigs_val(k), vv))
    return "{" + ", ".join(parts) + "}"


def num(x):
    return float(x) if isinstance(x, (int, float)) else None


def cmp_eq(a, b):
    an, bn = num(a), num(b)
    if an is not None and bn is not None:
        return an == bn
    if an is None and bn is None:
        return str(a).lower() == str(b).lower()
    return False


def py_valid(rule, value):
    t = rule["type"]
    if t == "list":
        return any(cmp_eq(value, v) for v in rule["values"])
    if t == "whole":
        if not isinstance(value, (int, float)):
            return False
        if value != int(value):
            return False
        return rule["min"] <= value <= rule["max"]
    if t == "decimal":
        if not isinstance(value, (int, float)):
            return False
        return rule["min"] <= value <= rule["max"]
    if t == "textlen":
        n = len(str(value))
        return rule["min"] <= n <= rule["max"]
    if t == "cmp":
        c = (value > rule["value"]) - (value < rule["value"])
        return {">": c > 0, "<": c < 0, ">=": c >= 0, "<=": c <= 0, "=": c == 0, "<>": c != 0}[rule["op"]]
    return True


def main():
    sets = "\n".join("sheet.set_validation of [s, %s, %s]" % (eigs_val(a), rule_lit(r)) for a, r in RULES.items())
    calls = "\n".join('print of (str of (sheet.is_valid of [s, %s, %s]))' % (eigs_val(a), eigs_val(v)) for a, v in CASES)
    prog = "import sheet\ns is sheet.new_sheet of null\n" + sets + "\n" + calls + "\n"
    out = [l for l in run_eigs(prog).splitlines() if l.strip() in ("0", "1")]

    failures = 0
    for i, (a, v) in enumerate(CASES):
        mine = out[i] == "1"
        ref = py_valid(RULES[a], v) if a in RULES else True
        if mine != ref:
            failures += 1
            print("FAIL %-3s %-10r eigen=%s python=%s" % (a, v, mine, ref))
        else:
            print("PASS %-3s %-10r -> %s" % (a, v, "valid" if ref else "reject"))
    if failures:
        print("\n%d validation divergence(s) from Python" % failures); sys.exit(1)
    print("\neigen-sheet data validation matches the Python reference")


if __name__ == "__main__":
    main()
