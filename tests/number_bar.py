#!/usr/bin/env python3
"""#104 number-boundary bar.

The population is rebuilt from sheet.eigs and templates.json on every run.
Formula cells occupy AA1 onward; inputs retain their declared addresses, so the
two regions are disjoint.  A
grid is run in chunks of 200 cells, one runtime process per chunk; a chunk that
crashes, times out (120 s) or does not print exactly its cells is run again one
cell per process, and a cell whose own process fails is CRASH, or TIMEOUT after
10 s.  The OLD derivation therefore records TIMEOUT after the same ten-second
per-cell limit.  A cell's answer comes from bar_answer in api/bar_api.eigs, the one
definition the api programs use too.

LibreOffice Calc decides every expected answer.  The tool writes each sheet into
an .xlsx twice: once with the number format 0.00000000000000E+00 (fifteen
significant digits, scientific) on every judged cell, and once with no format.
Both are converted to CSV by one headless Calc call with "save cell contents as
shown", so C, Calc's text for a cell, is a number in one spelling whatever Calc
would have auto-formatted.  The unformatted copy is read only for the shape of
a result whose C has that spelling: TRUE or FALSE there is a logical; the same
text there is a text that only looks like a number (Calc never shows a number
unformatted with fourteen decimals and a two-digit exponent).  A sentinel text
in the column after the last one used is written on every row and must come
back: a missing Calc row is the tool's error, never an expectation of blank.

THE RULE (the only tolerance in this tool).  For one cell, with C and this
spreadsheet's VALUE (sheet.get; a logical read as its number) and DISPLAY
(sheet.display):
- C is a number (it has the scientific form above, and is not a text).  The
  cell matches when the
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
A cell is caught when its answer changes if catches reachable while recalc
evaluates that cell re-raise instead.  The spreadsheet's `sheet.net_caught`
account is reported separately and does not decide the verdict.

`differ` counts every cell that does not match; no cell is set apart from it.
`before` is information that subtracts nothing: of the cells that differ now,
those whose answer on this repository's main with the OLD runtime was the same
(the same number by the rule's agreement, the same error name, the same text,
or the same CRASH or TIMEOUT).  tests/number_bar/before.json holds that run's
answers, keyed by set, formula text and the set's input cells, and is written
whole by --write-before; a key no present cell has is the tool's error.  The
api set has no before.

The api set (api/expectations.json) checks the paths outside recalc.  Each
program prints, with api/bar_api.eigs, every cell's raw content and the
defined names at each stage, and its judged answers.  Every expected item is
asked of Calc in the run (calc=cell: the same cell of the same sheet; calc=a
formula over the stage's cells, for the pivot and the status bar; calc=csv-out:
every cell of the range, against the fields of the CSV this spreadsheet wrote;
a stage may start from Calc's own read of a CSV), and compared by THE RULE.
Items no Calc operation answers (goal seek's root) carry their rule and an
expected text in Calc's spelling and are counted apart as rule_examined and
rule_differ.  A program that aborts counts each of its items as differing and
adds one to crash.

For a declared operation stage Calc receives the dump from immediately before
the operation, not the result dump: sort_range arguments are sheet, two
0-based corners, the 0-based key column within the range, and descending;
copy_block arguments are sheet and two 0-based corners, while paste_block is
sheet, that clip, and its 0-based target.  The declarations are checked against
the program lines.  Calc performs the sort or copy/paste through UNO.  Both the
cell content and value are judged; content normalisation changes CRLF/CR to LF,
strips surrounding whitespace, and Decimal-canonicalises finite numeric
constants, identically on both sides (formula text is otherwise unchanged).

Exit 0 only when differ, net, crash and rule_differ are all 0 and every set
ran; 1 when any is not; 2 for the tool's own errors.
"""
import argparse, csv, io, json, os, re, shutil, subprocess, sys, tempfile, time
from decimal import Decimal, InvalidOperation

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "tests", "number_bar")
XLFN = ("TEXTJOIN", "XOR", "IFNA", "IFS", "SWITCH", "XLOOKUP")
SOURCES = {
 "floating-overflow/operator":"1E300*1E10",
 "large-double/inline-product":"3037000500*3037000500",
 "nonfinite/dispatcher-function":"POWER(10,400)", "nan":"POWER(-1,0.5)",
 "na":"NA()", "division-zero":"1/0", "text":"\"not a number\"",
 "floating-overflow/power":"0.5^-2000",
 "floating-overflow/sum":"SUM(1E308,1E308)",
 "typed-int64/product":"B10*B10", "typed-int64/sum":"B11+B11",
 "typed-int64/difference":"B12-B11"}
BASE = {"B1":"1","B2":"2","B3":"3","C1":"10","C2":"20","C3":"30",
        "D1":"-1","D2":"2", "B10":"3037000500", "B11":"9223372036854775807",
        "B12":"-9223372036854775808"}
GENERATED_EMPTY = []

def dispatcher(tree):
 s=open(os.path.join(tree,"sheet.eigs"),encoding="utf-8").read()
 return sorted(set(re.findall(r'fname == "([A-Z][A-Z0-9_.]*)"',s)))

def load_templates(tree, path=None):
 p=path or os.path.join(DATA,"templates.json"); d=json.load(open(p)); got=set(dispatcher(tree)); rows=d["rows"]
 missing=sorted(got-set(rows)); stale=sorted(set(rows)-got)
 if missing: raise ValueError("dispatcher function has no template row: "+", ".join(missing))
 if stale: raise ValueError("template row lacks dispatcher function: "+", ".join(stale))
 for n,v in rows.items():
  if not isinstance(v,dict) or set(v) - {"call","arguments","note","source","paths"}: raise ValueError("invalid template row: "+n)
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
         for i,k in enumerate(row["arguments"]) if k!="range"]

def arrival_templates(row, name):
 """Derive every applicable arrival path from a row, never a case list."""
 args=split_call(row["call"]); out=[]
 if len(row.get("paths", [])) != len(row["arguments"]): raise ValueError("arrival paths do not match arguments: "+name)
 for i,paths in enumerate(row["paths"]):
  if not paths: raise ValueError("argument has no arrival path: %s position %d"%(name,i+1))
  for path in paths: out.append((i,path,name+"("+",".join(args[:i]+["@"]+args[i+1:])+")"))
 return out

def address(i):
 col=""; n=i//500+27
 while n: n,r=divmod(n-1,26); col=chr(65+r)+col
 return col+str(i%500+1)

