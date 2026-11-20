# Number-boundary bar baseline for #104

Formula cells occupy `AA1` onward; declared inputs remain at their original addresses.

## Provenance

NEW was EigenScript tag `phase2-consumers-1`, commit `b9881574b20503c5cfbdb6d80a5e6008e7501e15`, built with `make -s zlib` as the `calc-oracle` workflow builds it. The spreadsheet and tool tree was based on commit `d9963a12642311941a165b5f46e5adff5e9e8966`; the tool is the version in the commit containing this file. The full run had tool wall `756.3s`.

## Full NEW run

Command: `python3 tests/number_bar.py --runtime /tmp/eigs-bar8/build/zlib/eigenscript`

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
SET api examined=47 match=31 differ=16 crash=3 rule_examined=2 rule_differ=0
INPUTS sets=18 cells=131 chunks=133 same=1841
NUMBER-BAR examined=24014 differ=5394 before=2232 net=293 net_own=293 net_only_behaviour=0 net_only_own=0 crash=3 rule_examined=2 rule_differ=0 wall=756.3s
```

## Movement from the prior bar

Behavioural `net` remains 293 and `differ` remains 5,394 because every clean-tree behavioural catch agrees with the spreadsheet account; unlike the prior bar, those counts no longer trust that account.

## Movement from the prior 7,430 differences

`class` moved 4,945 -> 3,886; `arrivals-generated` moved 2,027 -> 1,050. Every other set was unchanged: `wrappers` 232, `number-text` 121, `c-sumif` 0, `c1` 0, `c10` 5, `c20` 48, `c22` 8, `c23` 9, `c24` 5, `c25` 2, `c4` 4, `c5` 1, `c6` 3, `c7` 3, `c8` 1, `c9` 0, and `api` 16. Total `differ` moved 7,430 -> 5,394.
