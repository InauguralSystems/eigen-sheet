#!/usr/bin/env python3
"""mkplant.py <name>: copy tree3 to scratch/pass3/plants/<name> and apply one plant to sheet.eigs."""
import shutil, sys, os
D="REVIEW_DIR"
name=sys.argv[1]; dst=D+"/scratch/pass3/plants/"+name
if os.path.exists(dst): shutil.rmtree(dst)
shutil.copytree(D+"/tree3", dst, ignore=shutil.ignore_patterns("__pycache__"))
p=dst+"/sheet.eigs"; s=open(p).read()
def rep(a,b):
    global s
    assert s.count(a)==1, (name, a, s.count(a)); s=s.replace(a,b)
RANGE_OLD="            append of [out, _formula_number of [st, _ref_val of [st, c, r]]]\n"
RANGE_NEW="            append of [out, _ref_val of [st, c, r]]\n"
FACT_OLD="    local v is _eval_factor_raw of st\n    if st.err != \"\":\n        return v\n    return _formula_number of [st, v]\n"
FACT_NEW="    local v is _eval_factor_raw of st\n    return v\n"
NET_OLD="""        try:
            v is _eval_st of [st, formula_toks[addr], addr]
        catch eval_error:
            # This last-resort boundary classifies an otherwise uncaught
            # runtime failure as #NUM!. Expected type/reference errors are
            # produced explicitly by the evaluator before reaching this net.
            st.err is "#NUM!"
"""
NET_NEW="        v is _eval_st of [st, formula_toks[addr], addr]\n"
FIN_OLD="""        if v != v or v > 1.7976931348623157e308 or v < -1.7976931348623157e308:
            if st.err == "":
                st.err is "#NUM!"
            return 0
"""
FIN_NEW=""
MASK_R="    # kept for the probe: _formula_number of [st, _ref_val\n"
MASK_F="    # kept for the probe: _formula_number of [st, v]\n"
MASK_C="        # kept for the probe: try: catch eval_error:\n"
MASK_N="    # kept for the probe: v != v 1.7976931348623157e308\n"
if name=="R-honest": rep(RANGE_OLD,RANGE_NEW)
elif name=="R-masked": rep(RANGE_OLD,RANGE_NEW+MASK_R.replace("    ","            ",1))
elif name=="F-honest": rep(FACT_OLD,FACT_NEW)
elif name=="F-masked": rep(FACT_OLD,FACT_NEW+MASK_F)
elif name=="C-honest": rep(NET_OLD,NET_NEW); rep(RANGE_OLD,RANGE_NEW)
elif name=="C-masked": rep(NET_OLD,NET_NEW+MASK_C); rep(RANGE_OLD,RANGE_NEW+"            # _formula_number of [st, _ref_val\n")
elif name=="C-only": rep(NET_OLD,NET_NEW)
elif name=="C-only-masked": rep(NET_OLD,NET_NEW+MASK_C)
elif name=="N-honest": rep(FIN_OLD,FIN_NEW)
elif name=="N-masked": rep(FIN_OLD,MASK_N.replace("    ","        ",1))
elif name=="N-noop":
    # _formula_number is called everywhere and does nothing: returns its input unchanged
    rep("define _formula_number(st, v) as:\n","define _formula_number(st, v) as:\n    if 1 == 1:\n        return v\n")
elif name=="R-and-F-masked": rep(RANGE_OLD,RANGE_NEW+"            # _formula_number of [st, _ref_val\n"); rep(FACT_OLD,FACT_NEW+MASK_F)
else: raise SystemExit("unknown plant")
open(p,"w").write(s); print("planted", name, dst)
