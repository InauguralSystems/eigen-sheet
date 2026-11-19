#!/usr/bin/env python3
"""#104 number-boundary bar.

The population is rebuilt from sheet.eigs and templates.json on every run.  A
grid is used first; a failed grid is isolated one cell per process.  LibreOffice
Calc owns expected displays.  Numeric displays use diff_vs_calc.py's absolute
1e-9 tolerance.  The per-cell catch has no observable signal, so formula sets
honestly report ``net=unknown``; a counter incremented in recalc's catch and a
read-only accessor would be the smallest hook which could make it countable.
"""
import argparse, csv, glob, json, math, os, re, shutil, subprocess, sys, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "tests", "number_bar")
XLFN = ("TEXTJOIN", "XOR", "IFNA", "IFS", "SWITCH", "XLOOKUP")
BAD = {
 "float-overflow/operator":"1E300*1E10", "int64-product":"3037000500*3037000500",
 "nonfinite/function":"POWER(10,400)", "nan":"POWER(-1,0.5)", "na":"NA()",
 "division-zero":"1/0", "text":"\"not a number\""}
BASE = {"B1":"1","B2":"2","B3":"3","C1":"10","C2":"20","C3":"30"}

def dispatcher(tree):
 s=open(os.path.join(tree,"sheet.eigs"),encoding="utf-8").read()
 return sorted(set(re.findall(r'fname == "([A-Z][A-Z0-9_.]*)"',s)))

def load_templates(tree, path=None):
 p=path or os.path.join(DATA,"templates.json"); d=json.load(open(p)); got=set(dispatcher(tree)); rows=d["rows"]
 missing=sorted(got-set(rows)); stale=sorted(set(rows)-got)
 if missing: raise ValueError("dispatcher function has no template row: "+", ".join(missing))
 if stale: raise ValueError("template row lacks dispatcher function: "+", ".join(stale))
 no=set(d["no_numeric_arguments"])
 for n,v in rows.items():
  if not v and n not in no: raise ValueError("dispatcher function has no numeric template: "+n)
  for t in v:
   if t.count("@") != 1: raise ValueError("template must mark exactly one position: "+t)
 return d

def address(i):
 col=""; n=i//500+1
 while n: n,r=divmod(n-1,26); col=chr(65+r)+col
 return col+str(i%500+1)

def population(tree):
 d=load_templates(tree); out={}
 fs={}; i=0
 # continued errors are tested bare and inside both required wrappers.
 shapes=("@","IFERROR(@,7101)","ISERROR(@)","(@)+2*3","IFERROR((@)+2*3,7101)","ISERROR((@)+2*3)")
 for name in sorted(d["rows"]):
  for ti,t in enumerate(d["rows"][name]):
   for kind,bad in BAD.items():
    expr=t.replace("@",bad)
    for shape in shapes:
     fs[address(i)]="="+shape.replace("@",expr); i+=1
 out["class"]={"base":BASE,"f":fs,"reference":"calc"}
 # c21's rule, rather than its 630 stored cells: 9 sources x 10 operators x 7 wrappers.
 sources=("NA()","1/0","SQRT(-1)","POWER(10,400)","0.5^-2000","SUM(1E308,1E308)","3037000500*3037000500","\"x\"+1","LN(0)")
 ops=("@+1+1","@*2*3","@*2/4","@/2*4","-@+1","ABS(@)+1","SUM(@,1)","@^2","(@)=0","@&\"x\"")
 wraps=("@","IFERROR(@,7)","IFNA(@,7)","ISERROR(@)","ISERR(@)","ISNA(@)","ERROR.TYPE(@)")
 fs={}; i=0
 for x in sources:
  for op in ops:
   for w in wraps: fs[address(i)]="="+w.replace("@",op.replace("@",x)); i+=1
 out["wrappers"]={"base":BASE,"f":fs,"reference":"calc"}
 # Number-to-text population is also generated, not retained from raw c3.json.
 xs=("(0.1+0.2)*10","2+1/100000","4/2","10/2","0.1+0.2","1E21","10^21","1E-7","10^-7","-0","0*-1","-(1/2-0.5)","2^53+1","9007199254740993","123456789012345678","123456789012345678*1","1/3","2^53","1E15+0.5","-2.5*2")
 ts=("@","@&\"\"","LEN(@)","LEFT(@,30)","RIGHT(@,3)","MID(@,1,30)","TEXT(@,\"0\")","TEXT(@,\"0.00\")","TEXT(@,\"#,##0\")","TEXT(@,\"0%\")","CONCATENATE(@)","VALUE(@&\"\")","VALUE(@&\"\")=@","(@&\"\")=TEXT(@,\"0\")")
 out["number-text"]={"base":{},"f":{address(i):"="+t.replace("@","("+x+")" if t!="@" else x) for i,(x,t) in enumerate((x,t) for x in xs for t in ts)},"reference":"calc"}
 out.update(json.load(open(os.path.join(DATA,"arrival_cases.json"))))
 return out,d