def population(tree):
 d=load_templates(tree); out={}
 fs={}; i=0
 # Continued errors are tested bare and inside both required wrappers.
 shapes=("@","IFERROR(@,7101)","ISERROR(@)","(@)+2*3","IFERROR((@)+2*3,7101)","ISERROR((@)+2*3)")
 for name in sorted(d["rows"]):
  for ti,t in enumerate(marked_templates(d["rows"][name],name)):
   for kind,bad in SOURCES.items():
    expr=t.replace("@",bad)
    for shape in shapes:
     fs[address(i)]="="+shape.replace("@",expr); i+=1
 out["class"]={"base":BASE,"empty":GENERATED_EMPTY,"f":fs,"reference":"calc"}
 # c21's rule: 8 valid sources x 10 operators x 7 wrappers.
 sources=("NA()","1/0","SQRT(-1)","POWER(10,400)","0.5^-2000","SUM(1E308,1E308)","3037000500*3037000500","\"x\"+1")
 ops=("@+1+1","@*2*3","@*2/4","@/2*4","-@+1","ABS(@)+1","SUM(@,1)","@^2","(@)=0","@&\"x\"")
 wraps=("@","IFERROR(@,7)","IFNA(@,7)","ISERROR(@)","ISERR(@)","ISNA(@)","ERROR.TYPE(@)")
 fs={}; i=0
 for x in sources:
  for op in ops:
   for w in wraps: fs[address(i)]="="+w.replace("@",op.replace("@",x)); i+=1
 out["wrappers"]={"base":BASE,"empty":GENERATED_EMPTY,"f":fs,"reference":"calc"}
 # Number-to-text population is also generated, not retained from raw c3.json.
 xs=("(0.1+0.2)*10","2+1/100000","4/2","10/2","0.1+0.2","1E21","10^21","1E-7","10^-7","-0","0*-1","-(1/2-0.5)","2^53+1","9007199254740993","123456789012345678","123456789012345678*1","1/3","2^53","1E15+0.5","-2.5*2")
 ts=("@","@&\"\"","LEN(@)","LEFT(@,30)","RIGHT(@,3)","MID(@,1,30)","TEXT(@,\"0\")","TEXT(@,\"0.00\")","TEXT(@,\"#,##0\")","TEXT(@,\"0%\")","CONCATENATE(@)","VALUE(@&\"\")","VALUE(@&\"\")=@","(@&\"\")=TEXT(@,\"0\")")
 out["number-text"]={"base":{},"empty":GENERATED_EMPTY,"f":{address(i):"="+t.replace("@","("+x+")" if t!="@" else x) for i,(x,t) in enumerate((x,t) for x in xs for t in ts)},"reference":"calc"}
 # Arrival cells are generated from the same rows and sources.  A formula-cell
 # reference is common to all paths; ranges, criteria and lookup keys then use
 # their syntactic path, while comparisons put the reference on either side.
 fs={}; base=dict(BASE); i=0; source_cells={}; by_formula={}; formula_paths={}; path_own={}; same_formula=set()
 for name,row in sorted(d["rows"].items()):
  for pos,path,t in arrival_templates(row,name):
   for kind,bad in SOURCES.items():
    cell=source_cells.setdefault(kind,"ZZ%d"%(len(source_cells)+1)); base[cell]="="+bad
    if path=="inside-range": repl=cell+":"+cell
    elif path=="criterion": repl=cell
    elif path=="lookup-key": repl=cell
    elif path=="comparison-left": repl="("+cell+"=0)"
    elif path=="comparison-right": repl="(0="+cell+")"
    else: repl=cell
    formula="="+t.replace("@",repl); path_own.setdefault(path,0)
    if formula in by_formula:
     same_formula.add(formula); formula_paths[by_formula[formula]].append(path)
    else:
     ad=address(i); i+=1; by_formula[formula]=ad; fs[ad]=formula
     formula_paths[ad]=[path]; path_own[path]+=1
 out["arrivals-generated"]={"base":base,"empty":GENERATED_EMPTY,"f":fs,"paths":formula_paths,"reference":"calc"}
 hand=json.load(open(os.path.join(DATA,"arrival_cases.json")))
 out.update(hand)
 out["_arrival_counts"]={"generated":len(fs),"hand":sum(len(x.get("f",{})) for x in hand.values()),
                         "same_formula":len(same_formula),"subsumed":sorted(p for p,n in path_own.items() if not n)}
 out["api"]={"reference":"api","programs":json.load(open(os.path.join(DATA,"api","expectations.json")))["programs"]}
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

def matches(c, shape, mine):
 """Step 1's rule for one cell. shape is what the unformatted copy showed:
 "TRUE"/"FALSE" (a logical), "TEXT" (a text that merely looks like the
 number spelling), or None.  mine = {"kind","value","display"}; kind is
 N (number), L (logical), S (text), E (error), CRASH or TIMEOUT."""
 k, value, disp = mine["kind"], mine["value"], mine["display"]
 if k in ("CRASH", "TIMEOUT"): return False
 cls = "text" if shape == "TEXT" else calc_class(c)
 if cls == "number":
  if k not in ("N", "L"): return False
  want = decimal(c, CALC_NUMBER); v = decimal(value)
  if not agree(v, want): return False
  if shape is not None:
   return k == "L" and disp == shape and v == (1 if shape == "TRUE" else 0)
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
API = os.path.join(DATA, "api")

def has_net(tree):
 return "\ndefine net_caught(sheet) as:" in open(os.path.join(tree,"sheet.eigs"),encoding="utf-8").read()

def reraise_tree(tree):
 """Make a private module tree whose catches reachable from recalc's per-cell
 evaluator re-raise.  Reachability is lexical: the catch is inside recalc's
 queue loop and directly guards its `_eval_st` call."""
 source=open(os.path.join(tree,"sheet.eigs"),encoding="utf-8").read()
 catches=list(re.finditer(r"(?m)^(\s*)catch (\w+):\n",source))
 recalc=source.find("\ndefine recalc(sheet) as:")
 if recalc < 0: raise ToolError("sheet.eigs has no recalc")
 next_definition=source.find("\ndefine ",recalc+2)
 end=len(source) if next_definition < 0 else next_definition
 reachable=[m for m in catches if recalc < m.start() < end and "_eval_st of" in source[recalc:m.start()]]
 for m in reversed(reachable):
  indent,name=m.group(1),m.group(2); body_start=m.end(); pos=body_start
  while pos < len(source):
   nl=source.find("\n",pos); nl=len(source) if nl < 0 else nl+1
   line=source[pos:nl]
   if line.strip() and len(line)-len(line.lstrip()) <= len(indent): break
   pos=nl
  source=source[:body_start]+indent+"    throw of "+name+"\n"+source[pos:]
 tmp=tempfile.mkdtemp(prefix="number-bar-reraise-")
 for name in ("sheet.eigs","pdf.eigs","eigs.json"):
  if name=="sheet.eigs": open(os.path.join(tmp,name),"w",encoding="utf-8").write(source)
  else: shutil.copy(os.path.join(tree,name),tmp)
 return tmp,len(catches),len(reachable)

def install(tree, tmp):
 """The tree as the module `sheet`, and api/bar_api.eigs (the one definition of
 a cell's answer) with the api programs' CSV inputs beside the program."""
 md=os.path.join(tmp,"eigs_modules","sheet"); os.makedirs(md)
 for n in ("sheet.eigs","pdf.eigs","eigs.json"): shutil.copy(os.path.join(tree,n),md)
 for n in os.listdir(API):
  if n=="bar_api.eigs" or n.endswith(".csv"): shutil.copy(os.path.join(API,n),tmp)

