# Number-boundary bar baseline for #104

This is measured output, not an expected-value source. LibreOffice Calc owns every expected display in the Calc-referenced sets. The comparison is exact display text equality; different numeric spellings and different errors differ. `known_before` means OLD differed from Calc and OLD's EigenScript display was exactly NEW's display. `new` is `differ - known_before`.

NEW is EigenScript tag `phase2-consumers-1`, commit `b9881574b20503c5cfbdb6d80a5e6008e7501e15`, run against eigen-sheet `d558f137c8064d0651c6abd36d44a6a7a295fe0e`. OLD is tag `v0.48.0`, commit `546848c0a7123ea7066923ebadb06f0af29af953`, run against the plain main clone at `3d43f211130d02774159e287a7cf84986639a1a3`.

The final NEW run took 109.8 seconds of tool wall time (1m50.819s shell wall time):

```text
DISPATCHER names=115 rule=unique names matching fname == "NAME" in sheet.eigs; repeated clauses and aliases explain 229 textual tests versus 115 reachable names
SET class examined=5418 match=3956 differ=1462 known_before=948 new=514 kinds=error-for-value:1054,error-kind:164,text:220,value-for-error:24 net=unknown
SET wrappers examined=630 match=304 differ=326 known_before=175 new=151 kinds=error-for-value:229,error-kind:70,text:27 net=unknown
SET number-text examined=280 match=143 differ=137 known_before=123 new=14 kinds=text:137 net=unknown
SET c-sumif examined=7 match=7 differ=0 known_before=0 new=0 kinds= net=unknown
SET c1 examined=12 match=9 differ=3 known_before=3 new=0 kinds=error-kind:3 net=unknown
SET c10 examined=22 match=17 differ=5 known_before=5 new=0 kinds=error-for-value:3,error-kind:2 net=unknown
SET c20 examined=114 match=20 differ=94 known_before=72 new=22 kinds=error-for-value:15,error-kind:10,text:49,value-for-error:20 net=unknown
SET c22 examined=56 match=44 differ=12 known_before=11 new=1 kinds=error-for-value:1,text:11 net=unknown
SET c23 examined=19 match=8 differ=11 known_before=1 new=10 kinds=error-for-value:9,error-kind:1,text:1 net=unknown
SET c24 examined=16 match=11 differ=5 known_before=1 new=4 kinds=error-for-value:1,text:3,value-for-error:1 net=unknown
SET c25 examined=3 match=1 differ=2 known_before=0 new=2 kinds=error-for-value:2 net=unknown
SET c4 examined=46 match=40 differ=6 known_before=4 new=2 kinds=error-for-value:2,error-kind:3,text:1 net=unknown
SET c5 examined=14 match=9 differ=5 known_before=5 new=0 kinds=text:5 net=unknown
SET c6 examined=18 match=15 differ=3 known_before=3 new=0 kinds=error-for-value:3 net=unknown
SET c7 examined=12 match=0 differ=12 known_before=8 new=4 kinds=error-for-value:2,text:10 net=unknown
SET c8 examined=6 match=0 differ=6 known_before=5 new=1 kinds=error-for-value:1,text:5 net=unknown
SET c9 examined=6 match=6 differ=0 known_before=0 new=0 kinds= net=unknown
NUMBER-BAR examined=6679 differ=2089 known_before=1364 new=725 net=unknown wall=109.8s
```

The per-cell catch cannot be observed from outside recalc, so every formula set honestly remains `net=unknown`; the builder who repairs that layer must add the counter.
