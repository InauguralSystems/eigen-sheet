SET class examined=14976 match=11090 differ=3886 left_out=0 before=1972 net=234 net_own=234 net_only_behaviour=0 net_only_own=0 crash=0
SET wrappers examined=560 match=328 differ=232 left_out=0 before=100 net=0 net_own=0 net_only_behaviour=0 net_only_own=0 crash=0
SET number-text examined=280 match=159 differ=121 left_out=0 before=111 net=0 net_own=0 net_only_behaviour=0 net_only_own=0 crash=0
SET arrivals-generated examined=7800 match=6750 differ=1050 left_out=0 before=0 net=39 net_own=39 net_only_behaviour=0 net_only_own=0 crash=0
SET c-sumif examined=7 match=7 differ=0 left_out=0 before=0 net=0 net_own=0 net_only_behaviour=0 net_only_own=0 crash=0
SET c1 examined=12 match=12 differ=0 left_out=0 before=0 net=0 net_own=0 net_only_behaviour=0 net_only_own=0 crash=0
SET c10 examined=22 match=17 differ=5 left_out=0 before=5 net=0 net_own=0 net_only_behaviour=0 net_only_own=0 crash=0
SET c20 examined=113 match=66 differ=47 left_out=1 before=27 net=17 net_own=17 net_only_behaviour=0 net_only_own=0 crash=0
SET c22 examined=54 match=48 differ=6 left_out=2 before=6 net=0 net_own=0 net_only_behaviour=0 net_only_own=0 crash=0
SET c23 examined=19 match=10 differ=9 left_out=0 before=0 net=0 net_own=0 net_only_behaviour=0 net_only_own=0 crash=0
SET c24 examined=15 match=11 differ=4 left_out=1 before=0 net=0 net_own=0 net_only_behaviour=0 net_only_own=0 crash=0
SET c25 examined=3 match=1 differ=2 left_out=0 before=0 net=0 net_own=0 net_only_behaviour=0 net_only_own=0 crash=0
SET c4 examined=46 match=42 differ=4 left_out=0 before=2 net=0 net_own=0 net_only_behaviour=0 net_only_own=0 crash=0
SET c5 examined=14 match=13 differ=1 left_out=0 before=1 net=0 net_own=0 net_only_behaviour=0 net_only_own=0 crash=0
SET c6 examined=18 match=15 differ=3 left_out=0 before=3 net=0 net_own=0 net_only_behaviour=0 net_only_own=0 crash=0
SET c7 examined=12 match=9 differ=3 left_out=0 before=1 net=2 net_own=2 net_only_behaviour=0 net_only_own=0 crash=0
SET c8 examined=6 match=5 differ=1 left_out=0 before=0 net=1 net_own=1 net_only_behaviour=0 net_only_own=0 crash=0
SET c9 examined=6 match=6 differ=0 left_out=0 before=0 net=0 net_own=0 net_only_behaviour=0 net_only_own=0 crash=0
SET api examined=42 match=28 differ=14 no_oracle=5 crash=3 rule_examined=2 rule_differ=0 ops=2 content_examined=9 content_differ=3 api_calc_asked=42 api_calc_not_asked=5
INPUTS sets=18 cells=131 chunks=133 same=1841
NUMBER-BAR examined=24005 differ=5388 no_oracle=5 left_out=calc-lacks-form:2,calc-approximate-equality:2 shape_changed=0 before=2228 net=293 net_own=293 net_only_behaviour=0 net_only_own=0 crash=3 rule_examined=2 rule_differ=0 api_calc_asked=42 api_calc_not_asked=5 wall=479.2s
LEFT-OUT c20:A88 formula==XLOOKUP(D1,D1:D2,D1:D2) rule=calc-lacks-form
LEFT-OUT c22:A45 formula==B1-B2 rule=calc-approximate-equality
LEFT-OUT c22:A47 formula==(B2+1)-B2 rule=calc-approximate-equality
LEFT-OUT c24:A14 formula==XLOOKUP(B3,B1:B3,C1:C3) rule=calc-lacks-form
NO-ORACLE sc-2-pivot.eigs:pivot:O2 reason=program aborted before stage
NO-ORACLE sc-2-pivot.eigs:pivot:O3 reason=program aborted before stage
NO-ORACLE sc-3-pivot-avg.eigs:pivot:O2 reason=program aborted before stage
NO-ORACLE sc-3-pivot-avg.eigs:pivot:O3 reason=program aborted before stage
NO-ORACLE sc-3-pivot-avg.eigs:pivot:O4 reason=program aborted before stage
differ moved from 5397 to 5388: four cells became named Calc exclusions and five aborted-stage API items became no-oracle (5397 - 4 - 5 = 5388); nothing else moved.