def runtime_grid(tree, binary, spec, cells, timeout=120, net=True):
 """One process for the given cells: {"cells": {addr: answer}, "net": [...]}
 or "CRASH" / "TIMEOUT"."""
 tmp=tempfile.mkdtemp()
 try:
  install(tree,tmp)
  lines=["import sheet",'load_file of "bar_api.eigs"',"s is sheet.new_sheet of null"]
  for a,v in list(spec.get("base",{}).items())+[(a,spec["f"][a]) for a in cells]:
   lines.append("sheet.set_cell of [s,%s,%s]"%(q(a),q(v)))
  lines.append("sheet.recalc of s")
  for a in list(spec.get("base",{}))+cells: lines.append('print of (%s + (json_encode of (bar_answer of [s, %s])))'%(q(a+"\t"),q(a)))
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
  return {"cells":{a:out[a] for a in cells if a in out},"inputs":{a:out[a] for a in spec.get("base",{}) if a in out},"net":caught or []}
 finally: shutil.rmtree(tmp)

def run_chunks(tree, binary, spec, net=True, grid=runtime_grid, size=200):
 """Every cell of the set, and the set of cells the net caught."""
 out={}; caught=set(); inputs=[]; cells=list(spec["f"])
 for off in range(0,len(cells),size):
  chunk=cells[off:off+size]; got=grid(tree,binary,spec,chunk,net=net)
  if isinstance(got,dict) and set(got["cells"])==set(chunk):
   out.update(got["cells"]); inputs.append(got.get("inputs",{})); caught.update(got["net"]); continue
  for ad in chunk:
   one=grid(tree,binary,spec,[ad],timeout=10,net=net)
   if isinstance(one,dict) and ad in one["cells"]: out[ad]=one["cells"][ad]; caught.update(one["net"])
   else: out[ad]={"kind":one if one in ("CRASH","TIMEOUT") else "CRASH","value":"","display":""}
 return out,caught,inputs

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

def office():
 o=shutil.which("libreoffice") or shutil.which("soffice")
 if not o: raise ToolError("LibreOffice Calc is required")
 return o

def calc_put(s, a, v):
 if v.startswith("="):
  # Calc 24.2 lacks these dispatcher names.  These are semantic equivalents,
  # not expected values: Calc still independently evaluates every cell.
  v=re.sub(r"\bAVG\(","AVERAGE(",v)
  atom=r"((?:[^(),]|\([^()]*\))+?)"
  xp=re.compile(r"XLOOKUP\("+atom+r","+atom+r","+atom+r","+atom+r"\)")
  v=xp.sub(lambda m:"IFERROR(INDEX(%s,MATCH(%s,%s,0)),%s)"%
           (m.group(3),m.group(1),m.group(2),m.group(4)),v)
  for n in XLFN: v=re.sub(r"\b"+n+r"\(","_xlfn."+n+"(",v)
  s[a]=v
 else:
  try: s[a]=int(v)
  except ValueError:
   try: s[a]=float(v)
   except ValueError: s[a]=v

def calc_name(defn):
 """A defined name for the .xlsx: a cell or range gets the sheet and $."""
 if re.fullmatch(r"[A-Z]+\d+(:[A-Z]+\d+)?",defn):
  return "Sheet!"+":".join(re.sub(r"([A-Z]+)(\d+)",r"$\1$\2",x) for x in defn.split(":"))
 return defn

def calc_sheet(spec, start=None):
 """Calc's two CSVs ("formatted": spec["f"] cells in FORMAT; "plain": no
 format) of one sheet: spec["base"] and spec["f"] cells (an f value None keeps
 the cell Calc read from `start`, an .xlsx Calc wrote) and spec["names"]."""
 import openpyxl
 from openpyxl.workbook.defined_name import DefinedName
 o=office(); tmp=tempfile.mkdtemp()
 try:
  paths=[]; shape=None
  for name,fmt in (("formatted",FORMAT),("plain",None)):
   w=openpyxl.load_workbook(start) if start else openpyxl.Workbook(); s=w.active
   for a,v in list(spec.get("base",{}).items())+list(spec["f"].items()):
    if v is not None: calc_put(s,a,v)
    if fmt: s[a].number_format=fmt
   shape=(s.max_row,s.max_column+1)
   for r in range(1,shape[0]+1): s[col_letters(shape[1])+str(r)]="@row%d"%r
   for nm,ref in spec.get("names",{}).items(): w.defined_names[nm]=DefinedName(nm,attr_text=calc_name(ref))
   w.calculation.fullCalcOnLoad=True; p=os.path.join(tmp,name+".xlsx"); w.save(p); paths.append(p)
  r=subprocess.run([o,"--headless","--norestore","--nolockcheck","-env:UserInstallation=file://"+tmp+"/profile",
                    "--convert-to",CSV_SHOWN,"--outdir",tmp]+paths,capture_output=True,timeout=600)
  grids={}
  for name in ("formatted","plain"):
   f=os.path.join(tmp,name+".csv")
   if not os.path.exists(f): raise ToolError("LibreOffice produced no %s CSV: %s"%(name,r.stderr.decode(errors="replace")))
   grids[name]=calc_rows(f,*shape)
  return grids
 finally: shutil.rmtree(tmp)

def calc_cells(grids, addrs):
 """{addr: (C, shape)}: shape is "TRUE"/"FALSE" when the unformatted copy
 shows a logical, "TEXT" when it shows the same text as the formatted copy
 (a text result in the number spelling: a number's unformatted text never has
 fourteen decimals and a two-digit exponent), else None."""
 out={}
 for a in addrs:
  c,rw=col_number(a); text=grids["formatted"][rw-1][c-1]; plain=grids["plain"][rw-1][c-1]
  shape=None
  if calc_class(text)=="number":
   if plain in ("TRUE","FALSE"): shape=plain
   elif plain==text: shape="TEXT"
  out[a]=(text,shape)
 return out

class CalcResult(dict): pass

def calc_grid(spec):
 grids=calc_sheet(spec)
 out=CalcResult(calc_cells(grids,spec["f"]))
 out.inputs=calc_cells(grids,spec.get("base",{}))
 return out

CSV_READ = "CSV:44,34,76,1,,0,false,true,false,false,false,-1,true"

def calc_read_csv(text, tmp):
 """Calc's own read of a CSV text (formulas evaluated), as an .xlsx path."""
 d=tempfile.mkdtemp(dir=tmp); p=os.path.join(d,"in.csv"); open(p,"w",encoding="utf-8").write(text)
 r=subprocess.run([office(),"--headless","--norestore","--nolockcheck","-env:UserInstallation=file://"+d+"/profile",
                   "--infilter="+CSV_READ,"--convert-to","xlsx","--outdir",d,p],capture_output=True,timeout=600)
 x=os.path.join(d,"in.xlsx")
 if not os.path.exists(x): raise ToolError("LibreOffice did not read the CSV: "+r.stderr.decode(errors="replace"))
 return x

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

