#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
# The digest fixes the OS filesystem; installing both Poppler and the URW
# standard-14 substitutes in this container keeps host fonts/renderers out.
IMAGE="ubuntu@sha256:fe81560990fae86dc4743202b2cb4d3df98d0bcf949173cecef15ce1127ef852"

if [[ ${1:-} == --render && $# == 3 ]]; then
  input=$(realpath "$2")
  output=$(realpath -m "$3")
  mkdir -p "$(dirname "$output")"
  docker run --rm -v "$(dirname "$input"):/input:ro" -v "$(dirname "$output"):/output" "$IMAGE" bash -eu -c '
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y -qq --no-install-recommends poppler-utils fonts-urw-base35 >/dev/null
    pdftoppm -f 1 -singlefile -gray -r 72 "/input/'"$(basename "$input")"'" "/output/page"
    mv /output/page.pgm "/output/'"$(basename "$output")"'"
  '
  exit
fi

if [[ $# != 0 ]]; then
  echo "usage: $0 [--render INPUT.pdf OUTPUT.pgm]" >&2
  exit 2
fi
: "${EIGENSCRIPT:?set EIGENSCRIPT to the EigenScript v0.48.0 executable}"
ISSUE100_UPDATE_GOLDEN=1 python3 "$ROOT/tests/issue_100_pdf_export.py"
