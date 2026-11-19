#!/usr/bin/env python3
"""#104 number-boundary bar.

The population is rebuilt from sheet.eigs and templates.json on every run.  A
grid is run in chunks of 200 cells, one runtime process per chunk; a chunk that
crashes, times out or prints fewer cells than it was given is run again one
cell per process, and a cell whose own process fails is CRASH or TIMEOUT.

LibreOffice Calc decides every expected answer.  The tool writes each set into
an .xlsx twice: once with the number format 0.00000000000000E+00 (fifteen
significant digits, scientific) on every formula cell, and once with no format.
Both are converted to CSV by one headless Calc call with "save cell contents as
shown", so C, Calc's text for a cell, is a number in one spelling whatever Calc
would have auto-formatted; the unformatted copy is read only to learn whether
Calc's result is a logical (it shows TRUE or FALSE there).  A sentinel text in
the column after the last one used is written on every row and must come back:
a missing Calc row is the tool's error, never an expectation of blank.

THE RULE (the only tolerance in this tool).  For one cell, with C and this
spreadsheet's VALUE (sheet.get; a logical read as its number) and DISPLAY
(sheet.display):
- C is a number (it has the scientific form above).  The cell matches when the
  VALUE is a number that agrees with C to within one unit in the fifteenth
  significant digit of the larger of the two in size (both zero agree), and
  the DISPLAY reads as a decimal number that agrees with C by the same rule
  and, when the VALUE is whole and below 1e15 in size, is plain digits with an
  optional minus sign (no ".0" ending, no exponent).  When Calc's unformatted
  display is TRUE or FALSE the result is a logical: the VALUE must then be a
  logical of that value and the DISPLAY must be TRUE or FALSE as Calc's is.
  Anything else differs: an error, a text, #ERROR, a crash.
- C is an error (it starts with "#", or is Err:<digits>).  The cell matches
  when this spreadsheet's cell holds an error value other than #ERROR (its
  marker that the evaluation itself failed), and where C is one of Excel's
  seven names (#DIV/0! #N/A #NAME? #NULL! #NUM! #REF! #VALUE!) or another
  "#" name, the same name; where C is Err:<digits>, any of the seven.
- C is anything else (a text result, an empty result): the DISPLAY equals C
  exactly, and the cell holds no error.
A cell the per-cell net in recalc caught (sheet.net_caught) differs whatever
its text.

`differ` counts every cell that does not match; no cell is set apart from it.
`before` is information that subtracts nothing: of the cells that differ now,
those whose answer on this repository's main with the OLD runtime was the same
(the same number by the rule's agreement, the same error name, or the same
text).  tests/number_bar/before.json holds that run's answers, keyed by set,
formula text and the set's input cells, and is written whole by --write-before.

Exit 0 only when differ, net, crash and rule_differ are all 0 and every set
ran; 1 when any is not; 2 for the tool's own errors.
"""
import argparse, csv, json, os, re, shutil, subprocess, sys, tempfile, time
from decimal import Decimal, InvalidOperation

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "tests", "number_bar")
XLFN = ("TEXTJOIN", "XOR", "IFNA", "IFS", "SWITCH", "XLOOKUP")
BAD = {
 "float-overflow/operator":"1E300*1E10", "int64-product":"3037000500*3037000500",
 "nonfinite/function":"POWER(10,400)", "nan":"POWER(-1,0.5)", "na":"NA()",
 "division-zero":"1/0", "text":"\"not a number\""}
EXTRA_BAD = {"log-zero/function":"LN(0)", "underflow/function":"0.5^-2000",
 "sum-overflow/function":"SUM(1E308,1E308)"}
BASE = {"B1":"1","B2":"2","B3":"3","C1":"10","C2":"20","C3":"30","D1":"-1","D2":"2"}

def dispatcher(tree):
 s=open(os.path.join(tree,"sheet.eigs"),encoding="utf-8").read()
 return sorted(set(re.findall(r'fname == "([A-Z][A-Z0-9_.]*)"',s)))

