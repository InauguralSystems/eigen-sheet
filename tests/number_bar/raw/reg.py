import sys
def iserr(s): return s.startswith("#") or s.startswith("Err:")
def ok(v,calc): return (not v.startswith("CRASH")) and (v==calc or (iserr(v) and iserr(calc)))
tot={"rows":0,"t3ok":0,"t3crash":0,"t3bad":0,"regr_vs_tree2":0,"regr_vs_before":0,"fixed_vs_tree2":0,"t3err_calcnum":0}
for p in sys.argv[1:]:
    rows=[l.rstrip("\n").split("\t") for l in open(p)]
    rows=[r for r in rows if len(r)>=6 and r[0][:1]=="A" and r[0]!="addr"]
    loc={k:0 for k in tot}; reg=[]
    for r in rows:
        calc,t3,t2,b0=r[2],r[3],r[4],r[5]
        loc["rows"]+=1
        if t3.startswith("CRASH"): loc["t3crash"]+=1
        if ok(t3,calc): loc["t3ok"]+=1
        else: loc["t3bad"]+=1
        if iserr(t3) and not iserr(calc) and calc not in ("","<blank>"): loc["t3err_calcnum"]+=1
        if ok(t2,calc) and not ok(t3,calc): loc["regr_vs_tree2"]+=1; reg.append(r)
        if ok(b0,calc) and not ok(t3,calc): loc["regr_vs_before"]+=1
        if ok(t3,calc) and not ok(t2,calc): loc["fixed_vs_tree2"]+=1
    for k in tot: tot[k]+=loc[k]
    print(p.split("/")[-1], loc)
    if "-v" in sys.argv[0:1] or True:
        for r in reg[:200]: print("    REGRESSION vs tree2:", r[1], "| Calc", r[2], "| tree3", r[3], "| tree2", r[4], "| before+OLD", r[5][:40])
print("TOTAL", tot)
