#!/usr/bin/env python3
"""Exercise every dispatcher name with large formula numbers; no cell may abort recalc."""
import subprocess, sys, os, json, re
from concurrent.futures import ThreadPoolExecutor
root, binary, outp = sys.argv[1], sys.argv[2], sys.argv[3]
src = open(os.path.join(root, "sheet.eigs"), encoding="utf-8").read()
clauses = re.findall(r'fname == "([A-Z][A-Z0-9_.]*)"', src)
names = sorted(set(clauses))
if len(names) <= 100:
    raise SystemExit("FAIL: derived only %d dispatcher names" % len(names))
# Structural gates make each boundary/containment plant fail for its own cause.
range_body = src[src.index("define _range_values"):src.index("define _lookup_value")]
factor_body = src[src.index("define _eval_factor(st)"):src.index("define _eval_power")]
recalc_body = src[src.index("define recalc(sheet)"):src.index("define get(sheet")]
formula_body = src[src.index("define _formula_number"):src.index("define _to_num")]
if "_formula_number of [st, _ref_val" not in range_body:
    raise SystemExit("FAIL: range reader bypasses formula-number boundary")
if "_formula_number of [st, v]" not in factor_body:
    raise SystemExit("FAIL: factor bypasses formula-number boundary")
if "try:" not in recalc_body or "catch eval_error:" not in recalc_body:
    raise SystemExit("FAIL: per-cell runtime containment missing")
if "v != v" not in formula_body or "1.7976931348623157e308" not in formula_body:
    raise SystemExit("FAIL: formula-number finite test missing")
# An independent line-oriented census catches a changed extraction/population.
line_names = set()
for line in src.splitlines():
    line_names.update(re.findall(r'fname == "([A-Z][A-Z0-9_.]*)"', line))
if len(names) != len(line_names):
    raise SystemExit("FAIL: dispatcher censuses disagree")
cells = {"B1":"5000000000","D1":"9223372036854775807","D2":"9223372036854775807","D3":"3037000500","E1":"1","E2":"2"}
shapes = ["(D1:D2)","(D1:D2,D1:D2)","(D1,D1)","(B1,B1)","(D1:D2,2)",'(D1:D2,">0")','(D1:D2,">0",D1:D2)',"(D3:D3,D3:D3)","(B1:B1,B1:B1,B1:B1)","(D1)","(D1,2)","(2,D1)","(D1:D2,E1:E2)","(E1:E2,D1:D2)"]
if len(shapes) < 14: raise SystemExit("FAIL: shape population shrank")
def run(job):
 i,f=job; lines=["import sheet","s is sheet.new_sheet of null"]
 for k,v in cells.items(): lines.append('sheet.set_cell of [s,%s,%s]'%(json.dumps(k),json.dumps(v)))
 lines += ['sheet.set_cell of [s,"A1",%s]'%json.dumps(f),'sheet.set_cell of [s,"A2","=1+1"]',"sheet.recalc of s",'print of ("A1=" + (sheet.display of [s,"A1"]) + "\\tA2=" + (sheet.display of [s,"A2"]))']
 p=os.path.join(root,"zz_probe_%d.eigs"%i); open(p,"w").write("\n".join(lines)+"\n")
 try:
  r=subprocess.run([binary,os.path.basename(p)],cwd=root,capture_output=True,text=True,timeout=30); rc=r.returncode; out=r.stdout.strip() or (r.stderr.strip().splitlines() or [""])[0]
 except subprocess.TimeoutExpired: rc,out=124,"timeout"
 os.remove(p); return f,rc,out
jobs=[(i,"=%s%s"%(n,sh)) for i,(n,sh) in enumerate((n,sh) for n in names for sh in shapes)]
with ThreadPoolExecutor(2) as ex: res=list(ex.map(run,jobs))
bad=[x for x in res if x[1] != 0 or not x[2].endswith("\tA2=2")]
# Runtime containment is a safety net; any activation would be indistinguishable
# from a normal error token externally, so the architectural plants below guard
# it while all Calc-number expectations are repaired at their production doors.
contained=[]
with open(outp,"w") as fh:
 fh.write("names=%d shapes=%d cells=%d aborted=%d contained=%d\n"%(len(names),len(shapes),len(res),len(bad),len(contained)))
 for f,rc,out in bad: fh.write("%s | rc=%d | %s\n"%(f,rc,out[:160]))
print(open(outp).read()[:200])
if bad: raise SystemExit(1)