def load_templates(tree, path=None):
 p=path or os.path.join(DATA,"templates.json"); d=json.load(open(p)); got=set(dispatcher(tree)); rows=d["rows"]
 missing=sorted(got-set(rows)); stale=sorted(set(rows)-got)
 if missing: raise ValueError("dispatcher function has no template row: "+", ".join(missing))
 if stale: raise ValueError("template row lacks dispatcher function: "+", ".join(stale))
 for n,v in rows.items():
  if not isinstance(v,dict) or set(v) - {"call","arguments","note"}: raise ValueError("invalid template row: "+n)
  if "(" not in v.get("call",""): raise ValueError("template call is not a call: "+n)
  if any(x not in ("number","text","range","criterion","logical") for x in v.get("arguments",[])):
   raise ValueError("invalid argument kind: "+n)
  if len(split_call(v["call"])) != len(v.get("arguments",[])): raise ValueError("argument labels do not match call: "+n)
 return d

def split_call(call):
 """Split the outer call's arguments without confusing nested calls or strings."""
 body=call[call.find("(")+1:-1]
 if not body:return []
 out=[]; start=0; depth=0; quoted=False
 for i,ch in enumerate(body):
  if ch=='"': quoted=not quoted
  elif not quoted:
   if ch=='(': depth+=1
   elif ch==')': depth-=1
   elif ch==',' and depth==0: out.append(body[start:i]); start=i+1
 out.append(body[start:]); return out

def marked_templates(row,name):
 args=split_call(row["call"])
 return [name+"("+",".join(args[:i]+["@"]+args[i+1:])+")"
         for i,k in enumerate(row["arguments"]) if k=="number"]

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
  for ti,t in enumerate(marked_templates(d["rows"][name],name)):
   for kind,bad in BAD.items():
    expr=t.replace("@",bad)
    for shape in shapes:
     fs[address(i)]="="+shape.replace("@",expr); i+=1
 # Append new source families so existing stable keys retain their addresses.
 for name in sorted(d["rows"]):
  for ti,t in enumerate(marked_templates(d["rows"][name],name)):
   for kind,bad in EXTRA_BAD.items():
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
 out["api"]={"reference":"rule","programs":json.load(open(os.path.join(DATA,"api","expectations.json")))["programs"]}
 return out,d

class ToolError(Exception):
 """The tool could not measure: exit 2, never a verdict."""

# ---- the rule ---------------------------------------------------------------
SEVEN = ("#DIV/0!", "#N/A", "#NAME?", "#NULL!", "#NUM!", "#REF!", "#VALUE!")
CALC_NUMBER = re.compile(r"-?\d\.\d{14}E[+-]\d+")
NUMBER_TEXT = re.compile(r"-?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?")
WHOLE_TEXT = re.compile(r"-?\d+")
FORMAT = "0.00000000000000E+00"

def decimal(text, pattern=NUMBER_TEXT):
 """The exact decimal a text spells, or None when it is not one."""
 if not isinstance(text, str) or not pattern.fullmatch(text): return None
 try: return Decimal(text)
 except InvalidOperation: return None

def agree(a, b):
 """Within one unit in the fifteenth significant digit of the larger."""
 if a is None or b is None or not a.is_finite() or not b.is_finite(): return False
 m = max(abs(a), abs(b))
 if m == 0: return True
 return abs(a - b) <= Decimal(1).scaleb(m.adjusted() - 14)

def calc_class(c):
 if CALC_NUMBER.fullmatch(c): return "number"
 if c.startswith("#") or re.fullmatch(r"Err:\d+", c): return "error"
 return "text"

def matches(c, logical, mine):
 """Step 1's rule for one cell. mine = {"kind","value","display"}; kind is
 N (number), L (logical), S (text), E (error), CRASH or TIMEOUT."""
 k, value, disp = mine["kind"], mine["value"], mine["display"]
 if k in ("CRASH", "TIMEOUT"): return False
 cls = calc_class(c)
 if cls == "number":
  if k not in ("N", "L"): return False
  want = decimal(c, CALC_NUMBER); v = decimal(value)
  if not agree(v, want): return False
  if logical is not None:
   return k == "L" and disp == logical and v == (1 if logical == "TRUE" else 0)
  shown = decimal(disp)
  if not agree(shown, want): return False
  if v == v.to_integral_value() and abs(v) < Decimal("1E15") and not WHOLE_TEXT.fullmatch(disp): return False
  return True
 if cls == "error":
  if k != "E": return False
  if disp == "#ERROR": return False
  if c.startswith("Err:"): return disp in SEVEN
  return disp == c
 return k != "E" and disp == c