def check_formulas(sets):
 """Reject overlapping cells, formula references, and duplicate keys before evaluation."""
 lines=[]
 for name,spec in sets.items():
  if spec.get("reference")=="api": continue
  seen={}; duplicates=[]
  for ad,formula in spec.get("f",{}).items():
   if ad in spec.get("base",{}): raise ToolError("set %s formula cell %s is also an input"%(name,ad))
   if formula in seen: duplicates.append((formula,seen[formula],ad))
   else: seen[formula]=ad
  lines.append("FORMULAS set=%s examined=%d duplicates=%d"%(name,len(seen),len(duplicates)))
  if duplicates:
   formula,_,_=duplicates[0]
   raise ToolError("two cells share the before key "+repr(before_key(name,"",formula)))
  formula_cells=set(spec.get("f",{})); allowed=set(spec.get("base",{}))|set(spec.get("empty",[]))
  for ad,formula in spec.get("f",{}).items():
   refs=set()
   for a,b in re.findall(r"\b([A-Z]+\d+)(?::([A-Z]+\d+))?",formula):
    if b: refs.update(sum(range_cells(a+":"+b),[]))
    else: refs.add(a)
   bad=sorted(refs & formula_cells)
   if bad: raise ToolError("set %s formula %s refers to formula cell %s"%(name,ad,bad[0]))
   undeclared=sorted(refs-formula_cells-allowed)
   if undeclared: raise ToolError("set %s formula %s refers to undeclared cell %s"%(name,ad,undeclared[0]))
 generated=set(sets.get("arrivals-generated",{}).get("f",{}).values())
 hand=[formula for name,spec in sets.items() if name not in ("class","wrappers","number-text","arrivals-generated","api")
       for formula in spec.get("f",{}).values() if formula in generated]
 hand_examined=sum(len(spec.get("f",{})) for name,spec in sets.items()
                   if name not in ("class","wrappers","number-text","arrivals-generated","api"))
 lines.append("FORMULAS set=arrivals-hand-overlap examined=%d duplicates=%d"%(hand_examined,len(hand)))
 if hand: raise ToolError("hand and generated arrivals share formula "+repr(hand[0]))
 return lines

def write_before(path, sets, tree, binary, grid=runtime_grid):
 """The answers of `tree` on `binary` for every formula set, written whole."""
 check_formulas(sets)
 doc={"tree":tree,"runtime":binary,"inputs":{},"cells":{}}
 for name,spec in sets.items():
  if spec.get("reference")=="api": continue
  if not spec.get("f"): raise ToolError("SET %s examined=0 is invalid"%name)
  mine,_,_=run_chunks(tree,binary,spec,net=False,grid=grid)
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
 live={}; expected_inputs={}
 for name,spec in sets.items():
  if spec.get("reference")=="api": continue
  expected_inputs[name]=spec.get("base",{})
  if name not in doc.get("inputs",{}) or doc["inputs"][name]!=spec.get("base",{}):
   raise ToolError("before.json: the inputs of set %s are not the present ones"%name)
  for ad,f in spec["f"].items(): live[before_key(name,ad,f)]=1
 stale=[k for k in doc["cells"] if k not in live]
 if stale: raise ToolError("before.json has %d keys no present cell has, first %r"%(len(stale),stale[0]))
 missing=[k for k in live if k not in doc["cells"]]
 if missing: raise ToolError("before.json lacks %d present keys, first %r"%(len(missing),missing[0]))
 extra_inputs=sorted(set(doc.get("inputs",{}))-set(expected_inputs))
 if extra_inputs: raise ToolError("before.json has inputs for no present set: "+extra_inputs[0])

# ---- one set ----------------------------------------------------------------
def compare_set(name, spec, mine, caught, own, calc, before):
 """Records and counts for one formula set."""
 if not spec.get("f"): raise ToolError("SET %s examined=0 is invalid"%name)
 recs=[]; n={"examined":0,"differ":0,"before":0,"net":0,"net_own":0,"net_only_behaviour":0,"net_only_own":0,"crash":0}
 for ad,f in spec["f"].items():
  if ad not in calc: raise ToolError("Calc has no row for %s:%s"%(name,ad))
  if ad not in mine: raise ToolError("no answer for %s:%s"%(name,ad))
  c,shape=calc[ad]; m=mine[ad]; net=ad in caught
  ok=matches(c,shape,m) and not net
  is_own=ad in own
  n["examined"]+=1; n["net"]+=net; n["net_own"]+=is_own; n["net_only_behaviour"]+=net and not is_own; n["net_only_own"]+=is_own and not net; n["crash"]+=m["kind"] in ("CRASH","TIMEOUT")
  b=False
  if not ok:
   n["differ"]+=1
   old=before.get(before_key(name,ad,f)) if before is not None else None
   if old is not None and same_answer(old,m): b=True; n["before"]+=1
  recs.append({"set":name,"address":ad,"formula":f,"paths":spec.get("paths",{}).get(ad,[]),"calc":c,"calc_shape":shape,"kind":m["kind"],
               "value":m["value"],"display":m["display"],"net":net,"net_own":is_own,"verdict":"match" if ok else "differ","before":b})
 return recs,n

# ---- the api programs (paths outside recalc) --------------------------------
def api_parse(stdout):
 """STAGE / CELL / NAME / VAL lines (bar_api.eigs) -> stages in order, answers."""
 stages={}; vals={}; cur=None
 for line in stdout.splitlines():
  p=line.split("\t",2)
  if p[0]=="STAGE": cur=stages.setdefault(p[1],{"cells":{},"names":{}})
  elif p[0]=="CELL": cur["cells"][p[1]]=json.loads(p[2])
  elif p[0]=="NAME": cur["names"][p[1]]=json.loads(p[2])
  elif p[0]=="VAL": k,v,d=json.loads(p[2]); vals[p[1]]={"kind":k,"value":v,"display":d}
 return stages,vals

def csv_matches(calc_fields, mine):
 """A CSV this spreadsheet wrote against Calc's answers for the same range:
 the same shape, and every field by the rule (a field is read as a number, a
 logical, an error or a text by its spelling)."""
 if mine["kind"]!="S": return False
 ours=list(csv.reader(mine["value"].splitlines()))
 if len(calc_fields)!=len(ours) or not ours: return False
 for crow,orow in zip(calc_fields,ours):
  if len(crow)!=len(orow): return False
  for (c,shape),of in zip(crow,orow):
   if of in ("TRUE","FALSE"): m={"kind":"L","value":"1" if of=="TRUE" else "0","display":of}
   else: m={"kind":"N" if decimal(of) is not None else ("E" if calc_class(of)=="error" else "S"),"value":of,"display":of}
   if not matches(c,shape,m): return False
 return True

