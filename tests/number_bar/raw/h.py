#!/usr/bin/env python3
"""Harness: run cells through eigen-sheet (several tree/runtime combos, one process per tested cell)
and through LibreOffice (one xlsx). Usage: h.py cases.json [--no-calc] [--combos a,b,c]"""
import csv, glob, json, os, re, shutil, subprocess, sys, tempfile
D = "REVIEW_DIR"
NEW = "NEW_RUNTIME_BINARY"
OLD = "OLD_RUNTIME_BINARY"
COMBOS = {"tree3+NEW": (D + "/tree3", NEW), "tree2+NEW": (D + "/tree2", NEW), "tree+NEW": (D + "/tree", NEW), "before+OLD": (D + "/tree-before", OLD)}
XLFN = ("TEXTJOIN", "XOR", "IFNA", "IFS", "SWITCH", "XLOOKUP")
def q(s): return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
def ooxml(f):
    for n in XLFN: f = re.sub(r"\b" + n + r"\(", "_xlfn." + n + "(", f)
    return f
def eig_run(tree, rt, base, addr, f, extra):
    tmp = tempfile.mkdtemp(dir=D + "/scratch/pass3/t")
    try:
        md = os.path.join(tmp, "eigs_modules", "sheet"); os.makedirs(md)
        for n in ("sheet.eigs", "pdf.eigs", "eigs.json"): shutil.copy(os.path.join(tree, n), md)
        L = ["import sheet", "s is sheet.new_sheet of null"]
        for a, r in base.items(): L.append("sheet.set_cell of [s,%s,%s]" % (q(a), q(r)))
        L.append("sheet.set_cell of [s,%s,%s]" % (q(addr), q(f)))
        L.append("sheet.recalc of s")
        L.append('print of ("DISP\\t" + (sheet.display of [s,%s]))' % q(addr))
        L += [x.replace("@A", q(addr)) for x in extra]
        open(os.path.join(tmp, "app.eigs"), "w").write("\n".join(L) + "\n")
        r = subprocess.run(["timeout", "30", rt, "app.eigs"], cwd=tmp, capture_output=True, text=True)
        if r.returncode != 0:
            err = [l for l in (r.stdout + r.stderr).strip().splitlines() if "DISP" not in l]
            return {"disp": "CRASH rc=%d %s" % (r.returncode, (err[0] if err else "")[-90:])}
        out = {}
        for line in r.stdout.splitlines():
            if "\t" in line:
                k, v = line.split("\t", 1); out[k.lower()] = v
        return out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
def eig_grid(tree, rt, base, fs):
    tmp = tempfile.mkdtemp(dir=D + "/scratch/pass3/t")
    try:
        md = os.path.join(tmp, "eigs_modules", "sheet"); os.makedirs(md)
        for n in ("sheet.eigs", "pdf.eigs", "eigs.json"): shutil.copy(os.path.join(tree, n), md)
        L = ["import sheet", "s is sheet.new_sheet of null"]
        for a, r in list(base.items()) + list(fs.items()): L.append("sheet.set_cell of [s,%s,%s]" % (q(a), q(r)))
        L.append("sheet.recalc of s")
        for a in fs: L.append('print of (%s + "\t" + (sheet.display of [s,%s]))' % (q(a), q(a)))
        open(os.path.join(tmp, "app.eigs"), "w").write("\n".join(L) + "\n")
        r = subprocess.run(["timeout", "120", rt, "app.eigs"], cwd=tmp, capture_output=True, text=True)
        if r.returncode != 0: return None
        out = {}
        for line in r.stdout.splitlines():
            if "\t" in line:
                k, v = line.split("\t", 1); out[k] = {"disp": v}
        return out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
def col2n(c):
    n = 0
    for ch in c: n = n * 26 + ord(ch) - 64
    return n
def calc(base, fs):
    import openpyxl
    tmp = tempfile.mkdtemp(dir=D + "/scratch/pass3/t")
    try:
        wb = openpyxl.Workbook(); ws = wb.active
        for a, r in list(base.items()) + list(fs.items()):
            if r.startswith("="): ws[a] = ooxml(r)
            else:
                try: ws[a] = float(r) if not re.fullmatch(r"-?\d+", r) else int(r)
                except ValueError: ws[a] = r
        wb.calculation.fullCalcOnLoad = True
        x = os.path.join(tmp, "g.xlsx"); wb.save(x)
        subprocess.run(["timeout", "200", "soffice", "--headless", "--norestore", "--nolockcheck",
                        "-env:UserInstallation=file://" + tmp + "/prof", "--convert-to", "csv", "--outdir", tmp, x],
                       capture_output=True)
        g = list(csv.reader(open(glob.glob(tmp + "/*.csv")[0], newline="")))
        out = {}
        for a in fs:
            m = re.match(r"([A-Z]+)(\d+)", a)
            try: out[a] = g[int(m.group(2)) - 1][col2n(m.group(1)) - 1]
            except IndexError: out[a] = "<blank>"
        return out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
def main():
    spec = json.load(open(sys.argv[1]))
    combos = [c for c in (sys.argv[sys.argv.index("--combos") + 1].split(",") if "--combos" in sys.argv else COMBOS)]
    base, fs, extra = spec.get("base", {}), spec["f"], spec.get("extra", [])
    lo = {} if "--no-calc" in sys.argv else calc(base, fs)
    hdr = ["addr", "formula", "Calc"] + combos
    print("\t".join(hdr))
    nrow = 0
    res = {}
    grids = {}
    if not extra:
        for c in combos:
            grids[c] = eig_grid(COMBOS[c][0], COMBOS[c][1], base, fs)
            print("# %s grid run: %s" % (c, "ok" if grids[c] is not None else "CRASHED -> per-cell runs"))
    for a, f in fs.items():
        row = [a, f, lo.get(a, "-")]
        res[a] = {"Calc": lo.get(a)}
        for c in combos:
            o = grids[c][a] if grids.get(c) and a in grids[c] else eig_run(COMBOS[c][0], COMBOS[c][1], base, a, f, extra)
            res[a][c] = o
            row.append(" | ".join("%s=%s" % (k, v) if k != "disp" else v for k, v in o.items()))
        print("\t".join(row)); nrow += 1
    print("ROWS EXAMINED: %d" % nrow)
    json.dump(res, open(sys.argv[1] + ".out.json", "w"), indent=1)
main()
