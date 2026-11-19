import sys
def iserr(s): return s.startswith("#") or s.startswith("Err:")
def cls(v,calc):
    if v.startswith("CRASH"): return "CRASH"
    if v==calc: return "same"
    if iserr(v) and iserr(calc): return "botherr"
    return "MISMATCH"
for p in sys.argv[1:]:
    lines=[l.rstrip("\n").split("\t") for l in open(p)]
    hdr=lines[0]; rows=[r for r in lines if r and r[0].startswith("A") and len(r)>=4 and r[0]!="addr"]
    cnt={}; det=[]
    for r in rows:
        calc=r[2]; c3=cls(r[3],calc); c2=cls(r[4],calc) if len(r)>4 else "-"; c0=cls(r[5],calc) if len(r)>5 else "-"
        cnt[c3]=cnt.get(c3,0)+1
        if c3 in ("CRASH","MISMATCH"): det.append((r,c2,c0))
    errnum=sum(1 for r in rows if iserr(r[3]) and not iserr(r[2]) and r[2] not in ("","<blank>"))
    print("== %s: rows=%d tree3: %s ; tree3 shows an error where Calc shows a value: %d" % (p.split("/")[-1],len(rows),cnt,errnum))
    for r,c2,c0 in det:
        print("   %-45s Calc=%-24s tree3=%-24s tree2=%s[%s] before+OLD=%s[%s]" % (r[1],r[2],r[3][:40],r[4][:30] if len(r)>4 else "",c2,r[5][:30] if len(r)>5 else "",c0))