def range_cells(rng):
 (c0,r0),(c1,r1)=(col_number(x) for x in rng.split(":"))
 return [[col_letters(c)+str(r) for c in range(c0,c1+1)] for r in range(r0,r1+1)]

def api_calc(program, item, stages, tmp):
 """Calc's answer for every calc item of a program that ran: {id: (C, shape)}."""
 got=CalcResult(); csvs={}; contents={}
 ops=item.get("operations",{})
 source=open(os.path.join(API,program),encoding="utf-8").read()
 for stage,op in ops.items():
  if stage not in stages: raise ToolError("%s: operation stage %s was not printed"%(program,stage))
  if op["kind"]=="sort_range":
   needle="sheet.sort_range of [s,"+",".join(str(x) for x in op["args"])+"]"
   if needle not in source: raise ToolError("%s: declared sort is not in program"%program)
  elif op["kind"]=="paste_block":
   copy="sheet.copy_block of [s,"+",".join(str(x) for x in op["copy_args"])+"]"
   paste="sheet.paste_block of [s,cp,"+",".join(str(x) for x in op["paste_args"])+"]"
   if copy not in source or paste not in source: raise ToolError("%s: declared copy/paste is not in program"%program)
  else: raise ToolError("%s: unknown declared operation"%program)
 for stage,dump in stages.items():
  its=[it for it in item["items"] if it["id"].split(":")[0]==stage and "calc" in it]
  if not its: continue
  opt=item.get("stages",{}).get(stage,{}); start=None; names=dump["names"]
  judged=[it["id"].split(":",1)[1] for it in its if it["calc"]=="cell"]
  if stage in ops:
   op=ops[stage]
   if op["kind"]=="sort_range":
    cells=dict(re.findall(r'sheet\.set_cell of \[s,"([A-Z]+\d+)","([^"]*)"\]',source))
   else:
    prior=list(stages).index(stage)-1
    if prior < 0: raise ToolError("%s: paste has no preceding dump"%program)
    cells=stages[list(stages)[prior]]["cells"]
   q={"cells":cells,"operation":op,"judged":judged}
   helper=os.path.join(ROOT,"tests","number_bar_uno.py")
   r=subprocess.run(["/usr/bin/python3",helper],input=json.dumps(q),text=True,capture_output=True,timeout=120)
   if r.returncode: raise ToolError("Calc operation failed: "+r.stderr)
   answer=json.loads(r.stdout)
   for a in judged:
    got[stage+":"+a]=(answer[a]["value"],None); contents[stage+":"+a]=answer[a]["content"]
   continue
  if "start" in opt:
   kind,src=opt["start"].split(":",1)
   text=open(os.path.join(API,src)).read() if kind=="csv" else csvs[src]
   start=calc_read_csv(text,tmp)
   base={a:dump["cells"][a] for a in opt.get("add",[]) if a not in judged}
   f={a:(dump["cells"][a] if a in opt.get("add",[]) else None) for a in judged}; names={}
  else:
   base={a:v for a,v in dump["cells"].items() if a not in judged}
   f={a:dump["cells"].get(a,"") for a in judged}
  for it in its:
   if it["calc"]=="csv-out":
    for a in sum(range_cells(it["range"]),[]):
     if a not in f: f[a]=None if start else dump["cells"].get(a)
  spare={}
  for i,it in enumerate(x for x in its if x["calc"].startswith("=")):
   a="Z%d"%(i+1)
   if a in dump["cells"]: raise ToolError("%s: the spare cell %s is in use"%(program,a))
   f[a]=it["calc"]; spare[it["id"]]=a
  grids=calc_sheet({"base":base,"f":f,"names":names},start)
  cells=calc_cells(grids,[a for a in f])
  for it in its:
   a=it["id"].split(":",1)[1]
   if it["calc"]=="cell": got[it["id"]]=cells[a]
   elif it["calc"]=="csv-out":
    fields=[[cells[x] for x in row] for row in range_cells(it["range"])]
    w=io.StringIO(); csv.writer(w,lineterminator="\n").writerows([[c for c,_ in row] for row in fields])
    csvs[it["id"]]=w.getvalue(); got[it["id"]]=(fields,None)
   else: got[it["id"]]=cells[spare[it["id"]]]
 got.contents=contents
 return got

MISSING={"kind":"CRASH","value":"","display":"<missing>"}

def api_grid(tree, binary, spec):
 """[(program, item, C, shape, answer)] for every expected item, and how many
 programs aborted.  An aborted program's items all differ."""
 out=[]; crashed=0
 if not spec["programs"]: raise ToolError("SET api has no program")
 for program,item in spec["programs"].items():
  if not item.get("items"): raise ToolError("api program %s has no expected item"%program)
  tmp=tempfile.mkdtemp()
  try:
   install(tree,tmp); shutil.copy(os.path.join(API,program),os.path.join(tmp,"app.eigs"))
   try: r=subprocess.run([binary,"app.eigs"],cwd=tmp,text=True,capture_output=True,timeout=120); rc=r.returncode; stdout=r.stdout
   except subprocess.TimeoutExpired: rc=124; stdout=""
   ran=rc==0; crashed+=not ran
   stages,vals=api_parse(stdout) if ran else ({},{})
   lo=api_calc(program,item,stages,tmp) if ran else {}
   for it in item["items"]:
    mine=vals.get(it["id"],MISSING) if ran else MISSING
    if ran and ":" in it["id"]:
     st,ad=it["id"].split(":",1)
     if st in stages and ad in stages[st]["cells"]: mine=dict(mine,content=stages[st]["cells"][ad])
    c,shape=(it["expect"],None) if "rule" in it else lo.get(it["id"],(None,None))
    content=getattr(lo,"contents",{}).get(it["id"])
    out.append((program,it,c,shape,mine,content))
  finally: shutil.rmtree(tmp)
 return out,crashed

def api_verdict(it, c, shape, mine):
 if mine["kind"] in ("CRASH","TIMEOUT") or c is None: return False
 if it.get("calc")=="csv-out": return csv_matches(c,mine)
 return matches(c,shape,mine)

def normal_content(s):
 s=str(s).replace("\r\n","\n").replace("\r","\n").strip()
 try:
  if not s.startswith("=") and Decimal(s).is_finite(): return str(Decimal(s).normalize())
 except InvalidOperation: pass
 return s

