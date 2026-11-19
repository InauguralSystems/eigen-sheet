# Number-boundary bar baseline for #104

This file records the tool's output. LibreOffice Calc 24.2 supplied the expected answers.

## Provenance

NEW was EigenScript tag `phase2-consumers-1`, commit `b9881574b20503c5cfbdb6d80a5e6008e7501e15`. OLD was tag `v0.48.0`, commit `546848c0a7123ea7066923ebadb06f0af29af953`. Both were built with `make -s zlib`, as the `calc-oracle` workflow builds NEW. The tested tree was commit `b3171f6a13f43f477c10a0d59ad882deaf49a2a4`; the plain main tree used with OLD was commit `3d43f211130d02774159e287a7cf84986639a1a3`.

The OLD derivation printed tool wall `2409.3s` and shell wall `40m10.316s`. The NEW full run printed tool wall `207.3s` and shell wall `3m28.340s`.

## Population and sources

```text
TEMPLATES functions=115 positions=208 left_out=26
ARRIVALS generated=7800 hand=351 same_formula=120
ARRIVALS no_own_formula=criterion,lookup-key
SOURCE floating-overflow/operator formula=1E300*1E10 calc=#NUM! sheet=#NUM!
SOURCE large-double/inline-product formula=3037000500*3037000500 calc=9.22337203700025E+18 sheet=9.22337203700025e+18
SOURCE nonfinite/dispatcher-function formula=POWER(10,400) calc=#NUM! sheet=#NUM!
SOURCE nan formula=POWER(-1,0.5) calc=#NUM! sheet=#NUM!
SOURCE na formula=NA() calc=#N/A sheet=#N/A
SOURCE division-zero formula=1/0 calc=#DIV/0! sheet=#DIV/0!
SOURCE text formula="not a number" calc=not a number sheet=not a number
SOURCE floating-overflow/power formula=0.5^-2000 calc=#NUM! sheet=#NUM!
SOURCE floating-overflow/sum formula=SUM(1E308,1E308) calc=#NUM! sheet=#NUM!
SOURCE typed-int64/product formula=B10*B10 calc=9.22337203700025E+18 sheet=9.22337203700025e+18
SOURCE typed-int64/sum formula=B11+B11 calc=1.84467440737096E+19 sheet=1.8446744073709552e+19
SOURCE typed-int64/difference formula=B12-B11 calc=-1.84467440737096E+19 sheet=-1.8446744073709552e+19
SOURCES kinds=12
```

## Full NEW run

```text
SET class examined=14976 match=10031 differ=4945 before=2913 net=234 crash=0
SET wrappers examined=560 match=328 differ=232 before=100 net=0 crash=0
SET number-text examined=280 match=159 differ=121 before=111 net=0 crash=0
SET arrivals-generated examined=7800 match=5773 differ=2027 before=0 net=39 crash=0
SET c-sumif examined=7 match=7 differ=0 before=0 net=0 crash=0
SET c1 examined=12 match=12 differ=0 before=0 net=0 crash=0
SET c10 examined=22 match=17 differ=5 before=5 net=0 crash=0
SET c20 examined=114 match=66 differ=48 before=28 net=17 crash=0
SET c22 examined=56 match=48 differ=8 before=8 net=0 crash=0
SET c23 examined=19 match=10 differ=9 before=0 net=0 crash=0
SET c24 examined=16 match=11 differ=5 before=1 net=0 crash=0
SET c25 examined=3 match=1 differ=2 before=0 net=0 crash=0
SET c4 examined=46 match=42 differ=4 before=2 net=0 crash=0
SET c5 examined=14 match=13 differ=1 before=1 net=0 crash=0
SET c6 examined=18 match=15 differ=3 before=3 net=0 crash=0
SET c7 examined=12 match=9 differ=3 before=1 net=2 crash=0
SET c8 examined=6 match=5 differ=1 before=0 net=1 crash=0
SET c9 examined=6 match=6 differ=0 before=0 net=0 crash=0
SET api examined=47 match=31 differ=16 crash=3 rule_examined=2 rule_differ=0
NUMBER-BAR examined=24014 differ=7430 before=3173 net=293 crash=3 rule_examined=2 rule_differ=0 wall=207.3s
```

Against the last recorded line on `36dd805` (`NUMBER-BAR examined=10248 differ=3115 before=1611 net=80 crash=3 rule_examined=2 rule_differ=0`), `examined` increased by 13,766 and `differ` increased by 4,315 because the population round added the expanded class population and the generated arrival population; this run counts each distinct formula once.