def same_answer(old, new):
 """The before comparison: the same number by agree(), the same error name,
 or the same text."""
 if old["kind"] != new["kind"]:
  if {old["kind"], new["kind"]} <= {"N", "L"}: pass
  else: return False
 if new["kind"] in ("N", "L"): return agree(decimal(old["value"]), decimal(new["value"]))
 if new["kind"] in ("CRASH", "TIMEOUT"): return True
 return old["display"] == new["display"]

# ---- this spreadsheet -------------------------------------------------------
def q(x): return json.dumps(x, ensure_ascii=False)
CELL_FN = '''define bar_cell(a) as:
    local d is sheet.display of [s, a]
    if (has_key of [s.err, a]):
        return ["E", "", d]
    local v is sheet.get of [s, a]
    if (type of v) == "num":
        return ["N", str of v, d]
    if (type of v) == "dict" and (has_key of [v, "b"]):
        return ["L", str of v.b, d]
    if (type of v) == "str":
        return ["S", v, d]
    return ["?", str of v, d]'''

def has_net(tree):
 return "\ndefine net_caught(sheet) as:" in open(os.path.join(tree,"sheet.eigs"),encoding="utf-8").read()

def install(tree, tmp):
 md=os.path.join(tmp,"eigs_modules","sheet"); os.makedirs(md)
 for n in ("sheet.eigs","pdf.eigs","eigs.json"): shutil.copy(os.path.join(tree,n),md)

def runtime_grid(tree, binary, spec, cells, timeout=120, net=True):
 """One process for the given cells: {"cells": {addr: answer}, "net": [...]}
 or "CRASH" / "TIMEOUT"."""
 tmp=tempfile.mkdtemp()
 try:
  install(tree,tmp)
  lines=["import sheet","s is sheet.new_sheet of null"]
  for a,v in list(spec.get("base",{}).items())+[(a,spec["f"][a]) for a in cells]:
   lines.append("sheet.set_cell of [s,%s,%s]"%(q(a),q(v)))
  lines += ["sheet.recalc of s", CELL_FN]
  for a in cells: lines.append('print of (%s + (json_encode of (bar_cell of %s)))'%(q(a+"\t"),q(a)))
  if net: lines.append('print of ("NET\\t" + (json_encode of (sheet.net_caught of s)))')
  open(os.path.join(tmp,"app.eigs"),"w").write("\n".join(lines)+"\n")
  try: r=subprocess.run([binary,"app.eigs"],cwd=tmp,text=True,capture_output=True,timeout=timeout)
  except subprocess.TimeoutExpired: return "TIMEOUT"
  if r.returncode: return "CRASH"
  out={}; caught=None
  for x in r.stdout.splitlines():
   if "\t" not in x: continue
   a,j=x.split("\t",1)
   if a=="NET": caught=json.loads(j); continue
   k,v,d=json.loads(j); out[a]={"kind":k,"value":v,"display":d}
  if net and caught is None: return "CRASH"
  return {"cells":out,"net":caught or []}
 finally: shutil.rmtree(tmp)

def run_chunks(tree, binary, spec, net=True, grid=runtime_grid, size=200):
 """Every cell of the set, and the set of cells the net caught."""
 out={}; caught=set(); cells=list(spec["f"])
 for off in range(0,len(cells),size):
  chunk=cells[off:off+size]; got=grid(tree,binary,spec,chunk,net=net)
  if isinstance(got,dict) and set(got["cells"])==set(chunk):
   out.update(got["cells"]); caught.update(got["net"]); continue
  for ad in chunk:
   one=grid(tree,binary,spec,[ad],timeout=60,net=net)
   if isinstance(one,dict) and ad in one["cells"]: out[ad]=one["cells"][ad]; caught.update(one["net"])
   else: out[ad]={"kind":one if one in ("CRASH","TIMEOUT") else "CRASH","value":"","display":""}
 return out,caught

# ---- LibreOffice Calc -------------------------------------------------------
def col_number(a):
 m=re.fullmatch(r"([A-Z]+)(\d+)",a); c=0
 for ch in m.group(1): c=c*26+ord(ch)-64
 return c,int(m.group(2))

def col_letters(c):
 s=""
 while c: c,r=divmod(c-1,26); s=chr(65+r)+s
 return s