# ---- the run ----------------------------------------------------------------
def run_bar(sets, tree, binary, before_doc, out=None, calc=calc_grid, grid=runtime_grid, api=api_grid, log=print):
 """Every set; returns (totals, exit status)."""
 if not sets: raise ToolError("no set to run")
 check_formulas(sets)
 if not has_net(tree): raise ToolError("the tree has no `define net_caught(sheet)`: its own account cannot be reported")
 reraised,sites,rewritten=reraise_tree(tree)
 log("NET-SITES examined=%d rewritten=%d"%(sites,rewritten))
 if not rewritten: shutil.rmtree(reraised); raise ToolError("no reachable catch was rewritten")
 before=None
 if before_doc is not None: check_before(before_doc,sets); before=before_doc["cells"]
 T={"examined":0,"differ":0,"before":0,"net":0,"net_own":0,"net_only_behaviour":0,"net_only_own":0,"crash":0,"rule_examined":0,"rule_differ":0,"ops":0,"content_examined":0,"content_differ":0}; records=[]
 try:
  for name,spec in sets.items():
   if spec.get("reference")=="api":
    got,crashed=api(tree,binary,spec); n={"examined":0,"differ":0,"rule_examined":0,"rule_differ":0,"ops":0,"content_examined":0,"content_differ":0}
    op_seen=set()
    for program,it,c,shape,m,content in got:
     value_ok=api_verdict(it,c,shape,m); pre="rule_" if "rule" in it else ""
     content_bad=content is not None and normal_content(content)!=normal_content(m.get("content",""))
     ok=value_ok and not content_bad
     n[pre+"examined"]+=1; n[pre+"differ"]+=not ok
     if content is not None:
      op_seen.add((program,it["id"].split(":",1)[0])); n["content_examined"]+=1; n["content_differ"]+=content_bad
     records.append({"set":name,"program":program,"id":it["id"],"reference":"rule" if pre else "calc","calc":c,"calc_shape":shape,"calc_content":content,"content":m.get("content"),"kind":m["kind"],"value":m["value"],"display":m["display"],"verdict":"match" if ok else "differ"})
    n["ops"]=len(op_seen)
    for k in n: T[k]+=n[k]
    T["crash"]+=crashed
    log("SET %s examined=%d match=%d differ=%d crash=%d rule_examined=%d rule_differ=%d ops=%d content_examined=%d content_differ=%d"%(name,n["examined"],n["examined"]-n["differ"],n["differ"],crashed,n["rule_examined"],n["rule_differ"],n["ops"],n["content_examined"],n["content_differ"]))
    continue
   lo=calc(spec); mine,own,input_chunks=run_chunks(tree,binary,spec,grid=grid)
   without,_,_=run_chunks(reraised,binary,spec,net=False,grid=grid)
   caught={ad for ad in spec["f"] if mine[ad] != without[ad]}
   calc_inputs=getattr(lo,"inputs",{}); same=0
   for chunk in input_chunks:
    for ad,want in spec.get("base",{}).items():
     c=calc_inputs.get(ad); r=chunk.get(ad)
     declared={"kind":"N" if decimal(want) is not None else "S","value":want,"display":want}
     calc_runtime = c is not None and r is not None and matches(c[0],c[1],r)
     declared_ok = want.startswith("=") or (matches(c[0],c[1],declared) and same_answer(declared,r))
     if not calc_runtime or not declared_ok: raise ToolError("set %s input %s declared=%r Calc=%r runtime=%r"%(name,ad,want,c,r))
     same+=1
   for k in ("input_sets","input_cells","input_chunks","input_same"): T.setdefault(k,0)
   T["input_sets"]+=1; T["input_cells"]+=len(spec.get("base",{})); T["input_chunks"]+=len(input_chunks); T["input_same"]+=same
   recs,n=compare_set(name,spec,mine,caught,own,lo,before); records+=recs
   for k in n: T[k]+=n[k]
   log("SET %s examined=%d match=%d differ=%d before=%d net=%d net_own=%d net_only_behaviour=%d net_only_own=%d crash=%d"%(name,n["examined"],n["examined"]-n["differ"],n["differ"],n["before"],n["net"],n["net_own"],n["net_only_behaviour"],n["net_only_own"],n["crash"]))
 finally: shutil.rmtree(reraised)
 if out:
  with open(out,"w") as fh: json.dump(records,fh,indent=1)
 bad=T["differ"] or T["net"] or T["crash"] or T["rule_differ"]
 return T, (1 if bad else 0)

def main(argv=None):
 ap=argparse.ArgumentParser(); ap.add_argument("--tree",default=ROOT); ap.add_argument("--runtime",default=os.environ.get("EIGENSCRIPT","eigenscript"))
 ap.add_argument("--list",action="store_true"); ap.add_argument("--set"); ap.add_argument("--out"); ap.add_argument("--selftest",action="store_true")
 ap.add_argument("--before",default=os.path.join(DATA,"before.json")); ap.add_argument("--sources",action="store_true")
 ap.add_argument("--write-before",action="store_true",help="write --before from --old-tree on --old-runtime (all formula sets)")
 ap.add_argument("--old-tree"); ap.add_argument("--old-runtime")
 a=ap.parse_args(argv); start=time.monotonic()
 if a.selftest: return selftest(a.tree)
 try:
  sets,d=population(a.tree); arrival=sets.pop("_arrival_counts")
  print("DISPATCHER names=%d rule=%s"%(len(d["rows"]),d["rule"]))
  positions=sum(k!="range" for row in d["rows"].values() for k in row["arguments"])
  left=sum(k=="range" for row in d["rows"].values() for k in row["arguments"])
  print("TEMPLATES functions=%d positions=%d left_out=%d"%(len(d["rows"]),positions,left))
  print("ARRIVALS generated=%d hand=%d same_formula=%d"%(arrival["generated"],arrival["hand"],arrival["same_formula"]))
  print("ARRIVALS no_own_formula=%s"%(",".join(arrival["subsumed"]) or "none"))
  for line in check_formulas(sets): print(line)
  if a.sources:
   spec={"base":BASE,"f":{address(i):"="+x for i,x in enumerate(SOURCES.values())}}
   lo=calc_grid(spec); mine,_,_=run_chunks(a.tree,a.runtime,spec)
   for i,(name,formula) in enumerate(SOURCES.items()):
    ad=address(i); print("SOURCE %s formula=%s calc=%s sheet=%s"%(name,formula,lo[ad][0],mine[ad]["display"]))
   print("SOURCES kinds=%d"%len(SOURCES)); return 0
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
  if not os.path.exists(a.before): raise ToolError("no before file "+a.before+" (write it with --write-before)")
  doc=json.load(open(a.before))
  if a.set: doc={"inputs":({} if a.set=="api" else {a.set:doc["inputs"].get(a.set)}),"cells":{k:v for k,v in doc["cells"].items() if k.split("\t",1)[0]==a.set}}
  check_before(doc,sets)
  if a.set!="api": validate_templates(d)
  T,status=run_bar(sets,a.tree,a.runtime,doc,a.out)
 except ToolError as e:
  print("NUMBER-BAR TOOL-ERROR %s"%e); return 2
 print("INPUTS sets=%d cells=%d chunks=%d same=%d"%(T.get("input_sets",0),T.get("input_cells",0),T.get("input_chunks",0),T.get("input_same",0)))
 print("NUMBER-BAR examined=%d differ=%d before=%d net=%d net_own=%d net_only_behaviour=%d net_only_own=%d crash=%d rule_examined=%d rule_differ=%d wall=%.1fs"%(
  T["examined"],T["differ"],T["before"],T["net"],T["net_own"],T["net_only_behaviour"],T["net_only_own"],T["crash"],T["rule_examined"],T["rule_differ"],time.monotonic()-start))
 return status

