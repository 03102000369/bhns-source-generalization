#!/usr/bin/env bash
set -euo pipefail
BHNS_MANUSCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BHNS_BUILD="$BHNS_MANUSCRIPT/../build/manuscript"
mkdir -p "$BHNS_BUILD"
cp "$BHNS_MANUSCRIPT/main.tex" "$BHNS_MANUSCRIPT/references.bib" "$BHNS_BUILD/"
cp -R "$BHNS_MANUSCRIPT/figures" "$BHNS_BUILD/"
mkdir -p "$BHNS_BUILD/supplement"
cp "$BHNS_MANUSCRIPT/supplement/supplement.tex" "$BHNS_BUILD/supplement/"
cp -R "$BHNS_MANUSCRIPT/supplement/figures" "$BHNS_BUILD/supplement/"
cp -R "$BHNS_MANUSCRIPT/supplement/tables" "$BHNS_BUILD/supplement/"
cd "$BHNS_BUILD"
for BHNS_DOCUMENT in main supplement/supplement; do
  BHNS_JOB="${BHNS_DOCUMENT##*/}"
  # Discard generated citation state from any earlier document class/style.
  rm -f -- "$BHNS_JOB.aux" "$BHNS_JOB.bbl" "$BHNS_JOB.blg" "$BHNS_JOB.out"
  pdflatex -recorder -interaction=nonstopmode -halt-on-error -jobname="$BHNS_JOB" "$BHNS_DOCUMENT.tex" > "$BHNS_JOB.pass1.txt"
  bibtex "$BHNS_JOB" > "$BHNS_JOB.bibtex.txt"
  # Float placement and author-year labels can need more than two post-BibTeX passes.
  for BHNS_PASS in 2 3 4 5; do
    pdflatex -recorder -interaction=nonstopmode -halt-on-error -jobname="$BHNS_JOB" "$BHNS_DOCUMENT.tex" > "$BHNS_JOB.pass$BHNS_PASS.txt"
    if ! grep -Eq 'Rerun to get|Rerun LaTeX|There were undefined|Label\(s\) may have changed' "$BHNS_JOB.log"; then
      break
    fi
  done
  if grep -Eq 'Rerun to get|Rerun LaTeX|There were undefined|Label\(s\) may have changed' "$BHNS_JOB.log"; then
    printf '%s\n' "Unresolved citations or references in $BHNS_JOB.log" >&2
    exit 1
  fi
done
printf '%s\n' 'Built build/manuscript/main.pdf and build/manuscript/supplement.pdf'