CSV_SHOWN = "csv:Text - txt - csv (StarCalc):44,34,76,1,,0,false,true,true"

def calc_rows(path, last_row, last_col):
 """Calc's CSV rows; every row 1..last_row must end in its sentinel."""
 rows=list(csv.reader(open(path,newline="",encoding="utf-8")))
 for i in range(last_row):
  if i>=len(rows) or len(rows[i])<last_col or rows[i][last_col-1]!="@row%d"%(i+1):
   raise ToolError("Calc row %d is missing or short in %s"%(i+1,os.path.basename(path)))
 return rows

def calc_grid(spec):
 """{addr: (C, "TRUE"/"FALSE"/None)} for every cell of spec["f"], from Calc."""
 import openpyxl
 from openpyxl.workbook.defined_name import DefinedName
 office=shutil.which("libreoffice") or shutil.which("soffice")
 if not office: raise ToolError("LibreOffice Calc is required")
 cells=list(spec.get("base",{}).items())+list(spec["f"].items())
 last_col=max(col_number(a)[0] for a,_ in cells)+1; last_row=max(col_number(a)[1] for a,_ in cells)
 tmp=tempfile.mkdtemp()
 try:
  paths=[]
  for name,fmt in (("formatted",FORMAT),("plain",None)):
   w=openpyxl.Workbook(); s=w.active
   for a,v in cells:
    if v.startswith("="):
     for n in XLFN: v=re.sub(r"\b"+n+r"\(","_xlfn."+n+"(",v)
     s[a]=v
    else:
     try: s[a]=int(v)
     except ValueError:
      try: s[a]=float(v)
      except ValueError: s[a]=v
    if fmt and a in spec["f"]: s[a].number_format=fmt
   for r in range(1,last_row+1): s[col_letters(last_col)+str(r)]="@row%d"%r
   for nm,ref in spec.get("names",{}).items(): w.defined_names[nm]=DefinedName(nm,attr_text=ref)
   w.calculation.fullCalcOnLoad=True; p=os.path.join(tmp,name+".xlsx"); w.save(p); paths.append(p)
  r=subprocess.run([office,"--headless","--norestore","--nolockcheck","-env:UserInstallation=file://"+tmp+"/profile",
                    "--convert-to",CSV_SHOWN,"--outdir",tmp]+paths,capture_output=True,timeout=600)
  grids={}
  for name in ("formatted","plain"):
   f=os.path.join(tmp,name+".csv")
   if not os.path.exists(f): raise ToolError("LibreOffice produced no %s CSV: %s"%(name,r.stderr.decode(errors="replace")))
   grids[name]=calc_rows(f,last_row,last_col)
  out={}
  for a in spec["f"]:
   c,rw=col_number(a); text=grids["formatted"][rw-1][c-1]; plain=grids["plain"][rw-1][c-1]
   out[a]=(text, plain if (plain in ("TRUE","FALSE") and calc_class(text)=="number") else None)
  return out
 finally: shutil.rmtree(tmp)

def validate_templates(d, oracle=calc_grid):
 """Ask Calc whether each unmarked valid call works before trusting the table."""
 fs={}; owner={}; i=0
 for name,row in d["rows"].items():
  if name=="NA": continue # NA's only valid result is the error value it constructs.
  a=address(i); i+=1; fs[a]="="+row["call"]; owner[a]=(name,row["call"])
 if not fs: raise ToolError("template validation examined=0")
 got=oracle({"base":BASE,"f":fs})
 if set(got)!=set(fs): raise ToolError("template validation: Calc answered %d of %d"%(len(got),len(fs)))
 for a,(v,_) in got.items():
  if calc_class(v)=="error":
   name,t=owner[a]; raise ValueError("template is an error by itself in Calc: %s: %s -> %s"%(name,t,v))

# ---- before.json ------------------------------------------------------------
def before_key(set_name, address, formula):
 return set_name+"\t"+formula

def write_before(path, sets, tree, binary, grid=runtime_grid):
 """The answers of `tree` on `binary` for every formula set, written whole."""
 doc={"tree":tree,"runtime":binary,"inputs":{},"cells":{}}
 for name,spec in sets.items():
  if spec.get("reference")=="rule": continue
  if not spec.get("f"): raise ToolError("SET %s examined=0 is invalid"%name)
  mine,_=run_chunks(tree,binary,spec,net=False,grid=grid)
  doc["inputs"][name]=spec.get("base",{})
  for ad,f in spec["f"].items():
   k=before_key(name,ad,f)
   if k in doc["cells"]: raise ToolError("two cells share the before key "+repr(k))
   doc["cells"][k]=mine[ad]
 with open(path,"w") as fh: json.dump(doc,fh,indent=1,sort_keys=True)
 return len(doc["cells"])

