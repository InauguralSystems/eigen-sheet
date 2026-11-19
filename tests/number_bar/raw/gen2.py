import json, sys
# Every numeric slot of every function the dispatcher has (list derived by grep of 'fname == "..."' in tree2/sheet.eigs).
T = ['ABS(@)','INT(@)','TRUNC(@)','ROUND(@,0)','ROUND(1.5,@)','ROUNDUP(@,0)','ROUNDDOWN(@,0)','SIGN(@)','SQRT(@)','MOD(@,2)','MOD(5,@)',
 'POWER(@,2)','POWER(2,@)','CEILING(@,1)','CEILING(5,@)','FLOOR(@,1)','FLOOR(5,@)',
 'DATE(@,1,1)','DATE(2020,@,1)','DATE(2020,1,@)','YEAR(@)','MONTH(@)','DAY(@)','WEEKDAY(@)','WEEKDAY(100,@)','EDATE(@,1)','EDATE(100,@)',
 'EOMONTH(@,1)','EOMONTH(100,@)','DATEVALUE(@)','DATEDIF(@,100,"d")','DATEDIF(1,@,"d")','TIME(@,0,0)','TIME(0,@,0)','HOUR(@)','MINUTE(@)','SECOND(@)',
 'ISEVEN(@)','ISODD(@)','TEXT(@,"0.00")','TEXT(@,"#,##0")',
 'SUM(@,1)','AVERAGE(@,1)','MIN(@,1)','MAX(@,1)','PRODUCT(@,2)','COUNT(@,1)','COUNTA(@,1)','MEDIAN(@,1)','MODE(@,1,1)','VAR(@,1)','STDEV(@,1)','VARP(@,1)','STDEVP(@,1)',
 'PMT(@,10,1000)','PMT(0.05,@,1000)','PMT(0.05,10,@)','FV(@,10,-100)','FV(0.05,@,-100)','PV(0.05,10,@)','NPER(@,-100,1000)','NPER(0.05,@,1000)','NPV(@,100,200)','NPV(0.1,@,200)',
 'RATE(@,-100,1000)','IPMT(0.05,1,@,1000)','PPMT(0.05,1,10,@)','IRR(@)',
 'SUMPRODUCT(@,2)','RANK(@,B1:B3)','PERCENTILE(B1:B3,@)','SUMIF(B1:B3,">0",@)','COUNTIF(B1:B3,@)',
 'CHAR(@)','REPT("a",@)','LEFT("abc",@)','RIGHT("abc",@)','MID("abc",@,1)','MID("abc",1,@)','FIND("a","abc",@)','SUBSTITUTE("aa","a","b",@)','REPLACE("abc",@,1,"z")',
 'LEN(@)','VALUE(@)','N(@)','CONCATENATE(@,"x")','TEXTJOIN(",",@,"a")',
 'INDEX(B1:B3,@)','MATCH(@,B1:B3,0)','VLOOKUP(@,B1:C3,2,0)','HLOOKUP(@,B1:C3,1,0)','XLOOKUP(@,B1:B3,C1:C3)','LOOKUP(@,B1:B3)',
 'IF(@,1,2)','AND(@)','OR(@)','NOT(@)','XOR(@,1)','IFS(@,1)','SWITCH(@,1,"a","b")']
BAD = {"OVF": "1E300*1E10", "DIV": "1/0", "LN0": "LN(0)", "INF": "POWER(10,400)", "INF2": "0.5^-2000", "NAN": "POWER(-1,0.5)", "SUMINF": "SUM(1E308,1E308)"}
fam = sys.argv[1]; x = BAD[fam]
f = {}; r = 1
for t in T:
    e = t.replace("@", x)
    for v in ("=" + e, "=ABS(" + e + ")", "=IFERROR(" + e + ",7101)", "=IFERROR(ABS(" + e + "),7101)"):
        f["A%d" % r] = v; r += 1
json.dump({"base": {"B1": "1", "B2": "2", "B3": "3", "C1": "10", "C2": "20", "C3": "30"}, "f": f}, sys.stdout)
print(len(T), file=sys.stderr)