# ---- self-test: one-line mutants of this file, no LibreOffice ---------------
def _stub_calc(table):
 return lambda spec: {a:table[a] for a in spec["f"] if a in table}

def _stub_grid(answers, crash=(), caught=()):
 def grid(tree, binary, spec, cells, timeout=0, net=True):
  if any(a in crash for a in cells): return "CRASH"
  out={a:dict(answers[a]) for a in cells}
  if os.path.basename(tree).startswith("number-bar-reraise-"):
   for a in cells:
    if a in caught: out[a]={"kind":"CRASH","value":"","display":""}
  return {"cells":out,"inputs":{},"net":[a for a in cells if a in caught]}
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

def _one(c, mine, shape=None): return dict(f={"A1":"=1"},calc={"A1":(c,shape)},answers={"A1":mine})

def _before_case(m, tree, tmp):
 """before.json written for A1 '=X', A2 '=Y'; then the two formulas swap
 addresses.  Matched by formula, both cells' answers are as before."""
 old={"t":{"base":{},"f":{"A1":"=X","A2":"=Y"},"reference":"calc"}}
 p=os.path.join(tmp,"before.json")
 m.write_before(p,old,tree,"stub",grid=_stub_grid({"A1":N("1"),"A2":N("2")}))
 return _bar(m,tree,{"A1":"=Y","A2":"=X"},{"A1":("9.00000000000000E+00",None),"A2":("9.00000000000000E+00",None)},
             {"A1":N("2"),"A2":N("1")},before=json.load(open(p)))

def _api_case(m, tree, tmp):
 """A runtime that aborts every program: each expected item differs."""
 b=os.path.join(tmp,"abort.sh"); open(b,"w").write("#!/bin/sh\nexit 1\n"); os.chmod(b,0o755)
 sets={"api":{"reference":"api","programs":{"sc-9-canonical.eigs":{"items":[{"id":"canonical:A%d"%i,"calc":"cell"} for i in (1,2,3)]}}}}
 try:
  T,status=m.run_bar(sets,tree,b,None,log=lambda *x:None)
  return "examined=%d differ=%d crash=%d status=%d"%(T["examined"],T["differ"],T["crash"],status)
 except Exception as e:
  if type(e).__name__=="ToolError": return "TOOL-ERROR"
  raise

def _api_content_case(m, tree, tmp):
 sets={"api":{"reference":"api","programs":{"stub.eigs":{"items":[{"id":"sorted:A1","calc":"cell"}]}}}}
 def api(*unused):
  mine={"kind":"N","value":"1","display":"1","content":"=B1"}
  return [("stub.eigs",sets["api"]["programs"]["stub.eigs"]["items"][0],"1.00000000000000E+00",None,mine,"=A1")],0
 T,status=m.run_bar(sets,tree,"stub",None,api=api,log=lambda *x:None)
 return "differ=%d content_differ=%d status=%d"%(T["differ"],T["content_differ"],status)

def _csv_case(m, tree, tmp):
 """Calc's CSV loses its second row: the reader must refuse it."""
 p=os.path.join(tmp,"short.csv"); open(p,"w").write("1,@row1\n")
 try: m.calc_rows(p,2,2); return "read"
 except Exception as e: return "TOOL-ERROR" if type(e).__name__=="ToolError" else repr(e)

def _duplicate_case(m, tree, tmp):
 sets={"t":{"base":{},"f":{"A1":"=1","A2":"=1"},"reference":"calc"}}
 calls=[]
 try:
  m.run_bar(sets,tree,"stub",None,calc=lambda spec:calls.append(1) or {},grid=_stub_grid({}))
  return "accepted evaluations=%d"%len(calls)
 except Exception as e:
  return "%s evaluations=%d"%("TOOL-ERROR" if type(e).__name__=="ToolError" else "BROKEN",len(calls))

def _arrival_duplicate_case(m, tree, tmp):
 try:
  sets,_=m.population(tree); sets.pop("_arrival_counts")
  m.check_formulas(sets); return "unique"
 except Exception as e:
  return str(e) if type(e).__name__=="ToolError" else "BROKEN: %r"%e

def _layout_case(m, tree, tmp):
 try:
  sets,_=m.population(tree); sets.pop("_arrival_counts")
  m.check_formulas(sets)
  return "accepted"
 except Exception as e: return "TOOL-ERROR" if type(e).__name__=="ToolError" else "BROKEN"

def _reference_case(m, tree, tmp):
 sets={"t":{"base":{},"empty":[],"f":{"AA1":"=1","AA2":"=AA1"},"reference":"calc"}}
 try:
  m.check_formulas(sets)
  return "accepted"
 except Exception as e: return "TOOL-ERROR" if type(e).__name__=="ToolError" else "BROKEN"

def _undeclared_case(m, tree, tmp):
 clean={"t":{"base":{},"empty":["B1"],"f":{"AA1":"=B1"},"reference":"calc"}}
 bad={"t":{"base":{},"empty":[],"f":{"AA1":"=B1"},"reference":"calc"}}
 try:
  m.check_formulas(clean)
  m.check_formulas(bad)
  return "accepted"
 except Exception as e: return "TOOL-ERROR" if type(e).__name__=="ToolError" else "BROKEN"

def _input_readback_case(m, tree, tmp):
 sets={"t":{"base":{"B1":"=1"},"empty":[],"f":{"AA1":"=1"},"reference":"calc"}}
 def calc(s):
  out=m.CalcResult({"AA1":("1.00000000000000E+00",None)}); out.inputs={"B1":("2.00000000000000E+00",None)}; return out
 def grid(tree,binary,spec,cells,timeout=0,net=True):
  return {"cells":{"AA1":N("1")},"inputs":{"B1":N("1")},"net":[]}
 try:
  T,status=m.run_bar(sets,tree,"stub",None,calc=calc,grid=grid,log=lambda *x:None)
  return "examined=%d status=%d"%(T["examined"],status)
 except Exception as e: return "TOOL-ERROR" if type(e).__name__=="ToolError" else "BROKEN"