def check_before(doc, sets):
 """Every key of before.json names a cell of the present population, and each
 set's inputs are the present ones."""
 live={}
 for name,spec in sets.items():
  if spec.get("reference")=="rule": continue
  if name in doc["inputs"] and doc["inputs"][name]!=spec.get("base",{}):
   raise ToolError("before.json: the inputs of set %s are not the present ones"%name)
  for ad,f in spec["f"].items(): live[before_key(name,ad,f)]=1
 stale=[k for k in doc["cells"] if k not in live]
 if stale: raise ToolError("before.json has %d keys no present cell has, first %r"%(len(stale),stale[0]))

# ---- one set ----------------------------------------------------------------
def compare_set(name, spec, mine, caught, calc, before):
 """Records and counts for one formula set."""
 if not spec.get("f"): raise ToolError("SET %s examined=0 is invalid"%name)
 recs=[]; n={"examined":0,"differ":0,"before":0,"net":0,"crash":0}
 for ad,f in spec["f"].items():
  if ad not in calc: raise ToolError("Calc has no row for %s:%s"%(name,ad))
  if ad not in mine: raise ToolError("no answer for %s:%s"%(name,ad))
  c,logical=calc[ad]; m=mine[ad]; net=ad in caught
  ok=matches(c,logical,m) and not net
  n["examined"]+=1; n["net"]+=net; n["crash"]+=m["kind"] in ("CRASH","TIMEOUT")
  b=False
  if not ok:
   n["differ"]+=1
   old=before.get(before_key(name,ad,f)) if before is not None else None
   if old is not None and same_answer(old,m): b=True; n["before"]+=1
  recs.append({"set":name,"address":ad,"formula":f,"calc":c,"calc_logical":logical,"kind":m["kind"],
               "value":m["value"],"display":m["display"],"net":net,"verdict":"match" if ok else "differ","before":b})
 return recs,n

def api_grid(tree,binary,spec):
 out={}; api=os.path.join(DATA,"api"); crashed=0
 for program,item in spec["programs"].items():
  tmp=tempfile.mkdtemp()
  try:
   install(tree,tmp)
   shutil.copy(os.path.join(api,program),os.path.join(tmp,"app.eigs"))
   if program=="sc-6-csv.eigs":
    os.makedirs(os.path.join(tmp,"api")); open(os.path.join(tmp,"api","big.csv"),"w").write("9223372036854775807,9223372036854775807,=A1+B1\n9007199254740993,5000000000,=A2*B2\n")
    s=open(os.path.join(tmp,"app.eigs")).read().replace("REVIEW_DIR/api/big.csv","api/big.csv"); open(os.path.join(tmp,"app.eigs"),"w").write(s)
   r=subprocess.run([binary,"app.eigs"],cwd=tmp,text=True,capture_output=True,timeout=60)
   got=r.stdout.splitlines() if r.returncode==0 else ["CRASH"]; crashed+=r.returncode!=0
   for i,expected in enumerate(item["expect"]): out[program+":"+str(i)]=(got[i] if i<len(got) else "<missing>",expected)
  finally: shutil.rmtree(tmp)
 return out,crashed

