#!/usr/bin/env bash
set -euo pipefail
BHNS_MANUSCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BHNS_BUILD="$BHNS_MANUSCRIPT/../build/manuscript"
mkdir -p "$BHNS_BUILD"
cp "$BHNS_MANUSCRIPT/main.tex" "$BHNS_MANUSCRIPT/references.bib" "$BHNS_MANUSCRIPT/mnras.cls" "$BHNS_MANUSCRIPT/mnras.bst" "$BHNS_BUILD/"
cp -R "$BHNS_MANUSCRIPT/figures" "$BHNS_BUILD/"
mkdir -p "$BHNS_BUILD/supplement"
cp "$BHNS_MANUSCRIPT/supplement/supplement.tex" "$BHNS_BUILD/supplement/"
cp -R "$BHNS_MANUSCRIPT/supplement/figures" "$BHNS_BUILD/supplement/"
cp -R "$BHNS_MANUSCRIPT/supplement/tables" "$BHNS_BUILD/supplement/"
cd "$BHNS_BUILD"
for BHNS_DOCUMENT in main supplement/supplement; do
  BHNS_JOB="${BHNS_DOCUMENT##*/}"
  pdflatex -interaction=nonstopmode -halt-on-error -jobname="$BHNS_JOB" "$BHNS_DOCUMENT.tex" > "$BHNS_JOB.pass1.txt"
  bibtex "$BHNS_JOB" > "$BHNS_JOB.bibtex.txt"
  pdflatex -interaction=nonstopmode -halt-on-error -jobname="$BHNS_JOB" "$BHNS_DOCUMENT.tex" > "$BHNS_JOB.pass2.txt"
  pdflatex -interaction=nonstopmode -halt-on-error -jobname="$BHNS_JOB" "$BHNS_DOCUMENT.tex" > "$BHNS_JOB.pass3.txt"
done
printf '%s\n' 'Built build/manuscript/main.pdf and build/manuscript/supplement.pdf'
