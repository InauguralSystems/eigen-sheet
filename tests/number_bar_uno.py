#!/usr/bin/python3
"""Run one Calc sort or copy/paste and return cell contents and displays."""
import json, os, shutil, subprocess, sys, tempfile, time, uno

def connect(port, profile):
 p=subprocess.Popen(["libreoffice","--headless","--norestore","--nodefault",
  "--accept=socket,host=127.0.0.1,port=%d;urp;"%port,
  "-env:UserInstallation=file://"+profile], env=dict(os.environ,SAL_USE_VCLPLUGIN="svp"),
  stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
 ctx=uno.getComponentContext(); resolver=ctx.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver",ctx)
 for _ in range(120):
  try: return p,resolver.resolve("uno:socket,host=127.0.0.1,port=%d;urp;StarOffice.ComponentContext"%port)
  except Exception:
   if p.poll() is not None: raise RuntimeError(p.stderr.read().decode(errors="replace"))
   time.sleep(.1)
 raise RuntimeError("Calc UNO bridge did not start")

def main():
 q=json.load(sys.stdin); profile=tempfile.mkdtemp(prefix="number-bar-uno-"); port=21000+(os.getpid()%10000)
 p,ctx=connect(port,profile)
 try:
  desktop=ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop",ctx)
  doc=desktop.loadComponentFromURL("private:factory/scalc","_blank",0,()); sheet=doc.Sheets[0]
  for a,v in q["cells"].items(): sheet.getCellRangeByName(a).Formula=v
  op=q["operation"]
  if op["kind"]=="sort_range":
   c0,r0,c1,r1,key,desc=op["args"]; rng=sheet.getCellRangeByPosition(min(c0,c1),min(r0,r1),max(c0,c1),max(r0,r1))
   field=uno.createUnoStruct("com.sun.star.util.SortField"); field.Field=key; field.SortAscending=not bool(desc)
   sd=list(rng.createSortDescriptor())
   for prop in sd:
    if prop.Name=="SortFields": prop.Value=uno.Any("[]com.sun.star.util.SortField",(field,))
   rng.sort(tuple(sd))
  else:
   c0,r0,c1,r1=op["copy_args"]; tc,tr=op["paste_args"]
   src=sheet.getCellRangeByPosition(min(c0,c1),min(r0,r1),max(c0,c1),max(r0,r1))
   dst=sheet.getCellByPosition(tc,tr); sheet.copyRange(dst.CellAddress,src.RangeAddress)
  formats=doc.NumberFormats; locale=uno.createUnoStruct("com.sun.star.lang.Locale")
  key=formats.queryKey("0.00000000000000E+00",locale,True)
  if key == -1: key=formats.addNew("0.00000000000000E+00",locale)
  for a in q["judged"]: sheet.getCellRangeByName(a).NumberFormat=key
  doc.calculateAll(); out={}
  for a in q["judged"]:
   c=sheet.getCellRangeByName(a); out[a]={"content":c.Formula,"value":c.String}
  print(json.dumps(out)); doc.close(True)
 finally:
  p.terminate(); p.wait(timeout=10); shutil.rmtree(profile)
 return 0
if __name__=="__main__": raise SystemExit(main())