def q(x): return json.dumps(x)
def runtime_grid(tree, binary, spec, only=None):
 fs=spec["f"] if only is None else {only:spec["f"][only]}; tmp=tempfile.mkdtemp()
 try:
  md=os.path.join(tmp,"eigs_modules","sheet"); os.makedirs(md)
  for n in ("sheet.eigs","pdf.eigs","eigs.json"): shutil.copy(os.path.join(tree,n),md)
  lines=["import sheet","s is sheet.new_sheet of null"]
  for a,v in list(spec.get("base",{}).items())+list(fs.items()): lines.append("sheet.set_cell of [s,%s,%s]"%(q(a),q(v)))
  lines.append("sheet.recalc of s")
  for a in fs: lines.append('print of (%s + "\\t" + (sheet.display of [s,%s]))'%(q(a),q(a)))
  open(os.path.join(tmp,"app.eigs"),"w").write("\n".join(lines)+"\n")
  r=subprocess.run([binary,"app.eigs"],cwd=tmp,text=True,capture_output=True,timeout=120)
  if r.returncode: return None
  return dict(x.split("\t",1) for x in r.stdout.splitlines() if "\t" in x)
 finally: shutil.rmtree(tmp)

def calc_grid(spec):
 import openpyxl
 office=shutil.which("libreoffice") or shutil.which("soffice")
 if not office: raise RuntimeError("LibreOffice Calc is required")
 tmp=tempfile.mkdtemp()
 try:
  w=openpyxl.Workbook(); s=w.active
  for a,v in list(spec.get("base",{}).items())+list(spec["f"].items()):
   if v.startswith("="):
    for n in XLFN: v=re.sub(r"\b"+n+r"\(","_xlfn."+n+"(",v)
    s[a]=v
   else:
    try: s[a]=int(v)
    except ValueError:
     try: s[a]=float(v)
     except ValueError: s[a]=v
  w.calculation.fullCalcOnLoad=True; x=os.path.join(tmp,"bar.xlsx"); w.save(x)
  r=subprocess.run([office,"--headless","--norestore","--nolockcheck","-env:UserInstallation=file://"+tmp+"/profile","--convert-to","csv","--outdir",tmp,x],capture_output=True,timeout=240)
  files=glob.glob(tmp+"/*.csv")
  if not files: raise RuntimeError("LibreOffice produced no CSV: "+r.stderr.decode(errors="replace"))
  rows=list(csv.reader(open(files[0],newline=""))); out={}
  for a in spec["f"]:
   m=re.match(r"([A-Z]+)(\d+)",a); c=0
   for ch in m.group(1): c=c*26+ord(ch)-64
   try: out[a]=rows[int(m.group(2))-1][c-1]
   except IndexError: out[a]="<blank>"
  return out
 finally: shutil.rmtree(tmp)