# ---- the run ----------------------------------------------------------------
def run_bar(sets, tree, binary, before_doc, out=None, calc=calc_grid, grid=runtime_grid, api=api_grid, log=print):
 """Every set; returns (totals, exit status)."""
 if not sets: raise ToolError("no set to run")
 net=has_net(tree)
 if not net: raise ToolError("the tree has no `define net_caught(sheet)`: the net cannot be counted")
 before=None
 if before_doc is not None: check_before(before_doc,sets); before=before_doc["cells"]
 T={"examined":0,"differ":0,"before":0,"net":0,"crash":0,"rule_examined":0,"rule_differ":0}; records=[]
 for name,spec in sets.items():
  if spec.get("reference")=="rule":
   got,crashed=api(tree,binary,spec); n=len(got); diff=sum(a!=e for a,e in got.values())
   T["rule_examined"]+=n; T["rule_differ"]+=diff; T["crash"]+=crashed
   log("SET %s reference=rule examined=%d match=%d differ=%d crash=%d"%(name,n,n-diff,diff,crashed))
   for key,(a,e) in got.items(): records.append({"set":name,"key":key,"eigen":a,"rule":e,"verdict":"match" if a==e else "differ"})
   continue
  lo=calc(spec); mine,caught=run_chunks(tree,binary,spec,grid=grid)
  recs,n=compare_set(name,spec,mine,caught,lo,before); records+=recs
  for k in n: T[k]+=n[k]
  log("SET %s examined=%d match=%d differ=%d before=%d net=%d crash=%d"%(name,n["examined"],n["examined"]-n["differ"],n["differ"],n["before"],n["net"],n["crash"]))
 if out:
  with open(out,"w") as fh: json.dump(records,fh,indent=1)
 bad=T["differ"] or T["net"] or T["crash"] or T["rule_differ"]
 return T, (1 if bad else 0)

def main(argv=None):
 ap=argparse.ArgumentParser(); ap.add_argument("--tree",default=ROOT); ap.add_argument("--runtime",default=os.environ.get("EIGENSCRIPT","eigenscript"))
 ap.add_argument("--list",action="store_true"); ap.add_argument("--set"); ap.add_argument("--out"); ap.add_argument("--selftest",action="store_true")
 ap.add_argument("--before",default=os.path.join(DATA,"before.json"))
 ap.add_argument("--write-before",action="store_true",help="write --before from --old-tree on --old-runtime (all formula sets)")
 ap.add_argument("--old-tree"); ap.add_argument("--old-runtime")
 a=ap.parse_args(argv); start=time.monotonic()
 if a.selftest: return selftest(a.tree)
 try:
  sets,d=population(a.tree); print("DISPATCHER names=%d rule=%s"%(len(d["rows"]),d["rule"]))
  positions=sum(row["arguments"].count("number") for row in d["rows"].values())
  print("TEMPLATES functions=%d positions=%d"%(len(d["rows"]),positions))
  if a.list:
   for n,s in sets.items():
    for ad,f in s.get("f",{}).items(): print("%s\t%s\t%s"%(n,ad,f))
   return 0
  if a.write_before:
   if a.set: raise ToolError("--write-before writes the whole file: no --set")
   if not (a.old_tree and a.old_runtime): raise ToolError("--write-before needs --old-tree and --old-runtime")
   n=write_before(a.before,sets,a.old_tree,a.old_runtime)
   print("BEFORE written=%d path=%s wall=%.1fs"%(n,a.before,time.monotonic()-start)); return 0
  if a.set:
   if a.set not in sets: raise ToolError("unknown set "+a.set)
   sets={a.set:sets[a.set]}
  if a.set!="api": validate_templates(d)
  if not os.path.exists(a.before): raise ToolError("no before file "+a.before+" (write it with --write-before)")
  doc=json.load(open(a.before))
  if a.set: doc={"inputs":doc["inputs"],"cells":{k:v for k,v in doc["cells"].items() if k.split("\t",1)[0]==a.set}}
  T,status=run_bar(sets,a.tree,a.runtime,doc,a.out)
 except ToolError as e:
  print("NUMBER-BAR TOOL-ERROR %s"%e); return 2
 print("NUMBER-BAR examined=%d differ=%d before=%d net=%d crash=%d rule_examined=%d rule_differ=%d wall=%.1fs"%(
  T["examined"],T["differ"],T["before"],T["net"],T["crash"],T["rule_examined"],T["rule_differ"],time.monotonic()-start))
 return status

# ---- self-test: one-line mutants of this file, no LibreOffice ---------------
def _stub_calc(table):
 return lambda spec: {a:table[a] for a in spec["f"] if a in table}

def _stub_grid(answers, crash=(), caught=()):
 def grid(tree, binary, spec, cells, timeout=0, net=True):
  if any(a in crash for a in cells): return "CRASH"
  return {"cells":{a:dict(answers[a]) for a in cells},"net":[a for a in cells if a in caught]}
 return grid

def N(v, d=None): return {"kind":"N","value":v,"display":v if d is None else d}
def E(d): return {"kind":"E","value":"","display":d}

