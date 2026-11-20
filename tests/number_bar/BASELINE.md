# Number-boundary bar baseline for #104

```text
DISPATCHER names=115 rule=One Calc-valid fullest call per dispatcher function. arguments labels every position the implementation reads; all scalar positions are expanded, while reference-only range positions are counted left_out. Each row cites its fullest-call source.
TEMPLATES functions=115 positions=208 left_out=26
ARRIVALS generated=7800 hand=351 same_formula=120
ARRIVALS no_own_formula=criterion,lookup-key
FORMULAS set=class examined=14976 duplicates=0
FORMULAS set=wrappers examined=560 duplicates=0
FORMULAS set=number-text examined=280 duplicates=0
FORMULAS set=arrivals-generated examined=7800 duplicates=0
FORMULAS set=c-sumif examined=7 duplicates=0
FORMULAS set=c1 examined=12 duplicates=0
FORMULAS set=c10 examined=22 duplicates=0
FORMULAS set=c20 examined=114 duplicates=0
FORMULAS set=c22 examined=56 duplicates=0
FORMULAS set=c23 examined=19 duplicates=0
FORMULAS set=c24 examined=16 duplicates=0
FORMULAS set=c25 examined=3 duplicates=0
FORMULAS set=c4 examined=46 duplicates=0
FORMULAS set=c5 examined=14 duplicates=0
FORMULAS set=c6 examined=18 duplicates=0
FORMULAS set=c7 examined=12 duplicates=0
FORMULAS set=c8 examined=6 duplicates=0
FORMULAS set=c9 examined=6 duplicates=0
FORMULAS set=arrivals-hand-overlap examined=351 duplicates=0
NET-SITES examined=1 rewritten=1
SET class examined=14976 match=11090 differ=3886 before=1972 net=234 net_own=234 net_only_behaviour=0 net_only_own=0 crash=0
SET wrappers examined=560 match=328 differ=232 before=100 net=0 net_own=0 net_only_behaviour=0 net_only_own=0 crash=0
SET number-text examined=280 match=159 differ=121 before=111 net=0 net_own=0 net_only_behaviour=0 net_only_own=0 crash=0
SET arrivals-generated examined=7800 match=6750 differ=1050 before=0 net=39 net_own=39 net_only_behaviour=0 net_only_own=0 crash=0
SET c-sumif examined=7 match=7 differ=0 before=0 net=0 net_own=0 net_only_behaviour=0 net_only_own=0 crash=0
SET c1 examined=12 match=12 differ=0 before=0 net=0 net_own=0 net_only_behaviour=0 net_only_own=0 crash=0
SET c10 examined=22 match=17 differ=5 before=5 net=0 net_own=0 net_only_behaviour=0 net_only_own=0 crash=0
SET c20 examined=114 match=66 differ=48 before=28 net=17 net_own=17 net_only_behaviour=0 net_only_own=0 crash=0
SET c22 examined=56 match=48 differ=8 before=8 net=0 net_own=0 net_only_behaviour=0 net_only_own=0 crash=0
SET c23 examined=19 match=10 differ=9 before=0 net=0 net_own=0 net_only_behaviour=0 net_only_own=0 crash=0
SET c24 examined=16 match=11 differ=5 before=1 net=0 net_own=0 net_only_behaviour=0 net_only_own=0 crash=0
SET c25 examined=3 match=1 differ=2 before=0 net=0 net_own=0 net_only_behaviour=0 net_only_own=0 crash=0
SET c4 examined=46 match=42 differ=4 before=2 net=0 net_own=0 net_only_behaviour=0 net_only_own=0 crash=0
SET c5 examined=14 match=13 differ=1 before=1 net=0 net_own=0 net_only_behaviour=0 net_only_own=0 crash=0
SET c6 examined=18 match=15 differ=3 before=3 net=0 net_own=0 net_only_behaviour=0 net_only_own=0 crash=0
SET c7 examined=12 match=9 differ=3 before=1 net=2 net_own=2 net_only_behaviour=0 net_only_own=0 crash=0
SET c8 examined=6 match=5 differ=1 before=0 net=1 net_own=1 net_only_behaviour=0 net_only_own=0 crash=0
SET c9 examined=6 match=6 differ=0 before=0 net=0 net_own=0 net_only_behaviour=0 net_only_own=0 crash=0
SET api examined=47 match=28 differ=19 crash=3 rule_examined=2 rule_differ=0 ops=2 content_examined=9 content_differ=3
INPUTS sets=18 cells=131 chunks=133 same=1841
NUMBER-BAR examined=24014 differ=5397 before=2232 net=293 net_own=293 net_only_behaviour=0 net_only_own=0 crash=3 rule_examined=2 rule_differ=0 wall=469.9s
```

`differ` moved from 5394 to 5397 because Calc independently sorted the block and exposed three clean content/value differences that the old re-evaluation could not detect.
