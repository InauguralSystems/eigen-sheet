#!/usr/bin/env python3
"""Conditional-format differential oracle: effective_style vs a Python reference.

A conditional format makes a cell's appearance a function of its value. We set
rules on cells, give them values, and read back effective_style's background
(the first matching rule's style, over any base), comparing against a Python
reimplementation of the same matching (comparisons, between, contains). Pure
Python — the render path (draw_grid uses effective_style) is covered by the
style oracle.
"""
import os, subprocess, sys, tempfile, shutil

EIGS = os.environ.get("EIGENSCRIPT", "eigenscript")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GREEN, RED, BLUE = [40, 160, 40], [160, 40, 40], [40, 40, 160]
# a hi/lo rule set reused across cases
HILO = [{"op": ">", "value": 50, "style": {"bg": GREEN}},
        {"op": "<=", "value": 50, "style": {"bg": RED}}]
# (cell raw value, rules, base_style_or_None)
CASES = [
    ("60", HILO, None),
    ("50", HILO, None),
    ("40", HILO, None),
    ("100", [{"op": "between", "min": 0, "max": 99, "style": {"bg": BLUE}}], None),
    ("50", [{"op": "between", "min": 0, "max": 99, "style": {"bg": BLUE}}], None),
    ("hello", [{"op": "contains", "value": "ell", "style": {"bg": GREEN}}], None),
    ("world", [{"op": "contains", "value": "ell", "style": {"bg": GREEN}}], None),
    ("5", [{"op": "=", "value": 5, "style": {"bg": RED}}], None),
    # base style, no matching conditional -> base bg shows through
    ("10", [{"op": ">", "value": 50, "style": {"bg": GREEN}}], {"bg": BLUE}),
    # conditional overrides base bg
    ("60", [{"op": ">", "value": 50, "style": {"bg": GREEN}}], {"bg": BLUE}),
]


def eigs_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def lit(v):
    if isinstance(v, list):
        return "[" + ", ".join(lit(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{" + ", ".join("%s: %s" % (eigs_str(k), lit(x)) for k, x in v.items()) + "}"
    if isinstance(v, str):
        return eigs_str(v)
    return str(v)


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


def num(x):
    try:
        return float(x)
    except (ValueError, TypeError):
        return None


def cmp_sign(l, r):
    ln, rn = num(l), num(r)
    if ln is not None and rn is not None:
        return (ln > rn) - (ln < rn)
    if ln is None and rn is None:
        a, b = str(l).lower(), str(r).lower()
        return (a > b) - (a < b)
    return -1 if ln is not None else 1


def match(val, rule):
    op = rule["op"]
    if op == "between":
        return cmp_sign(val, rule["min"]) >= 0 and cmp_sign(val, rule["max"]) <= 0
    if op == "contains":
        return str(rule["value"]).lower() in str(val).lower()
    c = cmp_sign(val, rule["value"])
    return {">": c > 0, "<": c < 0, ">=": c >= 0, "<=": c <= 0, "=": c == 0, "<>": c != 0}[op]


def py_bg(raw, rules, base):
    val = num(raw) if num(raw) is not None else raw
    for rule in rules:
        if match(val, rule):
            return rule["style"].get("bg", base.get("bg") if base else None)
    return base.get("bg") if base else None


def main():
    lines = ["import sheet"]
    for i, (raw, rules, base) in enumerate(CASES):
        lines.append("s%d is sheet.new_sheet of null" % i)
        lines.append("sheet.set_cell of [s%d, %s, %s]" % (i, eigs_str("A1"), eigs_str(raw)))
        if base:
            lines.append("sheet.set_style of [s%d, %s, %s]" % (i, eigs_str("A1"), lit(base)))
        lines.append("sheet.set_conditional of [s%d, %s, %s]" % (i, eigs_str("A1"), lit(rules)))
        lines.append("sheet.recalc of s%d" % i)
        lines.append("es%d is sheet.effective_style of [s%d, %s]" % (i, i, eigs_str("A1")))
        lines.append('if es%d != null and (has_key of [es%d, "bg"]) == 1:' % (i, i))
        lines.append('    print of (str of es%d.bg)' % i)
        lines.append("else:")
        lines.append('    print of "none"')
    out = run_eigs("\n".join(lines) + "\n").splitlines()

    failures = 0
    for i, (raw, rules, base) in enumerate(CASES):
        mine = out[i]
        exp = py_bg(raw, rules, base)
        expected = "none" if exp is None else str(exp)
        if mine.replace(" ", "") != expected.replace(" ", ""):
            failures += 1
            print("FAIL %-8r eigen=%s python=%s" % (raw, mine, expected))
        else:
            print("PASS %-8r -> %s" % (raw, expected))
    if failures:
        print("\n%d conditional-format divergence(s)" % failures); sys.exit(1)
    print("\neigen-sheet conditional formatting matches the Python reference")


if __name__ == "__main__":
    main()