def _bar(m, tree, f, calc, answers, crash=(), caught=(), before=None, base=None):
 """The outcome the bar gives for one set "t": the counts and exit status, or
 TOOL-ERROR."""
 sets={"t":{"base":base or {},"f":f,"reference":"calc"}}
 try:
  T,status=m.run_bar(sets,tree,"stub",before,calc=_stub_calc(calc),grid=_stub_grid(answers,crash,caught),log=lambda *x:None)
  return "examined=%d differ=%d before=%d net=%d crash=%d status=%d"%(T["examined"],T["differ"],T["before"],T["net"],T["crash"],status)
 except Exception as e:
  if type(e).__name__=="ToolError": return "TOOL-ERROR"
  raise

def _one(c, mine, logical=None): return dict(f={"A1":"=1"},calc={"A1":(c,logical)},answers={"A1":mine})

def _before_case(m, tree, tmp):
 """before.json written for A1 '=X', A2 '=Y'; then the two formulas swap
 addresses.  Matched by formula, both cells' answers are as before."""
 old={"t":{"base":{},"f":{"A1":"=X","A2":"=Y"},"reference":"calc"}}
 p=os.path.join(tmp,"before.json")
 m.write_before(p,old,tree,"stub",grid=_stub_grid({"A1":N("1"),"A2":N("2")}))
 return _bar(m,tree,{"A1":"=Y","A2":"=X"},{"A1":("9.00000000000000E+00",None),"A2":("9.00000000000000E+00",None)},
             {"A1":N("2"),"A2":N("1")},before=json.load(open(p)))

def _csv_case(m, tree, tmp):
 """Calc's CSV loses its second row: the reader must refuse it."""
 p=os.path.join(tmp,"short.csv"); open(p,"w").write("1,@row1\n")
 try: m.calc_rows(p,2,2); return "read"
 except Exception as e: return "TOOL-ERROR" if type(e).__name__=="ToolError" else repr(e)