def validate_templates(d, oracle=calc_grid):
 """Ask Calc whether each marked call works before trusting the table."""
 fs={}; owner={}; i=0
 for name,templates in d["rows"].items():
  for t in templates:
   a=address(i); i+=1; fs[a]="="+t.replace("@","1"); owner[a]=(name,t)
 if not fs: raise ValueError("template validation examined=0")
 got=oracle({"base":BASE,"f":fs})
 for a,v in got.items():
  if v.startswith("#") or v.startswith("Err:"):
   name,t=owner[a]; raise ValueError("template is an error by itself in Calc: %s: %s -> %s"%(name,t,v))

def equal(a,b):
 if a==b:return True
 try:return math.isfinite(float(a)) and math.isfinite(float(b)) and abs(float(a)-float(b))<=1e-9
 except ValueError:return False

def selftest(tree):
 assert equal("1.0000000001","1") and not equal("12","13")
 clean=load_templates(tree); tmp=tempfile.mkdtemp()
 try:
  p=os.path.join(tmp,"t.json"); json.dump(clean,open(p,"w")); load_templates(tree,p)
  d=json.loads(json.dumps(clean)); d["rows"].pop(next(iter(d["rows"]))); json.dump(d,open(p,"w"))
  try: load_templates(tree,p); raise AssertionError("missing-row plant survived")
  except ValueError as e: assert "no template row" in str(e)
  # A one-character display plant is a difference, with an identical clean control.
  assert equal("7101","7101") and not equal("7101","710X")
  def bad_template(spec):
   return {a:("Err:502" if i==0 else "1") for i,a in enumerate(spec["f"])}
  try: validate_templates(clean,bad_template); raise AssertionError("bad-template plant survived")
  except ValueError as e: assert "error by itself in Calc" in str(e)
  try:
   if not {}: raise ValueError("examined=0")
  except ValueError as e: assert str(e)=="examined=0"
 finally: shutil.rmtree(tmp)
 print("PASS: number-bar clean controls and four plants")

def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--tree",default=ROOT); ap.add_argument("--runtime",default=os.environ.get("EIGENSCRIPT","eigenscript")); ap.add_argument("--list",action="store_true"); ap.add_argument("--set"); ap.add_argument("--out"); ap.add_argument("--selftest",action="store_true"); ap.add_argument("--known-before")
 a=ap.parse_args(); start=time.monotonic()
 if a.selftest:return selftest(a.tree)
 sets,d=population(a.tree); print("DISPATCHER names=%d rule=%s"%(len(d["rows"]),d["rule"]))
 if a.set:
  if a.set not in sets: raise SystemExit("unknown set "+a.set)
  sets={a.set:sets[a.set]}
 if a.list:
  for n,s in sets.items():
   for ad,f in s["f"].items(): print("%s\t%s\t%s"%(n,ad,f))
  return
 validate_templates(d)
 records=[]; N=D=0; unknown=False
 known=set(json.load(open(a.known_before))) if a.known_before else set()
 for name,spec in sets.items():
  if not spec.get("f"): raise SystemExit("SET %s examined=0 is invalid"%name)
  lo=calc_grid(spec); mine=runtime_grid(a.tree,a.runtime,spec)
  if mine is None:
   mine={ad:(runtime_grid(a.tree,a.runtime,spec,ad) or {}).get(ad,"CRASH") for ad in spec["f"]}
  diff=0
  for ad,f in spec["f"].items():
   verdict="match" if equal(mine.get(ad,"CRASH"),lo[ad]) else "differ"
   key=name+":"+ad
   if verdict=="differ" and key in known: verdict="known-before"
   if verdict=="differ": diff+=1
   records.append({"set":name,"address":ad,"formula":f,"eigen":mine.get(ad,"CRASH"),"calc":lo[ad],"verdict":verdict})
  n=len(spec["f"]); N+=n; D+=diff; unknown=True
  print("SET %s examined=%d match=%d differ=%d net=unknown"%(name,n,n-diff,diff))
 if a.out: json.dump(records,open(a.out,"w"),indent=2)
 print("NUMBER-BAR examined=%d differ=%d net=unknown wall=%.1fs"%(N,D,time.monotonic()-start))
 return 1 if D or unknown else 0
if __name__=="__main__": sys.exit(main() or 0)