ONE = 'return abs(a - b) <= Decimal(1).scaleb(m.adjusted() - 14)'
PLANTS = [
 ("Calc operation is given the spreadsheet's result content again",
  'content_bad=content is not None and normal_content(content)!=normal_content(m.get("content",""))',
  'content_bad=False', lambda m,t,x:_api_content_case(m,t,x), "differ=1 content_differ=1 status=1"),
 ("behavioural net replaced by identical second-run answers", 'caught={ad for ad in spec["f"] if mine[ad] != without[ad]}', 'caught=set()',
  lambda m,t,x: _bar(m,t,caught={"A1"},**_one("#NUM!",E("#NUM!"))), 'examined=1 differ=1 before=0 net=1 crash=0 status=1'),
 ("Calc input read-back skipped while workbook input is overwritten", 'calc_runtime = c is not None and r is not None and matches(c[0],c[1],r)', 'calc_runtime = True',
  lambda m,t,x: _input_readback_case(m,t,x), "TOOL-ERROR"),
 ("formula region moved over inputs", " col=\"\"; n=i//500+27", " col=\"\"; n=i//500+1",
  lambda m,t,x: _layout_case(m,t,x), "accepted"),
 ("a formula refers to another formula cell", 'if bad: raise ToolError("set %s formula %s refers to formula cell %s"%(name,ad,bad[0]))', 'if False: raise ToolError("set %s formula %s refers to formula cell %s"%(name,ad,bad[0]))',
  lambda m,t,x: _reference_case(m,t,x), "TOOL-ERROR"),
 ("generated arrivals not de-duplicated", "    if formula in by_formula:", "    if False:",
  lambda m,t,x: _arrival_duplicate_case(m,t,x), "unique"),
 ("duplicate check delayed until after evaluation", ' check_formulas(sets)\n if not has_net(tree):',
  " calc(next(spec for spec in sets.values() if spec.get('reference')!='api')); check_formulas(sets)\n if not has_net(tree):",
  lambda m,t,x: _duplicate_case(m,t,x), "TOOL-ERROR evaluations=0"),
 ("a non-numeric-labelled scalar position silently dropped", 'if k!="range"]', 'if k=="number"]',
  lambda m,t,x: str(len(m.marked_templates({"call":"IF(1,2,3)","arguments":["logical","number","number"]},"IF"))), "3"),
 ("a generated arrival path skipped", "  for path in paths: out.append((i,path,name+\"(\"+\",\".join(args[:i]+[\"@\"]+args[i+1:])+\")\"))",
  "  for path in paths[:-1]: out.append((i,path,name+\"(\"+\",\".join(args[:i]+[\"@\"]+args[i+1:])+\")\"))",
  lambda m,t,x: str(len(m.arrival_templates({"call":"MATCH(1,B1:B3,0)","arguments":["number","range","number"],"paths":[["formula-reference","comparison-left","comparison-right","lookup-key"],["inside-range"],["formula-reference","comparison-left","comparison-right"]]},"MATCH"))), "8"),
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
 ("a net-caught cell counted as a match", "ok=matches(c,shape,m) and not net", "ok=matches(c,shape,m)",
  lambda m,t,x: _bar(m,t,caught={"A1"},**_one("#NUM!",E("#NUM!"))), 'examined=1 differ=1 before=0 net=1 crash=0 status=1'),
 ("run_chunks gives every cell of a failed chunk a value", "one=grid(tree,binary,spec,[ad],timeout=10,net=net)",
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
 ("an aborted api program counted as zero differing lines", 'for it in item["items"]:', 'for it in (item["items"] if ran else []):',
  lambda m,t,x: _api_case(m,t,x), "examined=3 differ=3 crash=1 status=1"),
 ("a before.json key matched by address instead of formula", 'return set_name+"\\t"+formula', 'return set_name+"\\t"+address',
  lambda m,t,x: _before_case(m,t,x), 'examined=2 differ=2 before=2 net=0 crash=0 status=1'),
]
CONTROLS = [
 ("an undeclared referenced cell is refused after a clean declaration is accepted", _undeclared_case, "TOOL-ERROR"),
 ("a 17th-digit difference matches", lambda m,t,x: _bar(m,t,**_one("1.00000000000000E+00",N("1.0000000000000002"))),
  "examined=1 differ=0 before=0 net=0 crash=0 status=0"),
 ("Err:502 matches #NUM!", lambda m,t,x: _bar(m,t,**_one("Err:502",E("#NUM!"))), "examined=1 differ=0 before=0 net=0 crash=0 status=0"),
 ("a text in the number spelling matches only as that text", lambda m,t,x: (_bar(m,t,**_one("1.00000000000000E+00",{"kind":"S","value":"1.00000000000000E+00","display":"1.00000000000000E+00"},"TEXT")),
  _bar(m,t,**_one("1.00000000000000E+00",N("1"),"TEXT"))), ("examined=1 differ=0 before=0 net=0 crash=0 status=0","examined=1 differ=1 before=0 net=0 crash=0 status=1")),
 ("a logical matches only as a logical", lambda m,t,x: (_bar(m,t,**_one("1.00000000000000E+00",{"kind":"L","value":"1","display":"TRUE"},"TRUE")),
  _bar(m,t,**_one("1.00000000000000E+00",N("1"),"TRUE"))), ("examined=1 differ=0 before=0 net=0 crash=0 status=0","examined=1 differ=1 before=0 net=0 crash=0 status=1")),
]

def _load(path, name):
 """The file as a module; a copy elsewhere still reads this tree's data."""
 import importlib.util
 spec=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
 m.ROOT,m.DATA,m.API=ROOT,DATA,API; return m

def _run(case, m, tree, tmp):
 """A case's outcome; a case that raises is BROKEN, which is never a catch."""
 try: return case(m,tree,tmp)
 except Exception as e: return "BROKEN: %r"%e

def selftest(tree):
 src=open(os.path.abspath(__file__),encoding="utf-8").read(); tmp=tempfile.mkdtemp(); failed=0; examined=0
 # anchors are looked for, and edited, only above this section (the table holds them too)
 cut=src.index("# ---- self-test: one-line mutants"); body,rest=src[:cut],src[cut:]
 try:
  clean=_load(os.path.abspath(__file__),"bar_clean")
  for name,case,want in CONTROLS:
   got=_run(case,clean,tree,tmp); examined+=1
   if got!=want: failed+=1; print("FAIL: control %s: %r, wanted %r"%(name,got,want))
   else: print("PASS: control %s: %s"%(name,got))
  for i,(name,anchor,repl,case,right) in enumerate(PLANTS):
   examined+=1; n=body.count(anchor)
   if n!=1: failed+=1; print("FAIL: %s: anchor found %d times"%(name,n)); continue
   p=os.path.join(tmp,"mutant%d.py"%i); open(p,"w",encoding="utf-8").write(body.replace(anchor,repl)+rest)
   want=_run(case,clean,tree,tmp)
   if want!=right: failed+=1; print("FAIL: %s: the clean tool gives %r, wanted %r"%(name,want,right)); continue
   got=_run(case,_load(p,"bar_mutant%d"%i),tree,tmp)
   if got.startswith("BROKEN"): failed+=1; print("FAIL: %s: the mutant broke the case: %s"%(name,got))
   elif got==want: failed+=1; print("FAIL: %s: the mutant gives the clean result %r"%(name,got))
   else: print("PASS: %s: clean %s; mutant %s"%(name,want,got))
 finally: shutil.rmtree(tmp)
 total=len(CONTROLS)+len(PLANTS)
 if not (examined==total>0): failed+=1
 print("SELFTEST examined=%d of %d failed=%d"%(examined,total,failed))
 return 1 if failed else 0

if __name__=="__main__": sys.exit(main())