ONE = 'return abs(a - b) <= Decimal(1).scaleb(m.adjusted() - 14)'
PLANTS = [
 # (name, anchor, replacement, case, the clean tool's (correct) outcome)
 ("number rule widened: a 13th-digit difference accepted", ONE, ONE.replace("- 14","- 12"),
  lambda m,t,x: _bar(m,t,**_one("1.00000000000000E+00",N("1.000000000001"))), 'examined=1 differ=1 before=0 net=0 crash=0 status=1'),
 ("#ERROR accepted as a match for a Calc error", 'if disp == "#ERROR": return False', 'if disp == "#ERROR": return True',
  lambda m,t,x: _bar(m,t,**_one("Err:502",E("#ERROR"))), 'examined=1 differ=1 before=0 net=0 crash=0 status=1'),
 ("an Err:502 expectation refused for #NUM!", 'if c.startswith("Err:"): return disp in SEVEN', 'if c.startswith("Err:"): return disp == c',
  lambda m,t,x: _bar(m,t,**_one("Err:502",E("#NUM!"))), 'examined=1 differ=0 before=0 net=0 crash=0 status=0'),
 ("a different error name accepted where Calc names one", "  return disp == c\n", "  return True\n",
  lambda m,t,x: _bar(m,t,**_one("#DIV/0!",E("#NUM!"))), 'examined=1 differ=1 before=0 net=0 crash=0 status=1'),
 ("a whole number displayed with .0 accepted", 'and not WHOLE_TEXT.fullmatch(disp): return False', 'and not WHOLE_TEXT.fullmatch(disp): pass',
  lambda m,t,x: _bar(m,t,**_one("5.00000000000000E+00",N("5.0"))), 'examined=1 differ=1 before=0 net=0 crash=0 status=1'),
 ("a net-caught cell counted as a match", "ok=matches(c,logical,m) and not net", "ok=matches(c,logical,m)",
  lambda m,t,x: _bar(m,t,caught={"A1"},**_one("#NUM!",E("#NUM!"))), 'examined=1 differ=1 before=0 net=1 crash=0 status=1'),
 ("run_chunks gives every cell of a failed chunk a value", "one=grid(tree,binary,spec,[ad],timeout=60,net=net)",
  'one={"cells":{ad:{"kind":"N","value":"7","display":"7"}},"net":[]}',
  lambda m,t,x: _bar(m,t,{"A1":"=1","A2":"=2"},{"A1":("7.00000000000000E+00",None),"A2":("7.00000000000000E+00",None)},
                     {"A1":N("7"),"A2":N("7")},crash={"A2"}), 'examined=2 differ=1 before=0 net=0 crash=1 status=1'),
 ("an empty set accepted", 'if not spec.get("f"): raise ToolError("SET %s examined=0 is invalid"%name)\n recs=',
  'if False: raise ToolError("SET %s examined=0 is invalid"%name)\n recs=',
  lambda m,t,x: _bar(m,t,{},{},{}), 'TOOL-ERROR'),
 ("a missing Calc answer read as blank", 'if ad not in calc: raise ToolError("Calc has no row for %s:%s"%(name,ad))',
  'if ad not in calc: calc[ad]=("",None)',
  lambda m,t,x: _bar(m,t,{"A1":"=\"\""},{},{"A1":{"kind":"S","value":"","display":""}}), 'TOOL-ERROR'),
 ("a short Calc CSV row read", 'if i>=len(rows) or len(rows[i])<last_col or rows[i][last_col-1]!="@row%d"%(i+1):', "if False:",
  lambda m,t,x: _csv_case(m,t,x), 'TOOL-ERROR'),
 ("a before.json key matched by address instead of formula", 'return set_name+"\\t"+formula', 'return set_name+"\\t"+address',
  lambda m,t,x: _before_case(m,t,x), 'examined=2 differ=2 before=2 net=0 crash=0 status=1'),
]
CONTROLS = [
 ("a 17th-digit difference matches", lambda m,t,x: _bar(m,t,**_one("1.00000000000000E+00",N("1.0000000000000002"))),
  "examined=1 differ=0 before=0 net=0 crash=0 status=0"),
 ("Err:502 matches #NUM!", lambda m,t,x: _bar(m,t,**_one("Err:502",E("#NUM!"))), "examined=1 differ=0 before=0 net=0 crash=0 status=0"),
 ("a logical matches only as a logical", lambda m,t,x: (_bar(m,t,**_one("1.00000000000000E+00",{"kind":"L","value":"1","display":"TRUE"},"TRUE")),
  _bar(m,t,**_one("1.00000000000000E+00",N("1"),"TRUE"))), ("examined=1 differ=0 before=0 net=0 crash=0 status=0","examined=1 differ=1 before=0 net=0 crash=0 status=1")),
]

def _load(path, name):
 import importlib.util
 spec=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def selftest(tree):
 src=open(os.path.abspath(__file__),encoding="utf-8").read(); tmp=tempfile.mkdtemp(); failed=0; examined=0
 # anchors are looked for, and edited, only above this section (the table holds them too)
 cut=src.index("# ---- self-test: one-line mutants"); body,rest=src[:cut],src[cut:]
 try:
  clean=_load(os.path.abspath(__file__),"bar_clean")
  for name,case,want in CONTROLS:
   got=case(clean,tree,tmp); examined+=1
   if got!=want: failed+=1; print("FAIL: control %s: %r, wanted %r"%(name,got,want))
   else: print("PASS: control %s: %s"%(name,got))
  for i,(name,anchor,repl,case,right) in enumerate(PLANTS):
   examined+=1; n=body.count(anchor)
   if n!=1: failed+=1; print("FAIL: %s: anchor found %d times"%(name,n)); continue
   p=os.path.join(tmp,"mutant%d.py"%i); open(p,"w",encoding="utf-8").write(body.replace(anchor,repl)+rest)
   want=case(clean,tree,tmp)
   if want!=right: failed+=1; print("FAIL: %s: the clean tool gives %r, wanted %r"%(name,want,right)); continue
   got=case(_load(p,"bar_mutant%d"%i),tree,tmp)
   if got==want: failed+=1; print("FAIL: %s: the mutant gives the clean result %r"%(name,got))
   else: print("PASS: %s: clean %s; mutant %s"%(name,want,got))
 finally: shutil.rmtree(tmp)
 total=len(CONTROLS)+len(PLANTS)
 if not (examined==total>0): failed+=1
 print("SELFTEST examined=%d of %d failed=%d"%(examined,total,failed))
 return 1 if failed else 0

if __name__=="__main__": sys.exit(main())
