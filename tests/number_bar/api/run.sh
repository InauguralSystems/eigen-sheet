#!/usr/bin/env bash
# run.sh: each API scenario on tree3+NEW, tree2+NEW, before+OLD, one process each.
D=REVIEW_DIR; P=$D/scratch/pass3/api
NEW=NEW_RUNTIME_BINARY; OLD=OLD_RUNTIME_BINARY
printf '9223372036854775807,9223372036854775807,=A1+B1\n9007199254740993,5000000000,=A2*B2\n' > $P/big.csv
for combo in "tree3:$NEW" "tree2:$NEW" "tree-before:$OLD"; do
  tr=${combo%%:*}; rt=${combo#*:}; W=$P/w-$tr; mkdir -p $W/eigs_modules/sheet
  cp $D/$tr/sheet.eigs $D/$tr/pdf.eigs $D/$tr/eigs.json $W/eigs_modules/sheet/
  for sc in $P/sc-*.eigs; do
    cp $sc $W/app.eigs
    out=$(timeout 60 env -C $W $rt app.eigs 2>&1); rc=$?
    echo "== $tr $(basename $sc) rc=$rc"; printf '%s\n' "$out" | grep -v "^  at \|^ *[0-9]* |\|^ *| " | head -12
  done
done
